"""Camera757 complete-JPEG wire format, based on local ESP32/Ameba/SDK contracts."""
from collections import deque
from io import BytesIO
import json
import logging
from pathlib import Path
import select
import socket
import struct
import threading
import time

from PIL import Image

LOG = logging.getLogger('camera757')


def classify_control(data):
    if data == bytes.fromhex('ef000400'):
        return 'probe'
    if (88 <= len(data) <= 808 and data[:2] == bytes.fromhex('ef02')
            and struct.unpack_from('<H',data,2)[0] == len(data)
            and data[4:8] == bytes.fromhex('02020001')):
        return 'status'
    return None


def packetize(jpeg, frame_id):
    if not (4 <= len(jpeg) <= 256*1024 and jpeg[:2] == b'\xff\xd8' and jpeg[-2:] == b'\xff\xd9'):
        raise ValueError('Complete JPEG required, max 256 KiB')
    if not 0 < frame_id < 2**64:
        raise ValueError('Frame ID must be nonzero uint64')
    count = (len(jpeg)+1023)//1024
    for index in range(count):
        part=jpeg[index*1024:(index+1)*1024]
        header=bytearray(56)
        struct.pack_into('<BBHIQQQIIIHH',header,0,0x93,1,56+len(part),0x01000202,
                         frame_id,frame_id,frame_id-1,index,count,len(jpeg),640,360)
        header[48:50]=b'\xff\x45'  # Existing SDK's complete-JPEG extension, not a scan template.
        header[50]=header[52]=1
        yield bytes(header)+part


class Session:
    def __init__(self):
        self.peer=None
        self.last_control=-float('inf')

    def active(self,now):
        return self.peer is not None and 0 <= now-self.last_control < 3

    def accept(self,data,sender,now):
        kind=classify_control(data)
        if kind=='probe' and (not self.active(now) or sender==self.peer):
            self.peer=sender;self.last_control=now;return True
        if kind=='status' and self.active(now) and sender==self.peer:
            self.last_control=now;return True
        return False


class Camera757Server:
    def __init__(self,state_path,command_port=8800,source_port=1234,quality=70):
        self.state_path=Path(state_path)
        self.quality=quality
        self.command=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.video=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            self.command.bind(('0.0.0.0',command_port))
            self.video.bind(('0.0.0.0',source_port))
            self.command.setblocking(False)
            self.video.settimeout(.1)
        except Exception:
            self.command.close();self.video.close();raise
        self.session=Session()
        self.slot=None
        self.lock=threading.Lock()
        self.stopped=threading.Event()
        self.frames=self.packets=self.invalid=self.dropped=0
        self.probes=self.feedback=0
        self.last_datagram=None
        self.frame_times=deque()
        self.command_port=command_port;self.source_port=source_port
        self.frame_id=time.time_ns()
        self.thread=threading.Thread(target=self.run,name='camera757',daemon=True)
        self.thread.start()
        print(f'== V7RC video: UDP {command_port}, source {source_port}, JPEG FF/45 640x360',flush=True)

    def wants_frame(self):
        return not self.stopped.is_set() and self.session.active(time.monotonic())

    def publish(self,rgb):
        if getattr(rgb,'shape',None)!=(360,640,3) or str(rgb.dtype)!='uint8':
            raise ValueError('Camera757 requires actual RGB uint8 640x360 pixels')
        with self.lock:
            if self.slot is not None:self.dropped+=1
            self.slot=(rgb,self.session.peer)

    def poll(self):
        for _ in range(32):
            try:data,sender=self.command.recvfrom(2048)
            except BlockingIOError:return
            old=self.session.peer
            kind=classify_control(data)
            self.last_datagram={'sender':sender,'bytes':len(data),'prefix_hex':data[:8].hex(),
                                'kind':kind,'monotonic':time.monotonic()}
            if self.session.accept(data,sender,time.monotonic()):
                if kind=='probe':self.probes+=1
                elif kind=='status':self.feedback+=1
                if old!=self.session.peer:print(f'== V7RC video peer: {sender[0]}:{sender[1]}',flush=True)
            else:self.invalid+=1

    def run(self):
        next_stats=0
        try:
            while not self.stopped.is_set():
                select.select([self.command],[],[],.01)
                self.poll()
                now=time.monotonic()
                if self.session.active(now):
                    with self.lock:
                        item,self.slot=self.slot,None
                    if item and item[1]==self.session.peer:
                        rgb,peer=item
                        output=BytesIO()
                        Image.fromarray(rgb).save(output,format='JPEG',quality=self.quality)
                        jpeg=output.getvalue()
                        self.frame_id+=1
                        if len(jpeg)<=256*1024:
                            sent=True
                            for i,packet in enumerate(packetize(jpeg,self.frame_id)):
                                if not self.session.active(time.monotonic()) or peer!=self.session.peer:
                                    sent=False;break
                                self.video.sendto(packet,peer);self.packets+=1
                                if i%8==7:self.poll();time.sleep(.001)
                            if sent:self.frames+=1;self.frame_times.append(time.monotonic())
                else:
                    with self.lock:self.slot=None
                if now>=next_stats:
                    while self.frame_times and self.frame_times[0]<=now-1:self.frame_times.popleft()
                    status={'published_monotonic':now,'active':self.session.active(now),'peer':self.session.peer,
                            'command_port':self.command_port,'source_port':self.source_port,
                            'frames':self.frames,'packets':self.packets,'tx_fps':len(self.frame_times),'invalid':self.invalid,
                            'probes':self.probes,'feedback':self.feedback,'last_datagram':self.last_datagram}
                    self.state_path.parent.mkdir(parents=True,exist_ok=True)
                    temporary=self.state_path.with_suffix('.tmp');temporary.write_text(json.dumps(status)+'\n');temporary.replace(self.state_path)
                    next_stats=now+.5
        except Exception as error:
            print(f'== V7RC video error: {error}',flush=True)
            self.stopped.set()
        finally:
            self.command.close();self.video.close()

    def close(self):
        self.stopped.set();self.thread.join(timeout=2)
