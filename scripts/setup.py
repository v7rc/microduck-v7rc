#!/usr/bin/env python3
"""Install pinned upstreams and project-local tools without resetting existing checkouts."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'bridge'))
from platform_support import require_posix, ensure_short_root, shell_environment


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def prepare_upstream(name, revision):
    target = ROOT/name
    if not target.exists():
        if target.is_symlink():
            raise RuntimeError(f'Dangling symlink: {target}; fix it explicitly before setup')
        run(['git', 'clone', '--no-checkout', revision['url'], target])
        run(['git', '-C', target, 'checkout', '--detach', revision['commit']])
    head = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    if head != revision['commit']:
        raise RuntimeError(f'{name} is at {head}, expected {revision["commit"]}; refusing to reset your checkout')
    patch = revision.get('patch')
    if patch:
        patch = ROOT/patch
        applied = subprocess.run(['git', '-C', str(target), 'apply', '--reverse', '--check', str(patch)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not applied:
            run(['git', '-C', target, 'apply', '--check', patch])
            run(['git', '-C', target, 'apply', patch])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Only inspect prerequisites; no downloads, symlinks or checkout changes')
    args = parser.parse_args()
    require_posix()
    missing = [name for name in ['git', 'curl', 'cc', 'cmake', 'pkg-config'] if not shutil.which(name)]
    print(json.dumps({'platform': platform.system(), 'architecture': platform.machine(), 'missing_commands': missing, 'mode': 'check' if args.check else 'install'}))
    if missing:
        raise RuntimeError('Install prerequisites listed in docs/INSTALL.en.md first')
    if args.check:
        return
    tools = ROOT/'.tools'
    tools.mkdir(exist_ok=True)
    short = ensure_short_root()
    env = os.environ.copy()
    env.update({'CARGO_HOME': str(short/'.tools/cargo'), 'RUSTUP_HOME': str(short/'.tools/rustup'),
                'RUSTUP_TOOLCHAIN': '1.94.1', 'UV_INSTALL_DIR': str(tools/'bin'), 'UV_NO_MODIFY_PATH': '1',
                'UV_PYTHON_INSTALL_DIR': str(tools/'python'), 'UV_CACHE_DIR': str(tools/'uv-cache')})
    env['PATH'] = os.pathsep.join([str(tools/'cargo/bin'), str(tools/'bin'), os.environ.get('PATH', '')])
    uv = tools/'bin/uv'
    if not uv.exists():
        installer = tools/'install-uv.sh'
        # Fixed uv release. Download to a file for review, never curl | shell.
        urllib.request.urlretrieve('https://astral.sh/uv/0.13.7/install.sh', installer)
        run(['sh', installer], env=env)
    rustup = tools/'cargo/bin/rustup'
    if not rustup.exists():
        installer = tools/'install-rustup.sh'
        urllib.request.urlretrieve('https://sh.rustup.rs', installer)
        run(['sh', installer, '-y', '--no-modify-path', '--profile', 'minimal', '--default-toolchain', '1.94.1'], env=env)
    else:
        run([rustup, 'toolchain', 'install', '1.94.1', '--profile', 'minimal'], env=env)
    revisions = json.loads((ROOT/'upstream-revisions.json').read_text())
    for name, revision in revisions.items():
        prepare_upstream(name, revision)
    run([uv, 'python', 'install', '3.12.16'], env=env)
    run([uv, 'sync', '--project', short/'microduck_rl', '--python', '3.12.16', '--locked'], env=env)
    run([ROOT/'microduck_rl/.venv/bin/python', '-c', 'import mujoco, numpy, PIL, onnxruntime; print("Python simulation dependencies OK")'], env=env)
    print('Setup complete. Start scripts/microduck-sim serve, then scripts/v7rc-bridge in another terminal.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
