#!/usr/bin/env python3
"""Verify bundled application files before an installer executes them."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    manifest=json.loads((root/'.installer-source.json').read_text())
    for name,entry in manifest['files'].items():
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise RuntimeError('Unsafe installed path: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('Installed file differs from installer payload: '+name)
    return manifest


if __name__=='__main__':
    info=verify();print('Installer payload verified:',info['version'])
