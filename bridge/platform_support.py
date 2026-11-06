"""Shared POSIX paths and LAN discovery for macOS, Linux and Windows via WSL2."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import shlex
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def require_posix():
    if os.name == 'nt':
        raise RuntimeError('The upstream robotd requires Unix IPC. Use Windows 11 + WSL2 Ubuntu; see docs/INSTALL.en.md.')


def short_root(root=ROOT):
    require_posix()
    root = Path(root).resolve()
    override = os.environ.get('MICRODUCK_SHORT_ROOT')
    legacy = Path(f'/tmp/microduck-m4-{os.getuid()}')
    if override:
        path = Path(override)
    elif legacy.is_symlink() and legacy.resolve() == root:
        path = legacy  # Preserve the running Mac installation's existing sockets/tool paths.
    else:
        digest = hashlib.sha256(str(root).encode()).hexdigest()[:8]
        path = Path(f'/tmp/microduck-v7rc-{os.getuid()}-{digest}')
    if not path.is_absolute() or any(c.isspace() for c in str(path)) or len(str(path/'.runtime/duck-sim/duck-a.sock')) > 100:
        raise ValueError('MICRODUCK_SHORT_ROOT must be an absolute, short, whitespace-free path')
    return path


def ensure_short_root(root=ROOT):
    root = Path(root).resolve()
    path = short_root(root)
    if path.is_symlink():
        if path.resolve() != root:
            raise RuntimeError(f'Another workspace owns {path}; refusing to replace it')
    elif path.exists():
        raise RuntimeError(f'{path} exists and is not this workspace symlink')
    else:
        path.symlink_to(root, target_is_directory=True)
    return path


def robot_socket(root=ROOT):
    return Path(os.environ.get('MICRODUCK_ROBOT_SOCKET', str(short_root(root)/'.runtime/duck-sim/duck-a.sock')))


def valid_lan_ip(value):
    try:
        ip = ipaddress.IPv4Address(value)
        return not (ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_link_local)
    except ipaddress.AddressValueError:
        return False


def advertised_ip(peer=None):
    override = os.environ.get('MICRODUCK_ADVERTISE_IP')
    if override:
        return override if valid_lan_ip(override) else 'Invalid IP override'
    # A connected phone gives the most useful route, including multiple NIC/VPN setups.
    if peer and valid_lan_ip(peer):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((peer, 8800))  # Select a route; UDP connect sends no datagram.
                value = s.getsockname()[0]
                if valid_lan_ip(value):
                    return value
        except OSError:
            pass
    try:
        if platform.system() == 'Darwin':
            value = subprocess.check_output(['/usr/sbin/ipconfig', 'getifaddr', 'en0'], text=True, stderr=subprocess.DEVNULL, timeout=.3).strip()
            if valid_lan_ip(value):
                return value
        else:
            rows = json.loads(subprocess.check_output(['ip', '-j', '-4', 'addr', 'show', 'up'], text=True, stderr=subprocess.DEVNULL, timeout=.3))
            candidates = []
            for row in rows:
                name = row['ifname']
                if not name.startswith(('wl', 'en', 'eth')):
                    continue
                for address in row.get('addr_info', []):
                    value = address.get('local', '')
                    if valid_lan_ip(value):
                        candidates.append((not name.startswith('wl'), name, value))
            if candidates:
                return sorted(candidates)[0][2]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        pass
    return 'Set MICRODUCK_ADVERTISE_IP'


def shell_environment(root=ROOT):
    root = Path(root).resolve()
    short = ensure_short_root(root)
    (root/'.runtime/duck-sim').mkdir(parents=True, exist_ok=True)
    cargo = short/'.tools/cargo' if (root/'.tools/cargo').is_dir() else Path(os.environ.get('CARGO_HOME', Path.home()/'.cargo'))
    rustup = short/'.tools/rustup' if (root/'.tools/rustup').is_dir() else Path(os.environ.get('RUSTUP_HOME', Path.home()/'.rustup'))
    return {
        'SHORT': str(short), 'CARGO_HOME': str(cargo), 'RUSTUP_HOME': str(rustup), 'RUSTUP_TOOLCHAIN': '1.94.1',
        'CARGO_TARGET_DIR': str(short/'microduck/target'),
        'UV_CACHE_DIR': str(root/'.tools/uv-cache'), 'UV_PYTHON_INSTALL_DIR': str(root/'.tools/python'),
        'PATH': os.pathsep.join([str(root/'.tools/bin'), str(cargo/'bin'), str(root/'microduck_rl/.venv/bin'), os.environ.get('PATH', '')]),
        'DUCK_SIM_RL': str(short/'microduck_rl'), 'DUCK_SIM_STATE': str(short/'.runtime/duck-sim'),
        'MICRODUCK_BODY_MODULE': 'microduck_hud', 'MICRODUCK_HUD_FILE': str(root/'.runtime/v7rc-input.json'),
        'MICRODUCK_ROBOT_SOCKET': str(robot_socket(root)),
        'PYTHONPATH': os.pathsep.join(filter(None, [str(root/'bridge'), os.environ.get('PYTHONPATH', '')])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['shell-env', 'doctor'])
    args = parser.parse_args()
    try:
        if args.action == 'shell-env':
            for name, value in shell_environment().items():
                print(f'export {name}={shlex.quote(value)}')
        else:
            require_posix()
            print(json.dumps({'system': platform.system(), 'release': platform.release(),
                              'wsl': 'microsoft' in platform.release().lower(),
                              'advertised_ip': advertised_ip(), 'robot_socket': str(robot_socket()),
                              'display': os.environ.get('DISPLAY'), 'wayland_display': os.environ.get('WAYLAND_DISPLAY'),
                              'upstream_python_exists': (ROOT/'microduck_rl/.venv/bin/python').is_file()}, indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
