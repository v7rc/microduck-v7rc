import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from console_content import selected
from console_updates import REPO, candidates, install
from control_profile import BUNDLED, load_profile
from v7rc_udp import Config, map_channels


class ControlProfileTests(unittest.TestCase):
    def test_control_only_release_applies_validated_tuning_and_preserves_it_on_failure(self):
        tag = 'v0.1.0-preview.6'
        prefix = f'https://github.com/{REPO}/releases/download/{tag}/'
        release = {'tag_name': tag, 'prerelease': True, 'assets': [
            {'name': name, 'state': 'uploaded', 'browser_download_url': prefix + name}
            for name in ('control-profile.json', 'control-profile.json.sha256')
        ]}
        profile = copy.deepcopy(BUNDLED)
        profile['turn_deadzone'] = .25
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = candidates(root, '0.1.0-preview.5', [release])['control']

            def fetch(url, limit, output):
                payload = json.dumps(profile).encode()
                digest = hashlib.sha256(payload).hexdigest()
                output.write(digest.encode() if url.endswith('.sha256') else payload)
                return digest

            with patch('console_updates.download', side_effect=fetch):
                install(root, 'control', asset)
                receipt = selected(root, 'control')
                cfg = Config(control=load_profile(Path(receipt['path'])))
                self.assertEqual(map_channels((1625, 1500, 1500, 1500), cfg)[0]['vyaw'], 0)
                self.assertFalse(candidates(root, '0.1.0-preview.5', [release]))
                profile['assist']['release'] = 0
                with self.assertRaises(ValueError):
                    install(root, 'control', {**asset, 'version': '0.1.0-preview.7'})
                self.assertEqual(selected(root, 'control'), receipt)
