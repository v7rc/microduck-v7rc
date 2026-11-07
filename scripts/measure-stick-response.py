#!/usr/bin/env python3
"""Measure real MuJoCo motion through the SRT bridge; requires exclusive simulator use."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'bridge'))
from platform_support import robot_socket
from v7rc_udp import Config, map_channels


class Link:
    def __init__(self, address, unix=False):
        self.sock = socket.socket(socket.AF_UNIX if unix else socket.AF_INET)
        self.sock.settimeout(2)
        self.sock.connect(address)
        self.file = self.sock.makefile('rw')

    def call(self, value):
        self.file.write(json.dumps(value)+'\n'); self.file.flush()
        line = self.file.readline()
        if not line:
            raise RuntimeError('Simulator connection closed')
        reply = json.loads(line)
        if 'error' in reply:
            raise RuntimeError(reply['error'])
        return reply

    def close(self):
        try: self.sock.shutdown(socket.SHUT_RDWR)
        except OSError: pass
        self.file.close(); self.sock.close()


def angles(sensor):
    w, x, y, z = sensor['imu']['quat']
    yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
    tilt = math.degrees(math.acos(max(-1, min(1, -sensor['imu']['gravity'][2]))))
    return yaw, tilt


def motion(rows):
    if len(rows) < 2:
        return None
    forward = lateral = turn = 0.0
    for a, b in zip(rows, rows[1:]):
        dyaw = math.atan2(math.sin(b['yaw']-a['yaw']), math.cos(b['yaw']-a['yaw']))
        heading = a['yaw']+dyaw/2
        dx = b['sensor']['trunk'][0]-a['sensor']['trunk'][0]
        dy = b['sensor']['trunk'][1]-a['sensor']['trunk'][1]
        forward += dx*math.cos(heading)+dy*math.sin(heading)
        lateral += -dx*math.sin(heading)+dy*math.cos(heading)
        turn += dyaw
    sim_dt = rows[-1]['sensor']['sim_time']-rows[0]['sensor']['sim_time']
    wall_dt = rows[-1]['elapsed']-rows[0]['elapsed']
    if sim_dt <= 0 or wall_dt <= 0:
        raise RuntimeError('Non-positive measurement duration')
    return {'samples':len(rows), 'sim_seconds':sim_dt, 'wall_seconds':wall_dt,
            'realtime_factor':sim_dt/wall_dt,
            'body_forward_m':forward, 'body_lateral_m':lateral, 'turn_deg':math.degrees(turn),
            'vx_m_s':forward/sim_dt, 'vy_m_s':lateral/sim_dt,
            'yaw_rad_s':turn/sim_dt, 'yaw_deg_s':math.degrees(turn)/sim_dt,
            'vx_wall_m_s':forward/wall_dt, 'yaw_wall_deg_s':math.degrees(turn)/wall_dt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--levels', type=int, nargs='+', default=[25,50,75,100])
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--warmup', type=float, default=2)
    parser.add_argument('--drive-profile', choices=('linear', 'velstand-v8'), default='linear')
    args = parser.parse_args()
    if not 0 <= args.warmup < args.seconds or not all(0 < n <= 100 for n in args.levels) or args.repeats < 1:
        parser.error('Invalid measurement configuration')
    for port, kind in [(6188,socket.SOCK_DGRAM),(8800,socket.SOCK_DGRAM),(7801,socket.SOCK_STREAM)]:
        with socket.socket(socket.AF_INET,kind) as s:
            if kind==socket.SOCK_STREAM:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.bind(('0.0.0.0',port))  # Never stop a pre-existing simulator/phone session.
    args.output.mkdir(parents=True,exist_ok=True)
    cfg = Config(drive_profile=args.drive_profile)
    env = os.environ.copy(); env.update(DUCK_SIM_VIEWER='0',MICRODUCK_VIDEO='0')
    def revision(name):
        return subprocess.check_output(['git','-C',str(ROOT/name),'rev-parse','HEAD'],text=True).strip()
    policy=ROOT/'.runtime/duck-sim/policies/current/velstand.onnx'
    report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'Local SRT UDP sender -> bridge -> robotd -> headless CPU MuJoCo; no phone, camera or physical robot',
            'runtime_commit':revision('microduck'),'rl_commit':revision('microduck_rl'),
            'integration_commit':revision('.'),
            'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),
            'configuration':{'drive_profile':args.drive_profile,'repeats':args.repeats,'levels':args.levels,'neutral_seconds':4,
                             'motion_seconds':args.seconds,'excluded_start_seconds':args.warmup,
                             'sample_hz':20,'deadzone':cfg.deadzone,'max_forward':cfg.max_forward,
                             'max_turn':cfg.max_turn,'fresh_scene_per_trial':True},'trials':[]}
    def save():
        temp=args.output/'summary.tmp'
        temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(args.output/'summary.json')
    interrupted=False
    def stop(*_):
        nonlocal interrupted
        interrupted=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    cases=[]; rng=random.Random(20261107)
    for repeat in range(1,args.repeats+1):
        block=[(direction,level) for direction in ['forward','backward','left','right'] for level in args.levels]
        rng.shuffle(block)
        cases.extend([(repeat,'neutral',0),(repeat,'deadzone',8)]+[(repeat,d,l) for d,l in block])
    raw=(args.output/'samples.jsonl').open('w')
    try:
        for index,(repeat,direction,level) in enumerate(cases,1):
            if interrupted: raise RuntimeError('Interrupted')
            name=f'{index:02d}-r{repeat}-{direction}-{level}'
            channels=[1500]*4
            if direction in ['forward','backward']: channels[1]+=round(5*level)*(1 if direction=='forward' else -1)
            if direction in ['left','right']: channels[0]+=round(5*level)*(1 if direction=='right' else -1)
            if direction=='deadzone': channels[0]=channels[1]=1540
            expected,_=map_channels(channels,cfg)
            result={'name':name,'repeat':repeat,'direction':direction,'stick_percent':level,
                    'channels':channels,'command':expected}
            print('START',index,'/',len(cases),name,flush=True)
            processes=[]; links=[]; rows=[]; latest={}; receiver=None
            with (args.output/(name+'.log')).open('w') as log:
                try:
                    processes.append(subprocess.Popen([str(ROOT/'scripts/microduck-sim'),'serve'],cwd=ROOT,env=env,stdout=log,stderr=log))
                    processes.append(subprocess.Popen([str(ROOT/'scripts/v7rc-bridge'),'--source-ip','127.0.0.1',
                                                       '--drive-profile',args.drive_profile],cwd=ROOT,env=env,stdout=log,stderr=log))
                    deadline=time.monotonic()+30
                    while time.monotonic()<deadline:
                        if any(p.poll() is not None for p in processes): raise RuntimeError('Child exited during startup')
                        if 'Your duck is up.' not in (args.output/(name+'.log')).read_text(errors='replace'):
                            time.sleep(.15);continue
                        try:
                            health=Link(str(robot_socket()),True)
                            reply=health.call({'jsonrpc':'2.0','id':1,'method':'robot.health'})
                            health.close()
                            if reply.get('result',{}).get('healthy'):break
                        except (OSError,ValueError,RuntimeError):pass
                        time.sleep(.15)
                    else:raise RuntimeError('robotd health startup timeout')
                    body=Link(('127.0.0.1',7801));links.append(body)
                    body.call({'op':'hello','protocol':1,'joints':15})
                    control=Link(str(robot_socket()),True);links.append(control)
                    control.call({'jsonrpc':'2.0','id':2,'method':'robot.subscribe','params':{'hz':20}})
                    def receive():
                        try:
                            for line in control.file:
                                msg=json.loads(line)
                                if msg.get('method')=='robot.state':latest['value']=(time.monotonic(),msg['params'])
                        except (OSError,ValueError):pass
                    receiver=threading.Thread(target=receive,daemon=True);receiver.start()
                    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                    def send(values):
                        udp.sendto(('SRT'+''.join(f'{n:04d}' for n in values)+'#').encode(),('127.0.0.1',6188))
                    start=time.monotonic()
                    while time.monotonic()-start<4:
                        if interrupted:raise RuntimeError('Interrupted')
                        send([1500]*4);time.sleep(.05)
                    telemetry=json.loads((ROOT/'.runtime/v7rc-input.json').read_text())
                    if telemetry.get('owner')!='127.0.0.1' or not telemetry.get('armed'):
                        raise RuntimeError('Local sender did not acquire neutral-armed ownership')
                    start=time.monotonic(); initial=body.call({'op':'read'});_,tilt=angles(initial)
                    result['initial']={'trunk_z':initial['trunk_z'],'tilt_deg':tilt}
                    if initial['trunk_z']<.095 or tilt>20:
                        raise RuntimeError('Initial standing condition not met')
                    for step in range(round(args.seconds*20)+1):
                        if interrupted:raise RuntimeError('Interrupted')
                        send(channels)
                        sensor=body.call({'op':'read'});yaw,tilt=angles(sensor)
                        timestamp,state=latest.get('value',(0,None))
                        if time.monotonic()-timestamp>.5:raise RuntimeError('No fresh robot.state')
                        row={'trial':name,'elapsed':time.monotonic()-start,'sensor':sensor,'yaw':yaw,'tilt_deg':tilt,'state':state}
                        rows.append(row);raw.write(json.dumps(row)+'\n')
                        if sensor['trunk_z']<.065 or tilt>60 or state['safety']['fallen']:
                            result['aborted_for_fall']=True;break
                        if step<round(args.seconds*20):time.sleep(max(0,start+(step+1)/20-time.monotonic()))
                    send([1500]*4);udp.close()
                    steady=[r for r in rows if r['elapsed']>=args.warmup]
                    result['whole_motion']=motion(rows);result['steady']=motion(steady)
                    result['min_trunk_m']=min(r['sensor']['trunk_z'] for r in rows)
                    result['max_tilt_deg']=max(r['tilt_deg'] for r in rows)
                    result['loop_hz_min']=min(r['state']['loop']['hz'] for r in rows)
                    result['completed']=not result.get('aborted_for_fall',False)
                    result['upright']=result['min_trunk_m']>.095 and result['max_tilt_deg']<30 and result['completed']
                    result['mapping_ok']=bool(steady) and all(max(abs(a-b) for a,b in zip(r['state']['move']['requested'],[expected['vx'],0,expected['vyaw']]))<.002 for r in steady)
                    if steady:
                        result['mean_applied']=[sum(r['state']['move']['applied'][i] for r in steady)/len(steady) for i in range(3)]
                except Exception as error:
                    result['error']=str(error)
                finally:
                    # Terminate bridge first, so neutral is requested while robotd is alive.
                    for p in reversed(processes):
                        if p.poll() is None:
                            p.terminate()
                            try:p.wait(timeout=15)
                            except subprocess.TimeoutExpired:p.kill();p.wait()
                    for link in links:
                        try:link.close()
                        except OSError:pass
                    if receiver:receiver.join(timeout=2)
                    subprocess.run([str(ROOT/'scripts/microduck-sim'),'down'],cwd=ROOT,env=env,stdout=log,stderr=log)
            report['trials'].append(result);raw.flush();save()
            print('RESULT',json.dumps({k:result.get(k) for k in ['name','steady','upright','mapping_ok','error']}),flush=True)
            if 'error' in result:raise RuntimeError(result['error'])
        report['complete']=True
    except Exception as error:
        report['complete']=False;report['error']=str(error)
        raise
    finally:
        report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();raw.close()


if __name__=='__main__':main()
