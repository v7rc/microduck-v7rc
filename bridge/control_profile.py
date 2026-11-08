"""Validate the data-only control profile shared by the updater and SRT bridge."""
import json
import math
from pathlib import Path

from console_content import downloaded_options, selected

CURVES = {'forward', 'reverse', 'left', 'right'}
ASSIST_LIMITS = {
    'forward_travel': (0.001, 1), 'reverse_travel': (0.001, 1),
    'turn_travel': (0.001, 1), 'right_limit': (0, 1),
    'hold': (0, 2), 'release': (0.01, 2),
    'reverse_hold': (0, 2), 'reverse_release': (0.01, 2),
    'diagonal_ramp': (0.01, 2), 'yaw_ramp': (0.01, 2),
}


def in_range(value, minimum, maximum):
    return type(value) in (int, float) and minimum <= value <= maximum and math.isfinite(value)


def load_profile(path):
    with path.open('rb') as source:
        contents = source.read(16385)
    if len(contents) > 16384:
        raise ValueError('Control profile exceeds 16 KiB')
    profile = json.loads(contents)
    if (not isinstance(profile, dict) or set(profile) != {'schema', 'turn_deadzone', 'curves', 'assist'}
            or type(profile['schema']) is not int or profile['schema'] not in (1, 2)):
        raise ValueError('Unsupported control profile schema')
    if not in_range(profile['turn_deadzone'], 0, .49):
        raise ValueError('Invalid turn deadzone')
    curves = profile['curves']
    expected_curves = CURVES | {'right_diagonal'} if profile['schema'] == 2 else CURVES
    if not isinstance(curves, dict) or curves.keys() != expected_curves:
        raise ValueError('Drive curves do not match the control profile schema')
    for name, points in curves.items():
        if (not isinstance(points, list) or not 2 <= len(points) <= 32
                or any(not isinstance(point, list) or len(point) != 2
                       or not all(in_range(value, 0, 1) for value in point) for point in points)
                or points[0] != [0, 0] or points[-1][0] != 1
                or any(a[0] >= b[0] or a[1] > b[1] for a, b in zip(points, points[1:]))):
            raise ValueError(f'Invalid {name} curve')
    assist = profile['assist']
    if (not isinstance(assist, dict) or assist.keys() != ASSIST_LIMITS.keys()
            or any(not in_range(assist[key], *limits) for key, limits in ASSIST_LIMITS.items())):
        raise ValueError('Invalid start-assist parameters')
    return profile


BUNDLED = load_profile(Path(__file__).with_name('control-profile.json'))


def active_profile(root):
    """Keep older settings available for older installs without masking a new schema."""
    receipt = selected(root, 'control')
    if receipt:
        profile = load_profile(Path(receipt['path']))
        if profile['schema'] >= BUNDLED['schema']:
            return receipt['version'], profile
    return None, BUNDLED


def control_options(root):
    options = {'auto': '自動選用目前設定', 'bundled': '內建曲線', 'linear': '線性曲線'}
    for key, (version, path) in downloaded_options(root, 'control', 'control-profile.json').items():
        try:
            profile = load_profile(path)
        except (OSError, ValueError):
            continue
        options[key] = f'控制設定 {version} · Schema {profile["schema"]}'
    return options
