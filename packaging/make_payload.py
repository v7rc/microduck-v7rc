#!/usr/bin/env python3
"""Create an allowlisted installer payload; exclude upstreams, credentials and runtime state."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import stat
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'packaging/version.txt').read_text().strip()


def sources():
    files=[]
    for folder in ['bridge','scripts','patches','windows']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.is_symlink())
    files += [ROOT/'scenes/maze.xml',ROOT/'upstream-revisions.json',ROOT/'README.md',*ROOT.glob('README.*.md'),ROOT/'docs/how-to.html',ROOT/'docs/desktop-console.html',ROOT/'docs/integration/desktop-console-todo.html',*ROOT.glob('docs/INSTALL.*.md')]
    return sorted(set(files))


def content(path):
    # Every allowlisted payload file is text. Never ship Windows CRLF to /bin/sh.
    return path.read_bytes().replace(b'\r\n',b'\n')


def source_commit():
    result=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,capture_output=True)
    return result.stdout.strip() if result.returncode==0 else 'source-archive'


def build(output):
    files=sources()
    manifest={'version':VERSION,'source_commit':source_commit(),
              'files':{p.relative_to(ROOT).as_posix():{'sha256':hashlib.sha256(content(p)).hexdigest(),'executable':p.relative_to(ROOT).parts[0]=='scripts'} for p in files}}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            name=p.relative_to(ROOT).as_posix()
            entry=zipfile.ZipInfo(name)
            entry.create_system=3
            entry.external_attr=(stat.S_IFREG | (0o755 if manifest['files'][name]['executable'] else 0o644)) << 16
            entry.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(entry,content(p))
        z.writestr('.installer-source.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256').write_text(digest+'\n')
    print(json.dumps({'version':VERSION,'files':len(files),'bytes':output.stat().st_size,'sha256':digest}))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    build(parser.parse_args().output)
