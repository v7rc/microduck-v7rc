import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import signal
import shlex
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
payload=module('installer_payload',ROOT/'packaging/make_payload.py')
verify=module('verify_installation',ROOT/'scripts/verify-installation.py')


class InstallerTests(unittest.TestCase):
 def test_payload_contains_only_application_sources_and_detects_tampering(self):
  with tempfile.TemporaryDirectory() as folder:
   out=Path(folder)/'payload.zip';payload.build(out)
   with zipfile.ZipFile(out) as z:
    names=z.namelist();self.assertIn('scripts/desktop.py',names)
    self.assertTrue(z.getinfo('scripts/setup').external_attr >> 16 & 0o111)
    self.assertFalse(any('\\' in n for n in names))
    self.assertFalse(any(n.split('/')[0] in {'.runtime','.tools','microduck','microduck_rl','.git'} for n in names))
    self.assertFalse(any(n.startswith('/') or '..' in Path(n).parts for n in names))
    target=Path(folder)/'application';z.extractall(target)
   info=verify.verify(target);self.assertEqual(info['version'],payload.VERSION)
   p=target/'bridge/camera757.py';p.write_text(p.read_text()+'\n# changed\n')
   with self.assertRaises(RuntimeError):verify.verify(target)

 def test_payload_normalizes_windows_shell_newlines(self):
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'script';source.write_bytes(b'#!/bin/sh\r\necho ok\r\n')
   self.assertEqual(payload.content(source),b'#!/bin/sh\necho ok\n')

 def test_four_installer_languages_have_matching_keys(self):
  values=json.loads((ROOT/'packaging/ui.json').read_text())
  self.assertEqual(set(values),{'zh-TW','zh-CN','en','ja'})
  for texts in values.values():
   self.assertEqual(set(texts),set(values['en']))
   self.assertTrue(all(texts.values()))

 def test_desktop_shutdown_requests_neutral_and_stops_owned_simulator(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'scripts').mkdir();(root/'.runtime').mkdir()
   sim=root/'scripts/microduck-sim'
   sim.write_text('#!/bin/sh\nif [ "$1" = down ]; then touch .runtime/down-ack; exit 0; fi\ntrap "exit 0" TERM\nwhile :; do sleep 1; done\n');sim.chmod(0o755)
   bridge=root/'scripts/v7rc-bridge'
   fake=root/'fake_bridge.py'
   fake.write_text('import signal,time,json\nfrom pathlib import Path\ndef stop(*_):\n Path(".runtime/neutral-ack").write_text("neutral")\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\nwhile True:\n Path(".runtime/v7rc-input.json").write_text(json.dumps({"robot_connected":True,"published_monotonic":time.monotonic()}))\n time.sleep(.1)\n')
   bridge.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(fake))+'\n');bridge.chmod(0o755)
   driver=("import importlib.util,sys;from pathlib import Path;"
           "s=importlib.util.spec_from_file_location('desktop',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
           "m.ROOT=Path.cwd();m.STATE=m.ROOT/'.runtime/desktop-session.json';m.port_conflicts=lambda:[];sys.argv=['desktop'];m.main()")
   p=subprocess.Popen([sys.executable,'-c',driver,str(ROOT/'scripts/desktop.py')],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   try:
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
     try:
      if json.loads((root/'.runtime/desktop-session.json').read_text())['status']=='running':break
     except (OSError,ValueError):pass
     time.sleep(.1)
    else:self.fail('Supervisor did not reach running')
    p.send_signal(signal.SIGHUP);self.assertEqual(p.wait(timeout=10),0)
    self.assertTrue((root/'.runtime/neutral-ack').is_file())
    self.assertTrue((root/'.runtime/down-ack').is_file())
    self.assertEqual(json.loads((root/'.runtime/desktop-session.json').read_text())['status'],'stopped')
   finally:
    if p.poll() is None:p.terminate();p.wait(timeout=10)

 @unittest.skipUnless(platform.system()=='Linux','Linux installer script targets Ubuntu')
 def test_linux_setup_failure_never_writes_success_and_success_is_verified(self):
  with tempfile.TemporaryDirectory() as folder:
   work=Path(folder);stubs=work/'bin';stubs.mkdir()
   for name,text in {'id':'#!/bin/sh\nprintf 1000','dpkg-query':'#!/bin/sh\nprintf "install ok installed\\n"'}.items():
    p=stubs/name;p.write_text(text);p.chmod(0o755)
   (stubs/'python3').symlink_to(sys.executable)
   env=os.environ.copy();env['PATH']=str(stubs)+os.pathsep+env['PATH']
   for code in [7,0]:
    source=work/f'source-{code}';(source/'scripts').mkdir(parents=True)
    setup=source/'scripts/setup';setup.write_text(f'#!/bin/sh\nexit {code}\n');setup.chmod(0o755)
    checker=source/'scripts/verify-installation.py';checker.write_bytes((ROOT/'scripts/verify-installation.py').read_bytes())
    files={str(p.relative_to(source)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [setup,checker]}
    (source/'.installer-source.json').write_text(json.dumps({'version':'test','files':files}))
    package=work/f'package-{code}.zip'
    with zipfile.ZipFile(package,'w') as z:
     for p in source.rglob('*'):
      if p.is_file():z.write(p,p.relative_to(source))
    target=work/f'target-{code}'
    result=subprocess.run(['bash',str(ROOT/'packaging/common/install-linux.sh'),str(package),str(target),'test','--approved'],env=env,text=True,capture_output=True)
    receipt=json.loads((target/'.install-ready.json').read_text())
    self.assertEqual(result.returncode,code,result.stdout+result.stderr)
    self.assertEqual(receipt['ready'],code==0)


if __name__=='__main__':unittest.main()
