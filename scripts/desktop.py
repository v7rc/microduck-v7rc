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
from console_content import active_model, downloaded_options, scene_for_root, scenes
from control_profile import active_profile, control_options
from stopwatch import update_timer


def write_state(status,**extra):
    STATE.parent.mkdir(exist_ok=True)
    temp=STATE.with_suffix('.tmp')
    temp.write_text(json.dumps({'status':status,'pid':os.getpid(),'root':str(ROOT),'updated':time.time(),**extra})+'\n')
    temp.replace(STATE)


def port_conflicts():
    used=[]
    for port in (6188,8800,1234):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            try:
                s.bind(('0.0.0.0',port))
            except OSError:
                used.append(port)
    return used


def allocate_body_port():
    # A robotd left behind by an older session keeps reconnecting to its old TCP
    # endpoint. Do not hand it the new body alongside the new session's robotd.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--scene', default='free')
    parser.add_argument('--keyboard', action='store_true')
    parser.add_argument('--control-option', default='auto')
    parser.add_argument('--model-option', default='auto')
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
        controls = control_options(ROOT)
        if args.control_option not in controls:
            parser.error('Unknown control option')
        models = downloaded_options(ROOT, 'model', 'velstand.onnx')
        if args.model_option == 'auto':
            model = active_model(ROOT)
        elif args.model_option == 'bundled':
            model = ('bundled', None)
        elif args.model_option in models:
            model = models[args.model_option]
        else:
            parser.error('Unknown model option')
        control_label = controls[args.control_option]
        if args.control_option == 'auto':
            version, _ = active_profile(ROOT)
            control_label = f'控制設定 {version}' if version else controls['bundled']
        extra = dict(scene=args.scene, keyboard=args.keyboard, model=model[0],
                     model_option=args.model_option, control_option=args.control_option, control_label=control_label)
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
            body_port = allocate_body_port()
            environment['DUCK_SIM_PORT'] = str(body_port)
            extra['body_port'] = body_port
            write_state('starting', **extra)
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
            if args.control_option in ('bundled', 'linear'):
                bridge += ['--control-file', str(ROOT/'bridge/control-profile.json')]
                if args.control_option == 'linear':
                    bridge += ['--drive-profile', 'linear']
            elif args.control_option != 'auto':
                _, path = downloaded_options(ROOT, 'control', 'control-profile.json')[args.control_option]
                bridge += ['--control-file', str(path)]
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
                subprocess.run([str(ROOT/'scripts/microduck-sim'),'down'],env=environment,check=False)
            ready_file.unlink(missing_ok=True)
            update_timer(STATE.parent / 'stopwatch.json', 'stop')
            write_state('failed' if failure else 'stopped',error=failure, **extra)
        if failure:raise SystemExit(failure)


if __name__=='__main__':main()
