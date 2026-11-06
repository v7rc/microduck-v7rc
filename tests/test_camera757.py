from io import BytesIO
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import time
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from camera757 import Camera757Server, Session, classify_control, packetize


def feedback():
    data=bytearray(88);data[:2]=b'\xef\x02'
    struct.pack_into('<HI',data,2,88,0x01000202)
    return bytes(data)


class Camera757Tests(unittest.TestCase):
    def test_header_and_fragment_boundaries(self):
        for size in [4,1024,1025,1026,262144]:
            jpeg=b'\xff\xd8'+bytes(size-4)+b'\xff\xd9'
            packets=list(packetize(jpeg,73))
            self.assertEqual(len(packets),(size+1023)//1024)
            self.assertEqual(b''.join(p[56:] for p in packets),jpeg)
            for i,p in enumerate(packets):
                self.assertEqual(p[:2],b'\x93\x01')
                self.assertEqual(struct.unpack_from('<H',p,2)[0],len(p))
                self.assertEqual(struct.unpack_from('<QQQIIIHH',p,8),(73,73,72,i,len(packets),size,640,360))
                self.assertEqual(p[48:50],b'\xff\x45')

    def test_invalid_image_and_id(self):
        for jpeg in [b'',b'1234',b'\xff\xd8'+bytes(262144)+b'\xff\xd9']:
            with self.assertRaises(ValueError):list(packetize(jpeg,1))
        with self.assertRaises(ValueError):list(packetize(b'\xff\xd8\xff\xd9',0))

    def test_control_and_single_peer_timeout(self):
        probe=b'\xef\x00\x04\x00';a=('phone',100);b=('other',200)
        self.assertEqual(classify_control(probe),'probe')
        self.assertEqual(classify_control(feedback()),'status')
        self.assertIsNone(classify_control(feedback()[:-1]))
        session=Session()
        self.assertFalse(session.accept(feedback(),a,1))
        self.assertTrue(session.accept(probe,a,1))
        self.assertFalse(session.accept(probe,b,2))
        self.assertFalse(session.accept(feedback(),b,2.5))
        self.assertTrue(session.accept(feedback(),a,3))
        self.assertTrue(session.active(5.9))
        self.assertFalse(session.active(6.1))
        self.assertTrue(session.accept(probe,b,6.2))

    def test_real_udp_roundtrip_decodable_jpeg_and_expiry(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as folder:
            server=Camera757Server(Path(folder)/'video.json',command_port=0,source_port=0)
            client=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);client.bind(('127.0.0.1',0));client.settimeout(2)
            endpoint=('127.0.0.1',server.command.getsockname()[1])
            try:
                client.sendto(b'\xef\x00\x04\x00',endpoint)
                deadline=time.monotonic()+2
                while not server.wants_frame() and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(server.wants_frame())
                rgb=np.zeros((360,640,3),dtype=np.uint8);rgb[:180,:,0]=220;rgb[180:,:,2]=220
                server.publish(rgb)
                parts={};count=None
                while count is None or len(parts)<count:
                    packet,source=client.recvfrom(2048)
                    self.assertEqual(source[1],server.video.getsockname()[1])
                    index,count,total=struct.unpack_from('<III',packet,32);parts[index]=packet[56:]
                jpeg=b''.join(parts[i] for i in range(count))
                self.assertEqual(len(jpeg),total)
                image=Image.open(BytesIO(jpeg));self.assertEqual(image.size,(640,360));image.load()
                self.assertGreater(image.getpixel((50,50))[0],150)
                self.assertGreater(image.getpixel((50,300))[2],150)
                # Force only the isolated test session clock to expire; no live stream touched.
                server.session.last_control=time.monotonic()-4
                self.assertFalse(server.wants_frame())
                with self.assertRaises(ValueError):server.publish(rgb[:100])
            finally:client.close();server.close()


if __name__=='__main__':unittest.main()
