#!/usr/bin/env python3
"""Build a universal, ad-hoc signed preview .app and DMG without installing it."""
from pathlib import Path
import json
import plistlib
import shutil
import subprocess
import sys
import hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging'))
from make_payload import build, VERSION


def run(args):subprocess.run(list(map(str,args)),check=True)


def main():
    out=ROOT/'dist';out.mkdir(exist_ok=True);build(out/'payload.zip')
    app=out/'Microduck V7RC.app';contents=app/'Contents';resources=contents/'Resources';binary=contents/'MacOS'
    if app.exists():shutil.rmtree(app) # Only this build's generated output directory.
    resources.mkdir(parents=True);binary.mkdir()
    for source,name in [(out/'payload.zip','payload.zip'),(out/'payload.sha256','payload.sha256'),(ROOT/'packaging/version.txt','version.txt'),(ROOT/'packaging/ui.json','ui.json'),(ROOT/'packaging/assets/AppIcon.icns','AppIcon.icns'),(ROOT/'packaging/macos/install.command','install.command'),(ROOT/'docs/how-to.html','how-to.html')]:shutil.copy2(source,resources/name)
    for guide in ROOT.glob('docs/INSTALL.*.md'):shutil.copy2(guide,resources/guide.name)
    short_version, _, preview_number = VERSION.partition('-preview.')
    info={'CFBundleIdentifier':'com.v7rc.microduck-simulator','CFBundleName':'MicroduckV7RC','CFBundleDisplayName':'Microduck V7RC','CFBundleExecutable':'MicroduckV7RC','CFBundlePackageType':'APPL','CFBundleIconFile':'AppIcon.icns','CFBundleShortVersionString':short_version,'CFBundleVersion':preview_number or '1','LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True}
    with (contents/'Info.plist').open('wb') as f:plistlib.dump(info,f)
    parts=[]
    cache=ROOT/'.runtime/swift-installer-cache';cache.mkdir(parents=True,exist_ok=True)
    for arch in ['arm64','x86_64']:
        target=out/f'launcher-{arch}'
        run(['xcrun','swiftc','-swift-version','5','-O','-module-cache-path',cache,'-target',f'{arch}-apple-macos13.0',ROOT/'packaging/macos/Launcher.swift','-o',target]);parts.append(target)
    run(['lipo','-create',*parts,'-output',binary/'MicroduckV7RC'])
    run(['codesign','--force','--deep','--sign','-',app])
    run(['codesign','--verify','--deep','--strict',app])
    run([binary/'MicroduckV7RC','--self-test'])
    stage=out/'dmg-stage'
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir();shutil.copytree(app,stage/app.name);(stage/'Applications').symlink_to('/Applications')
    dmg=out/f'MicroduckV7RC-{VERSION}-macOS-universal.dmg'
    if dmg.exists():dmg.unlink()
    run(['hdiutil','create','-volname','Microduck V7RC','-srcfolder',stage,'-ov','-format','UDZO',dmg])
    run(['hdiutil','verify',dmg])
    (out/(dmg.name+'.sha256')).write_text(hashlib.sha256(dmg.read_bytes()).hexdigest()+'  '+dmg.name+'\n')
    print(dmg)


if __name__=='__main__':main()
