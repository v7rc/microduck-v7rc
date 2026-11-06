import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'bridge'))
import platform_support as support
spec = importlib.util.spec_from_file_location('setup_program', ROOT/'scripts/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class PlatformTests(unittest.TestCase):
    def test_owned_short_path_and_socket_are_consistent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'repo with spaces'; root.mkdir()
            short = Path(folder)/'short'
            with patch.dict(os.environ, {'MICRODUCK_SHORT_ROOT': str(short)}, clear=True):
                self.assertEqual(support.ensure_short_root(root), short)
                self.assertEqual(short.resolve(), root.resolve())
                self.assertEqual(support.robot_socket(root), short/'.runtime/duck-sim/duck-a.sock')
                self.assertEqual(support.ensure_short_root(root), short)
                other = Path(folder)/'other'; other.mkdir()
                with self.assertRaises(RuntimeError): support.ensure_short_root(other)
                self.assertEqual(short.resolve(), root.resolve())

    def test_short_path_rejects_regular_files_and_long_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'taken'; target.write_text('keep')
            with patch.dict(os.environ, {'MICRODUCK_SHORT_ROOT': str(target)}, clear=True):
                with self.assertRaises(RuntimeError): support.ensure_short_root(folder)
                self.assertEqual(target.read_text(), 'keep')
            with patch.dict(os.environ, {'MICRODUCK_SHORT_ROOT': '/tmp/'+'x'*100}, clear=True):
                with self.assertRaises(ValueError): support.short_root(folder)

    def test_linux_ip_selection_ignores_vpn_and_prefers_wifi(self):
        rows = [{'ifname':'tun0','addr_info':[{'local':'10.9.0.2'}]},
                {'ifname':'eth0','addr_info':[{'local':'192.168.1.2'}]},
                {'ifname':'wlan0','addr_info':[{'local':'192.168.2.3'}]}]
        with patch.dict(os.environ, {}, clear=True), patch.object(support.platform,'system',return_value='Linux'), patch.object(support.subprocess,'check_output',return_value=json.dumps(rows)):
            self.assertEqual(support.advertised_ip(), '192.168.2.3')

    def test_explicit_advertise_ip_and_invalid_override(self):
        with patch.dict(os.environ, {'MICRODUCK_ADVERTISE_IP':'192.168.3.4'}):
            self.assertEqual(support.advertised_ip(), '192.168.3.4')
        with patch.dict(os.environ, {'MICRODUCK_ADVERTISE_IP':'127.0.0.1'}):
            self.assertEqual(support.advertised_ip(), 'Invalid IP override')
        with patch.dict(os.environ, {}, clear=True), patch.object(support.subprocess,'check_output',side_effect=OSError()):
            self.assertIn('MICRODUCK_ADVERTISE_IP', support.advertised_ip())

    def test_installer_preserves_wrong_revision_and_patches_idempotently(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); repo=root/'fake';repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL,text=True)
            git('init'); (repo/'file.txt').write_text('before\n');git('add','file.txt')
            git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture')
            head=git('rev-parse','HEAD').strip()
            (repo/'file.txt').write_text('after\n'); diff=git('diff');(root/'fixture.patch').write_text(diff);(repo/'file.txt').write_text('before\n')
            (repo/'unrelated.txt').write_text('keep user work')
            with patch.object(setup,'ROOT',root):
                with self.assertRaises(RuntimeError):setup.prepare_upstream('fake',{'commit':'0'*40})
                self.assertEqual(git('rev-parse','HEAD').strip(),head)
                revision={'commit':head,'patch':'fixture.patch'}
                setup.prepare_upstream('fake',revision);setup.prepare_upstream('fake',revision)
            self.assertEqual((repo/'file.txt').read_text(),'after\n')
            self.assertEqual((repo/'unrelated.txt').read_text(),'keep user work')


if __name__ == '__main__': unittest.main()
