#!/usr/bin/env python3
"""Short local-only Camera757 receive test. Do not run while phone owns video."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import socket
import struct
import time
import base64

from PIL import Image

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seconds',type=float,default=5)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
state=json.loads((root/'.runtime/v7rc-video.json').read_text())
if state.get('active'):
    parser.error('A receiver is active; stop its camera before running this local test')
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(('127.0.0.1',0));s.settimeout(.1)
start=time.monotonic();next_probe=0;pending={};complete=[];last=None
while time.monotonic()-start<args.seconds:
    now=time.monotonic()
    if now>=next_probe:
        s.sendto(bytes.fromhex('ef000400'),('127.0.0.1',8800));next_probe=now+.5
    try:packet,source=s.recvfrom(2048)
    except socket.timeout:continue
    assert source[1]==1234 and packet[:2]==b'\x93\x01'
    assert struct.unpack_from('<H',packet,2)[0]==len(packet)
    frame_id=struct.unpack_from('<Q',packet,8)[0]
    index,count,total,width,height=struct.unpack_from('<IIIHH',packet,32)
    assert (width,height)==(640,360) and packet[48:50]==b'\xffE'
    parts=pending.setdefault(frame_id,{})
    parts[index]=packet
    if len(parts)==count:
        ordered=[parts[i] for i in range(count)]
        jpeg=b''.join(p[56:] for p in ordered)
        assert len(jpeg)==total
        im=Image.open(BytesIO(jpeg));im.load();assert im.size==(640,360)
        complete.append(frame_id);last=(jpeg,ordered)
        del pending[frame_id]
s.close()
assert last,'No decodable frames received'
output=root/'.runtime/camera757-check';output.mkdir(exist_ok=True)
(output/'latest.jpg').write_bytes(last[0])
(output/'vector-latest.json').write_text(json.dumps({'jpeg':base64.b64encode(last[0]).decode(),'packets':[base64.b64encode(p).decode() for p in last[1]]}))
report={'scope':'local client, not phone','frames':len(complete),'seconds':time.monotonic()-start,'width':640,'height':360,'last_fragments':len(last[1]),'last_jpeg_bytes':len(last[0])}
(output/'latest-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
