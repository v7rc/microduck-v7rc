#!/usr/bin/env python3
"""Send real SRT UDP datagrams and observe robotd plus MuJoCo; not a phone test."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bridge'))
from platform_support import robot_socket
import argparse
import datetime
import json
import math
import socket
import threading
import time
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Mac LAN IPv4, or loopback for a local test")
    parser.add_argument("--port", type=int, default=6188)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    body = socket.create_connection(("127.0.0.1",7801), timeout=3)
    bf = body.makefile("rw")

    def body_call(value):
        bf.write(json.dumps(value)+"\n");bf.flush()
        return json.loads(bf.readline())

    body_call({"op":"hello","protocol":1,"joints":15})
    control = socket.socket(socket.AF_UNIX)
    control.connect(str(robot_socket()))
    sf = control.makefile("rw")
    sf.write('{"jsonrpc":"2.0","id":1,"method":"robot.subscribe","params":{"hz":20}}\n');sf.flush()
    accepted=json.loads(sf.readline())
    if not accepted.get("result",{}).get("accepted"): raise RuntimeError(accepted)
    current={}

    def receive():
        try:
            for line in sf:
                msg=json.loads(line)
                if msg.get("method")=="robot.state":
                    current["latest"]=(time.monotonic(), msg["params"])
        except OSError:
            pass

    threading.Thread(target=receive,daemon=True).start()
    rows=(args.output/"samples.jsonl").open("w")
    report={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "destination":{"ip":args.host,"port":args.port},
            "scope":"SRT from a Python sender on this Mac to its LAN IP; not V7RC phone or over-air Wi-Fi acceptance",
            "phases":[]}
    head_reference = None

    def send(channels):
        udp.sendto(("SRT"+"".join(f"{n:04d}" for n in channels)+"#").encode(),(args.host,args.port))

    def phase(name,seconds,channels=None,expected_move=None,expected_head=None,kind=None):
        nonlocal head_reference
        start=time.monotonic();samples=[]
        for i in range(round(seconds*10)+1):
            if channels is not None:send(channels)
            if kind=="invalid":udp.sendto(b"SRT1500999915001500#",(args.host,args.port))
            sensor=body_call({"op":"read"})
            fresh=current.get("latest")
            if not fresh or time.monotonic()-fresh[0]>.4:raise RuntimeError("No fresh robot.state")
            state=fresh[1]
            w,x,y,z=sensor["imu"]["quat"]
            row={"phase":name,"elapsed_s":time.monotonic()-start,"sensor":sensor,"state":state,
                 "yaw_rad":math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))}
            rows.write(json.dumps(row)+"\n");samples.append(row)
            if i<round(seconds*10):time.sleep(max(0,start+(i+1)/10-time.monotonic()))
        a,b=samples[0],samples[-1]
        turn=sum(math.atan2(math.sin(q["yaw_rad"]-p["yaw_rad"]),math.cos(q["yaw_rad"]-p["yaw_rad"])) for p,q in zip(samples,samples[1:]))
        pa,pb=a['sensor']['trunk'],b['sensor']['trunk'];dx,dy=pb[0]-pa[0],pb[1]-pa[1]
        result={"name":name,"seconds":seconds,"channels":channels,"displacement_m":math.hypot(dx,dy),
                "forward_m":dx*math.cos(a['yaw_rad'])+dy*math.sin(a['yaw_rad']),"turn_deg":math.degrees(turn),
                "min_trunk_m":min(r['sensor']['trunk_z'] for r in samples),
                "max_tilt_deg":max(math.degrees(math.acos(max(-1,min(1,-r['sensor']['imu']['gravity'][2])))) for r in samples),
                "end_move":b['state']['move'],"end_head":b['state']['head'],
                "end_head_joints":b['sensor']['positions'][5:9],
                "loop_hz_min":min(r['state']['loop']['hz'] for r in samples)}
        checks={"upright":result['min_trunk_m']>.095 and result['max_tilt_deg']<30,
                "control_loop":result['loop_hz_min']>=45,
                "not_fallen":all(not r['state']['safety']['fallen'] for r in samples)}
        if expected_move is not None:
            checks['mapped_move']=all(abs(p-q)<.01 for p,q in zip(b['state']['move']['requested'],expected_move))
            checks['applied_move']=all(abs(p-q)<.02 for p,q in zip(b['state']['move']['applied'],expected_move))
        if expected_head is not None:
            checks['mapped_head']=all(abs(p-q)<.02 for p,q in zip(b['state']['head'],expected_head))
        if kind=='forward':checks['actual_forward']=result['forward_m']>.3
        if kind=='left':checks['actual_left']=result['turn_deg']>30
        if kind=='right':checks['actual_right']=result['turn_deg']<-30
        if name=='neutral_before_head':
            head_reference=result['end_head_joints']
        if kind and kind.startswith('head_'):
            # The learned policy's nominal joint pose is not a zero command angle.
            # Check actual joint changes against the measured centered pose.
            result['centered_head_reference']=head_reference
            delta=[x-y for x,y in zip(result['end_head_joints'],head_reference)]
            result['head_joint_delta_rad']=delta
            if kind=='head_yaw_right':checks['actual_head_joint']=delta[2]<-.1
            if kind=='head_yaw_left':checks['actual_head_joint']=delta[2]>.1
            if kind=='head_pitch_positive':checks['actual_head_joint']=delta[1]>.1
            if kind=='head_pitch_negative':checks['actual_head_joint']=delta[1]<-.1
        if kind in ['expiry','invalid']:
            zeros=[r['elapsed_s'] for r in samples if r['elapsed_s']>.1
                   and max(abs(v) for v in r['state']['move']['requested'])<.001]
            centered=[r['elapsed_s'] for r in samples if r['elapsed_s']>.1
                      and max(abs(v) for v in r['state']['head'])<.01]
            result['first_zero_request_s']=min(zeros) if zeros else None
            result['first_head_centered_s']=min(centered) if centered else None
            checks['watchdog_zero']=bool(zeros) and min(zeros)<.6
            # robot.state.head is a smoothed command, unlike move.requested.
            # Allow its convergence separately from the UDP watchdog deadline.
            checks['head_settled']=bool(centered) and min(centered)<1.0
        result['checks']=checks;result['passed']=all(checks.values())
        report['phases'].append(result)
        (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(result),flush=True)

    try:
        # Allow the subscription's first notification before sampling.
        deadline=time.monotonic()+2
        while not current and time.monotonic()<deadline:time.sleep(.01)
        center=(1500,)*4; zero=(0,0,0); home=(0,0,0,0)
        # An already-idle robot fades its autonomous look-around out over 1.5 s.
        phase('neutral_arm',3,center,zero,home)
        phase('forward',8,(1500,2000,1500,1500),(.3,0,0),home,'forward')
        phase('packet_loss',2,None,zero,home,'expiry')
        phase('nonneutral_after_timeout',1,(1500,2000,1500,1500),zero,home)
        phase('neutral_rearm',.5,center,zero,home)
        phase('left',6,(1000,1500,1500,1500),(0,0,.8),home,'left')
        phase('neutral_before_right',1,center,zero,home)
        phase('right',6,(2000,1500,1500,1500),(0,0,-.8),home,'right')
        phase('neutral_before_head',1,center,zero,home)
        phase('head_yaw_right',2,(1500,1500,1500,2000),zero,(0,0,-.4,0),'head_yaw_right')
        phase('head_yaw_left',2,(1500,1500,1500,1000),zero,(0,0,.4,0),'head_yaw_left')
        phase('head_pitch_positive',2,(1500,1500,1000,1500),zero,(0,.25,0,0),'head_pitch_positive')
        phase('head_pitch_negative',2,(1500,1500,2000,1500),zero,(0,-.25,0,0),'head_pitch_negative')
        phase('malformed_flood',2,None,zero,home,'invalid')
        report['passed']=all(p['passed'] for p in report['phases'])
    finally:
        for _ in range(3):send((1500,)*4);time.sleep(.03)
        rows.close();udp.close();body.close();control.shutdown(socket.SHUT_RDWR);control.close()
        (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report.get('passed'):raise SystemExit(1)


if __name__=='__main__':main()
