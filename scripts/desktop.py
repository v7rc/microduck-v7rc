#!/usr/bin/env python3
"""One desktop session owns the simulator and neutral-on-exit V7RC bridge."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.runtime/desktop-session.json'


def write_state(status,**extra):
    STATE.parent.mkdir(exist_ok=True)
    temp=STATE.with_suffix('.tmp')
    temp.write_text(json.dumps({'status':status,'pid':os.getpid(),'root':str(ROOT),'updated':time.time(),**extra})+'\n')
    temp.replace(STATE)


def port_conflicts():
    used=[]
    for port,kind in [(6188,socket.SOCK_DGRAM),(8800,socket.SOCK_DGRAM),(1234,socket.SOCK_DGRAM),(7801,socket.SOCK_STREAM)]:
        with socket.socket(socket.AF_INET,kind) as s:
            try:s.bind(('0.0.0.0',port))
            except OSError:used.append(port)
    return used


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop',action='store_true')
    args=parser.parse_args()
    if args.stop:
        if not STATE.exists():return
        state=json.loads(STATE.read_text())
        if state.get('root')!=str(ROOT) or state.get('status') not in ['starting','running']:return
        pid=state['pid']
        command=subprocess.run(['ps','-p',str(pid),'-o','args='],text=True,capture_output=True).stdout
        if str(ROOT/'scripts/desktop.py') not in command:raise SystemExit('Session PID is no longer owned by this launcher')
        os.kill(pid,signal.SIGTERM);return
    STATE.parent.mkdir(exist_ok=True)
    with (STATE.parent/'desktop.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('A desktop session for this installation is already running')
        write_state('starting')
        used=port_conflicts()
        if used:
            message='Ports already in use: '+', '.join(map(str,used))+'. Stop the other simulator instance first.'
            write_state('failed',error=message)
            raise SystemExit(message)
        stopped=False
        def stop(*_):
            nonlocal stopped
            stopped=True
        signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGHUP,stop)
        processes=[];failure=None
        try:
            processes.append(subprocess.Popen([str(ROOT/'scripts/microduck-sim'),'serve'],start_new_session=True))
            processes.append(subprocess.Popen([str(ROOT/'scripts/v7rc-bridge')],start_new_session=True))
            while not stopped:
                if any(p.poll() is not None for p in processes):
                    failure='Simulator or bridge exited; inspect terminal output';break
                try:
                    v=json.loads((ROOT/'.runtime/v7rc-input.json').read_text())
                    if v.get('robot_connected') and 0<=time.monotonic()-v['published_monotonic']<1:
                        write_state('running')
                except (OSError,ValueError,KeyError):pass
                time.sleep(.5)
        except Exception as e:failure=str(e)
        finally:
            # Bridge requests neutral before the simulator is stopped.
            for p in reversed(processes):
                if p.poll() is None:
                    p.terminate()
                    try:p.wait(timeout=20)
                    except subprocess.TimeoutExpired:p.kill();p.wait()
            if processes:
                subprocess.run([str(ROOT/'scripts/microduck-sim'),'down'],check=False)
            write_state('failed' if failure else 'stopped',error=failure)
        if failure:raise SystemExit(failure)


if __name__=='__main__':main()
