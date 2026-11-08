"""Installed scene and walking-policy versions for the desktop console."""
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def program_version(root):
    manifest = read_json(root / '.installer-source.json')
    version = manifest.get('version') if isinstance(manifest, dict) else None
    if isinstance(version, str) and version:
        return version
    try:
        return (root / 'packaging/version.txt').read_text().strip() or 'dev'
    except OSError:
        return 'dev'


def content_root(root):
    if (root / '.installer-source.json').is_file():
        return root.parents[2] / 'content'
    return root / '.runtime/console-content'


def selected(root, kind):
    return read_json(content_root(root) / f'{kind}.json')


def scenes(root):
    result = {
        'free': {'title': '自由練習 / Free practice', 'path': None},
        'maze': {'title': 'S 型迷宮 / S maze', 'path': Path('scenes/maze.xml')},
    }
    result.update({
        item['id']: {'title': item['title'], 'path': Path(item['path'])}
        for item in selected(root, 'scenes').get('items', [])
        if Path(item['path']).is_file()
    })
    return result


def active_model(root):
    model = selected(root, 'model')
    path = Path(model['path']) if model.get('path') else None
    return (model['version'], path) if path and path.is_file() else ('bundled', None)


def scene_for_root(root, source, destination):
    """Resolve a downloaded scene against the active installation's MuJoCo assets."""
    base = root / 'microduck_rl/src/mjlab_microduck/robot/microduck'
    scene = ET.parse(source)
    scene.getroot().find('include').set('file', str(base / 'scene_backlash.xml'))
    scene.getroot().find('compiler').set('meshdir', str(base / 'assets'))
    scene.write(destination, encoding='utf-8')


def downloaded_options(root, kind, filename):
    """Discover retained downloads by the updater's version and digest directory format."""
    options = {}
    pattern = re.compile(rf'{kind}-(\d+\.\d+\.\d+(?:-preview\.\d+)?)-[a-f0-9]{{12}}')
    for path in sorted(content_root(root).glob(f'{kind}-*/{filename}')):
        match = pattern.fullmatch(path.parent.name)
        if match and path.is_file():
            options[path.parent.name] = (match[1], path)
    return options
