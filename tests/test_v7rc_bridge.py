import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
from v7rc_udp import Config, InputState, axis, map_channels, parse_srt

NEUTRAL = b"SRT1500150015001500#"
FORWARD = b"SRT1500200015001500#"


class ProtocolTests(unittest.TestCase):
    def test_four_channels_in_order(self):
        self.assertEqual(parse_srt(b"SRT1000123417502000#", Config()), (1000, 1234, 1750, 2000))

    def test_reject_corrupt_datagrams_and_other_protocols(self):
        for frame in [b"", NEUTRAL[:-1], NEUTRAL+b"\n", NEUTRAL+b"\0", NEUTRAL*2,
                      b"SRV1500150015001500#", b"SRT150015001500150a#", b"SRT0999150015001500#",
                      b"SRT1500200115001500#", b"SRT1500150015001500\xff"]:
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                parse_srt(frame, Config())

    def test_center_and_deadzone(self):
        cfg = Config()
        for value in [1460, 1500, 1540]:
            self.assertEqual(axis(value, cfg), 0)
        self.assertAlmostEqual(axis(2000, cfg), 1)
        self.assertAlmostEqual(axis(1000, cfg), -1)
        self.assertGreater(axis(1541, cfg), 0)

    def test_channel_direction_limits_and_inversion(self):
        move, head = map_channels((2000, 2000, 2000, 2000), Config())
        self.assertEqual(move, {"vx": .3, "vy": 0, "vyaw": -.8})
        self.assertEqual(head, {"neck_pitch": 0, "head_pitch": -.25, "head_yaw": -.4, "head_roll": 0})
        reverse = map_channels((2000,)*4, Config(invert=(True,)*4))
        self.assertEqual(reverse[0], {"vx": -.3, "vy": 0, "vyaw": .8})
        self.assertEqual(reverse[1]["head_yaw"], .4)

    def test_non_symmetric_endpoints(self):
        cfg = Config(low=1000, center=1450, high=1900)
        self.assertEqual(axis(1000, cfg), -1)
        self.assertEqual(axis(1900, cfg), 1)
        self.assertEqual(axis(1450, cfg), 0)

    def test_ch3_pitch_and_ch4_yaw_are_independent(self):
        move, head = map_channels((1500, 1500, 2000, 1500), Config())
        self.assertEqual(move, {"vx": 0, "vy": 0, "vyaw": 0})
        self.assertEqual(head["head_pitch"], -.25)
        self.assertEqual(head["head_yaw"], 0)
        _, head = map_channels((1500, 1500, 1500, 2000), Config())
        self.assertEqual(head["head_pitch"], 0)
        self.assertEqual(head["head_yaw"], -.4)

    def test_startup_and_timeout_require_neutral(self):
        state = InputState(Config())
        self.assertFalse(state.accept(FORWARD, "phone", 1))
        self.assertIsNone(state.owner)
        self.assertTrue(state.accept(NEUTRAL, "phone", 2))
        self.assertTrue(state.accept(FORWARD, "phone", 2.1))
        self.assertFalse(state.expire(2.39))
        self.assertTrue(state.expire(2.41))
        self.assertFalse(state.accept(FORWARD, "phone", 2.42))
        self.assertTrue(state.accept(NEUTRAL, "phone", 2.43))

    def test_invalid_and_other_senders_do_not_refresh_watchdog(self):
        state = InputState(Config())
        state.accept(NEUTRAL, "phone", 1)
        self.assertFalse(state.accept(FORWARD, "other", 1.1))
        self.assertFalse(state.accept(b"bad", "phone", 1.2))
        self.assertEqual(state.last_at, 1)
        self.assertTrue(state.expire(1.31))
        self.assertEqual(state.owner, "phone")

    def test_explicit_source_ip(self):
        state = InputState(Config(), "phone")
        self.assertFalse(state.accept(NEUTRAL, "other", 1))
        self.assertTrue(state.accept(NEUTRAL, "phone", 1.1))


class BridgeProcessTests(unittest.TestCase):
    def test_udp_to_ipc_watchdog_rearm_reconnect_and_shutdown(self):
        with tempfile.TemporaryDirectory(prefix="md-v7-", dir="/tmp") as folder:
            path = str(Path(folder)/"robot.sock")
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(path)
            listener.listen()
            listener.settimeout(.1)
            messages, peers = [], []
            done = threading.Event()

            def handle(peer):
                try:
                    file = peer.makefile("r")
                    for line in file:
                        message = json.loads(line)
                        if message["method"] == "robot.health":
                            peer.sendall(json.dumps({"jsonrpc":"2.0", "id":1, "result":{"healthy":True}}).encode()+b"\n")
                        else:
                            messages.append((time.monotonic(), message))
                except OSError:
                    pass

            def server():
                while not done.is_set():
                    try:
                        peer, _ = listener.accept()
                        peers.append(peer)
                        threading.Thread(target=handle, args=(peer,), daemon=True).start()
                    except socket.timeout:
                        continue
                    except OSError:
                        break

            threading.Thread(target=server, daemon=True).start()
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.bind(("127.0.0.1",0)); port = probe.getsockname()[1]; probe.close()
            log = (Path(folder)/"bridge.log").open("w+")
            process = subprocess.Popen([sys.executable, str(ROOT/"bridge/v7rc_udp.py"), "--bind","127.0.0.1", "--port",str(port),"--socket",path,
                                        "--telemetry-file",str(Path(folder)/"input.json")], stdout=log, stderr=log)

            def wait_for(predicate, timeout=3):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    if predicate(): return
                    if process.poll() is not None: self.fail("Bridge exited unexpectedly")
                    time.sleep(.01)
                self.fail("Timed out waiting for bridge state")

            def send(payload):
                udp.sendto(payload,("127.0.0.1",port))

            def moves():
                return [(t,m['params']['vx']) for t,m in messages if m['method']=='robot.move']

            def arm():
                for _ in range(3): send(NEUTRAL);time.sleep(.03)

            try:
                wait_for(lambda: bool(moves()))
                send(FORWARD);time.sleep(.1)
                self.assertTrue(all(v==0 for _,v in moves()))
                arm();send(FORWARD)
                wait_for(lambda: any(v==.3 for _,v in moves()))
                last_sent=time.monotonic()
                # Bad traffic continues; it must not prolong the last valid movement.
                while time.monotonic()-last_sent<.5: send(b"invalid");time.sleep(.02)
                wait_for(lambda: moves()[-1][1]==0)
                stop_at=moves()[-1][0]
                self.assertLess(stop_at-last_sent,.45)
                mark=len(moves());send(FORWARD);time.sleep(.15)
                self.assertFalse(any(v!=0 for _,v in moves()[mark:]))
                arm();send(FORWARD)
                wait_for(lambda: moves()[-1][1]==.3)
                for peer in list(peers): peer.shutdown(socket.SHUT_RDWR);peer.close()
                wait_for(lambda: len(peers)>1)
                mark=len(moves());send(FORWARD);time.sleep(.15)
                self.assertFalse(any(v!=0 for _,v in moves()[mark:]))
                arm();send(FORWARD);wait_for(lambda: moves()[-1][1]==.3)
                process.terminate();process.wait(timeout=3)
                self.assertEqual(process.returncode,0)
                self.assertEqual(moves()[-1][1],0)
            finally:
                if process.poll() is None:process.terminate();process.wait(timeout=3)
                udp.close();done.set();listener.close();log.close()


if __name__ == "__main__":
    unittest.main()
