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
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.runtime/desktop-session.json'
sys.path.insert(0, str(ROOT/'bridge'))
from platform_support import ensure_short_root
from console_content import active_model, scene_for_root, scenes
from stopwatch import update_timer


def write_state(status,**extra):
    STATE.parent.mkdir(exist_ok=True)
    temp=STATE.with_suffix('.tmp')
    temp.write_text(json.dumps({'status':status,'pid':os.getpid(),'root':str(ROOT),'updated':time.time(),**extra})+'\n')
    temp.replace(STATE)


def port_conflicts():
    used=[]
    for port,kind in [(6188,socket.SOCK_DGRAM),(8800,socket.SOCK_DGRAM),(1234,socket.SOCK_DGRAM),(7801,socket.SOCK_STREAM)]:
        with socket.socket(socket.AF_INET,kind) as s:
            try:
                if kind == socket.SOCK_STREAM:
                    # Match MuJoCo's reusable listener so a recent connection can be in TIME_WAIT.
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1',port))
                    s.listen()
                else:
                    s.bind(('0.0.0.0',port))
            except OSError:
                used.append(port)
    return used


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--scene', default='free')
    parser.add_argument('--keyboard', action='store_true')
    args=parser.parse_args()
    if args.stop:
        if not STATE.exists():return
        state=json.loads(STATE.read_text())
        if state.get('root')!=str(ROOT) or state.get('status') not in ['starting','running']:return
        pid=state['pid']
        command=subprocess.run(['ps','-p',str(pid),'-o','args='],text=True,capture_output=True).stdout
        if str(ROOT/'scripts/desktop.py') not in command:raise SystemExit('Session PID is no longer owned by this launcher')
        try:
            os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:
            pass
        return
    STATE.parent.mkdir(exist_ok=True)
    with (STATE.parent/'desktop.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('A desktop session for this installation is already running')
        scene = scenes(ROOT).get(args.scene)
        if scene is None:
            raise SystemExit('Unknown scene: ' + args.scene)
        model = active_model(ROOT)
        extra = dict(scene=args.scene, keyboard=args.keyboard, model=model[0])
        write_state('starting', **extra)
        used=port_conflicts()
        if used:
            message='Ports already in use: '+', '.join(map(str,used))+'. Stop the other simulator instance first.'
            write_state('failed',error=message,**extra)
            raise SystemExit(message)
        ready_file = STATE.parent / 'desktop-simulator-ready'
        ready_file.unlink(missing_ok=True)
        stopped=False
        def stop(*_):
            nonlocal stopped
            stopped=True
        signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGHUP,stop)
        processes=[];failure=None
        try:
            environment = os.environ.copy()
            environment['MICRODUCK_DESKTOP_READY_FILE'] = str(ready_file)
            environment.pop('DUCK_SIM_SCENE', None)
            environment.pop('DUCK_SIM_WALK_POLICY', None)
            short = ensure_short_root(ROOT)
            if scene['path'] is not None:
                scene_path = scene['path']
                if scene_path.is_absolute():
                    # The upstream launcher splits its scene arguments on whitespace.
                    local_scene = ROOT / '.runtime/console-scene.xml'
                    scene_for_root(ROOT, scene_path, local_scene)
                    scene_path = local_scene.relative_to(ROOT)
                environment['DUCK_SIM_SCENE'] = str(short / scene_path)
            if model[1] is not None:
                link = ROOT / '.runtime/console-velstand.onnx'
                link.unlink(missing_ok=True)
                link.symlink_to(model[1])
                environment['DUCK_SIM_WALK_POLICY'] = str(short / link.relative_to(ROOT))
            processes.append(subprocess.Popen([str(ROOT/'scripts/microduck-sim'),'serve'],env=environment,start_new_session=True))
            bridge = [str(ROOT/'scripts/v7rc-bridge')]
            if args.keyboard:
                bridge += ['--source-ip', '127.0.0.1']
            processes.append(subprocess.Popen(bridge,start_new_session=True))
            while not stopped:
                if any(p.poll() is not None for p in processes):
                    failure='Simulator or bridge exited; inspect terminal output';break
                try:
                    v=json.loads((ROOT/'.runtime/v7rc-input.json').read_text())
                    if ready_file.is_file() and v.get('robot_connected') and 0<=time.monotonic()-v['published_monotonic']<1:
                        write_state('running', **extra)
                except (OSError,ValueError,KeyError):pass
                time.sleep(.5)
        except Exception as e:failure=str(e)
        finally:
            # Bridge requests neutral before the simulator is stopped.
            for p in reversed(processes):
                if p.poll() is None:
                    try:
                        os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:p.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        p.wait()
            if processes:
                subprocess.run([str(ROOT/'scripts/microduck-sim'),'down'],check=False)
            ready_file.unlink(missing_ok=True)
            update_timer(STATE.parent / 'stopwatch.json', 'stop')
            write_state('failed' if failure else 'stopped',error=failure, **extra)
        if failure:raise SystemExit(failure)


if __name__=='__main__':main()
