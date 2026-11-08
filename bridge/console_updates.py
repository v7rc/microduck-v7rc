"""Check published GitHub releases and validate updates before activation."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

from console_content import content_root, selected
from control_profile import BUNDLED, active_profile, load_profile

REPO = 'v7rc/microduck-v7rc'
RELEASES = f'https://api.github.com/repos/{REPO}/releases?per_page=100'
VERSION = re.compile(r'v?(\d+)\.(\d+)\.(\d+)(?:-preview\.(\d+))?\Z')
IDENTIFIER = re.compile(r'[a-z][a-z0-9-]{0,39}\Z')


def version_key(value):
    match = VERSION.fullmatch(value)
    if not match:
        return None
    major, minor, patch, preview = match.groups()
    return int(major), int(minor), int(patch), preview is None, int(preview or 0)


def platform_suffix():
    return 'macOS-universal.dmg' if sys.platform == 'darwin' else 'Windows-x64.exe'


def download(url, limit, destination):
    if urlparse(url).scheme != 'https':
        raise ValueError('Expected an HTTPS GitHub URL')
    request = Request(url, headers={'User-Agent': 'MicroduckV7RC-Console'})
    digest = hashlib.sha256()
    size = 0
    with urlopen(request, timeout=20) as response:
        while chunk := response.read(128 * 1024):
            size += len(chunk)
            if size > limit:
                raise ValueError('Download exceeds size limit')
            digest.update(chunk)
            destination.write(chunk)
    return digest.hexdigest()


def candidates(root, version, releases):
    versions = {'program': version, **{
        kind: selected(root, kind).get('version', '0.0.0') for kind in ('scenes', 'model')
    }}
    versions['control'] = active_profile(root)[0] or version
    updates = {}
    for release in releases:
        tag = release.get('tag_name', '')
        key = version_key(tag)
        if release.get('draft') or not key or (
                (release.get('prerelease') or not key[3]) and '-preview.' not in version):
            continue
        assets = {asset['name']: asset for asset in release.get('assets', []) if asset.get('state') == 'uploaded'}
        names = {
            'program': f'MicroduckV7RC-{tag.removeprefix("v")}-{platform_suffix()}',
            'scenes': 'microduck-scenes.zip',
            'model': 'velstand.onnx',
            'control': 'control-profile.json',
        }
        for kind, name in names.items():
            if key <= (version_key(versions[kind]) or (0, 0, 0, False, 0)):
                continue
            if name not in assets or name + '.sha256' not in assets:
                continue
            if kind in updates and key <= version_key(updates[kind]['version']):
                continue
            prefix = f'https://github.com/{REPO}/releases/download/{tag}/'
            urls = [assets[n].get('browser_download_url') for n in (name, name+'.sha256')]
            if urls != [prefix + name, prefix + name + '.sha256']:
                continue
            updates[kind] = dict(version=tag.removeprefix('v'), name=name, url=urls[0], checksum=urls[1])
    return updates


def check(root, version):
    from io import BytesIO
    output = BytesIO()
    download(RELEASES, 8 * 1024 * 1024, output)
    return candidates(root, version, json.loads(output.getvalue()))


def validate_model(path):
    import numpy as np
    import onnxruntime as ort

    session = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
    inputs, outputs = session.get_inputs(), session.get_outputs()
    if ([(i.name, i.shape, i.type) for i in inputs] != [('obs', [1, 61], 'tensor(float)')]
            or [(i.name, i.shape, i.type) for i in outputs] != [('actions', [1, 14], 'tensor(float)')]):
        raise ValueError('Expected VelStand obs[1,61] → actions[1,14] float32')
    actions, = session.run(None, {'obs': np.zeros((1, 61), dtype=np.float32)})
    if not np.isfinite(actions).all():
        raise ValueError('Model produced non-finite actions')


def install_scenes(root, archive, stage):
    import mujoco

    base = root / 'microduck_rl/src/mjlab_microduck/robot/microduck'
    items = []
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > 51 or sum(e.file_size for e in entries) > 8 * 1024 * 1024:
            raise ValueError('Scene pack exceeds limits')
        if len({e.filename for e in entries}) != len(entries):
            raise ValueError('Duplicate entries in scene pack')
        manifest = json.loads(bundle.read('scenes.json'))
        if manifest.get('schema') != 1 or not 1 <= len(manifest['scenes']) <= 50:
            raise ValueError('Unsupported scene pack')
        identifiers = {'free', 'maze'}
        for item in manifest['scenes']:
            identifier, title = item['id'], item['title']
            if not IDENTIFIER.fullmatch(identifier) or identifier in identifiers or not 1 <= len(title) <= 80:
                raise ValueError('Invalid or duplicate scene')
            identifiers.add(identifier)
            fragment = ET.fromstring(bundle.read(f'{identifier}.xml'))
            if fragment.tag != 'worldbody' or fragment.attrib or any(
                geom.tag != 'geom' or len(geom) or geom.get('type') not in {'box','sphere','cylinder','capsule','ellipsoid'}
                or set(geom.attrib) - {'type','name','pos','size','quat','euler','rgba','contype','conaffinity','friction'}
                for geom in fragment
            ):
                raise ValueError('Scene pack accepts only primitive geoms inside worldbody')
            scene = ET.Element('mujoco', model=identifier)
            ET.SubElement(scene, 'include', file=str(base / 'scene_backlash.xml'))
            ET.SubElement(scene, 'compiler', meshdir=str(base / 'assets'))
            scene.append(fragment)
            name = identifier + '.xml'
            path = stage / name
            ET.ElementTree(scene).write(path, encoding='utf-8')
            mujoco.MjModel.from_xml_path(str(path))
            items.append(dict(id=identifier, title=title, name=name))
    return items


def install(root, kind, asset):
    from io import BytesIO

    base = content_root(root)
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix='update-') as temp:
        stage = Path(temp)
        checksum = BytesIO()
        download(asset['checksum'], 4096, checksum)
        match = re.match(rb'\s*([a-fA-F0-9]{64})(?:\s|$)', checksum.getvalue())
        payload = stage / asset['name']
        with payload.open('wb') as output:
            digest = download(asset['url'], {'program': 512 * 1024 * 1024, 'control': 16384}.get(kind, 64 * 1024 * 1024), output)
        if match is None or digest != match[1].decode().lower():
            raise ValueError('SHA256 mismatch')
        if kind == 'program':
            return open_installer(base, payload)
        receipt = dict(version=asset['version'])
        if kind == 'model':
            validate_model(payload)
        elif kind == 'control':
            if load_profile(payload)['schema'] < BUNDLED['schema']:
                raise ValueError('Control profile schema is older than the bundled profile')
        else:
            items = install_scenes(root, payload, stage)
            payload.unlink()
        # Publish the receipt only after all files have been validated.
        target = base / f"{kind}-{asset['version']}-{digest[:12]}"
        if not target.exists():
            stage.rename(target)
        if kind in ('model', 'control'):
            receipt['path'] = str(target / payload.name)
        else:
            receipt['items'] = [dict(id=i['id'], title=i['title'], path=str(target/i['name'])) for i in items]
        atomic_json(base / (kind+'.json'), receipt)
        return '已安裝。下次啟動時套用。'


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
        json.dump(value, handle)
    os.replace(handle.name, path)


def open_installer(base, payload):
    if sys.platform == 'darwin':
        target = base / payload.name
        os.replace(payload, target)
        subprocess.run(['open', str(target)], check=True)
    else:
        import shutil

        windows_temp = subprocess.check_output(
            ['powershell.exe', '-NoProfile', '-Command', '[System.IO.Path]::GetTempPath()'], text=True
        ).strip()
        linux_temp = subprocess.check_output(['wslpath', '-u', windows_temp], text=True).strip()
        directory = Path(tempfile.mkdtemp(prefix='MicroduckV7RC-', dir=linux_temp))
        target = directory / payload.name
        shutil.copyfile(payload, target)
        windows_path = subprocess.check_output(['wslpath', '-w', str(target)], text=True).strip()
        escaped = windows_path.replace("'", "''")
        command = base64.b64encode(f"Start-Process -FilePath '{escaped}'".encode('utf-16-le')).decode()
        subprocess.run(['powershell.exe', '-NoProfile', '-EncodedCommand', command], check=True)
    return '校驗完成，請在已開啟的安裝器完成更新。'
