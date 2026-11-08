#!/usr/bin/env python3
"""Serve the Microduck desktop console on localhost."""
import argparse
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
SESSION = RUNTIME / 'desktop-session.json'
TIMER = RUNTIME / 'stopwatch.json'
sys.path.insert(0, str(ROOT / 'bridge'))

from console_content import active_model, read_json, scenes, selected
from console_updates import check, install
from platform_support import advertised_ip
from stopwatch import elapsed_ns, read_timer, update_timer


class Console:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.updates = {}
        self.next_ip = 0
        self.ip = ''
        self.version = read_json(ROOT / '.installer-source.json').get('version')
        if self.version is None:
            self.version = (ROOT / 'packaging/version.txt').read_text().strip()

    def session(self):
        value = read_json(SESSION)
        if value.get('status') in ('starting', 'running') and time.time() - value.get('updated', 0) > 5:
            if self.process is None or self.process.poll() is not None:
                return {'status': 'stopped'}
        return value

    def state(self):
        session = self.session()
        control = read_json(RUNTIME / 'v7rc-input.json')
        video = read_json(RUNTIME / 'v7rc-video.json')
        now = time.monotonic()
        if now >= self.next_ip:
            self.ip = advertised_ip(control.get('owner'))
            self.next_ip = now + 5
        timer = read_timer(TIMER)
        live = session.get('status') == 'running'
        control_live = live and 0 <= now - control.get('published_monotonic', -1) < 1 and control.get('armed')
        camera_live = live and 0 <= now - video.get('published_monotonic', -1) < 2 and video.get('active')
        return {
            'session': session, 'ip': self.ip,
            'control': (control.get('owner') or '') if control_live else '',
            'camera': bool(camera_live), 'fps': video.get('tx_fps', 0) if camera_live else 0,
            'scenes': {key: value['title'] for key, value in scenes(ROOT).items()},
            'timer_ms': elapsed_ns(timer, time.monotonic_ns()) // 1_000_000,
            'timer_running': timer['started_ns'] is not None,
            'versions': {'program': self.version, 'scenes': selected(ROOT, 'scenes').get('version', 'bundled'),
                         'model': active_model(ROOT)[0],
                         'control': selected(ROOT, 'control').get('version', self.version)},
            'updates': {key: value['version'] for key, value in self.updates.items()},
        }

    def stop(self):
        update_timer(TIMER, 'stop')
        subprocess.run([ROOT / 'scripts/desktop', '--stop'], check=True, timeout=10)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.process is not None:
                if self.process.poll() is not None:
                    break
            elif self.session().get('status') not in ('running', 'starting'):
                break
            time.sleep(.1)
        else:
            raise TimeoutError('Simulator did not stop')
        self.process = None

    def start(self, scene, keyboard):
        if scene not in scenes(ROOT):
            raise ValueError('Unknown scene')
        if self.session().get('status') in ('starting', 'running') or (
                self.process is not None and self.process.poll() is None):
            raise ValueError('Stop the current scene first')
        command = [ROOT / 'scripts/desktop', '--scene', scene]
        if keyboard:
            command.append('--keyboard')
        with (RUNTIME / 'console-simulator.log').open('ab') as log:
            self.process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        # Avoid briefly displaying the previous run while the supervisor starts.
        deadline = time.monotonic() + 2
        while read_json(SESSION).get('pid') != self.process.pid and self.process.poll() is None and time.monotonic() < deadline:
            time.sleep(.025)

    def keyboard(self, keys):
        session = self.session()
        if session.get('status') != 'running' or not session.get('keyboard'):
            return
        keys = set(keys)
        pwm = [1500] * 4
        if ' ' not in keys:
            for index, positive, negative in [(0,'d','a'), (1,'w','s'), (2,'ArrowDown','ArrowUp'), (3,'ArrowRight','ArrowLeft')]:
                pwm[index] += 350 * ((positive in keys) - (negative in keys))
        payload = ('SRT' + ''.join(f'{value:04d}' for value in pwm) + '#').encode()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(payload, ('127.0.0.1', 6188))

    def action(self, name, body):
        if name == 'keyboard':
            self.keyboard(body['keys'])
            return ''
        with self.lock:
            if name in ('start', 'restart'):
                scene = body['scene']
                if scene not in scenes(ROOT):
                    raise ValueError('Unknown scene')
                if name == 'restart':
                    self.stop()
                self.start(scene, body.get('keyboard') is True)
            elif name == 'stop':
                self.stop()
            elif name in ('timer-start', 'timer-stop', 'timer-reset'):
                update_timer(TIMER, name.removeprefix('timer-'))
            elif name == 'check':
                self.updates = check(ROOT, self.version)
                return '有可用更新。' if self.updates else '目前沒有可用更新。'
            elif name == 'install':
                kind = body['kind']
                if kind not in self.updates:
                    raise ValueError('Check for updates first')
                if self.session().get('status') in ('starting', 'running'):
                    raise ValueError('Stop the simulator before installing an update')
                message = install(ROOT, kind, self.updates[kind])
                if kind != 'program':
                    del self.updates[kind]
                return message
            else:
                raise ValueError('Unknown action')
        return ''


def handler(console, token):
    class Handler(BaseHTTPRequestHandler):
        def allowed_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def send_data(self, content, kind, status=200):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(content)

        def json(self, data, status=200):
            self.send_data(json.dumps(data).encode(), 'application/json', status)

        def authorized(self):
            return self.allowed_host() and secrets.compare_digest(self.headers.get('X-Microduck-Token', ''), token)

        def do_GET(self):
            if not self.allowed_host():
                return self.send_error(403)
            if self.path == '/':
                return self.send_data((ROOT / 'docs/desktop-console.html').read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/checklist':
                return self.send_data((ROOT / 'docs/integration/desktop-console-todo.html').read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/state' and self.authorized():
                return self.json(console.state())
            self.send_error(404)

        def do_POST(self):
            if not self.authorized():
                return self.send_error(403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Invalid request length')
                body = json.loads(self.rfile.read(length))
                message = console.action(self.path.removeprefix('/'), body)
                self.json({'message': message})
            except Exception as error:
                self.json({'error': str(error)}, 400)

        def log_message(self, *_):
            pass

    return Handler


def open_browser(url):
    if sys.platform == 'darwin':
        subprocess.Popen(['open', url])
    elif 'microsoft' in Path('/proc/sys/kernel/osrelease').read_text().lower():
        subprocess.Popen(['explorer.exe', url])
    else:
        subprocess.Popen(['xdg-open', url])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    address = RUNTIME / 'console-url'
    with (RUNTIME / 'console.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            url = address.read_text().strip()
            print(url, flush=True)
            if not args.no_browser:
                open_browser(url)
            return
        token = secrets.token_urlsafe()
        with ThreadingHTTPServer(('127.0.0.1', 0), handler(Console(), token)) as server:
            url = f'http://127.0.0.1:{server.server_port}/#{token}'
            with open(address, 'w', opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
                handle.write(url)
            print(url, flush=True)
            if not args.no_browser:
                open_browser(url)
            try:
                server.serve_forever()
            finally:
                address.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
