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
from v7rc_udp import Config, GaitStart, InputState, axis, map_channels, parse_srt

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

    def test_calibrated_start_fades_and_does_not_repeat_while_held(self):
        cfg = Config(drive_profile="velstand-v8")
        start = GaitStart()
        channels = (1500, 1625, 1500, 1500)
        move, _ = map_channels(channels, cfg)
        self.assertAlmostEqual(start.apply(move, channels, cfg, 10)["vx"], .3)
        self.assertEqual(start.apply(move, channels, cfg, 12), move)
        self.assertEqual(start.apply(move, channels, cfg, 20), move)
        center = (1500,) * 4
        neutral, _ = map_channels(center, cfg)
        self.assertEqual(start.apply(neutral, center, cfg, 21), neutral)
        self.assertAlmostEqual(start.apply(move, channels, cfg, 22)["vx"], .3)

    def test_turn_deadzone_is_inclusive_and_keeps_forward_input(self):
        for profile in ("linear", "velstand-v8"):
            cfg = Config(drive_profile=profile)
            for steering in (1400, 1425, 1500, 1575, 1600):
                move, _ = map_channels((steering, 1575, 1500, 1500), cfg)
                self.assertEqual(move["vyaw"], 0)
                self.assertGreater(move["vx"], 0)
            self.assertGreater(map_channels((1399, 1500, 1500, 1500), cfg)[0]["vyaw"], 0)
            self.assertLess(map_channels((1601, 1500, 1500, 1500), cfg)[0]["vyaw"], 0)

    def test_diagonal_assist_ramps_then_settles_and_reversal_cancels_it(self):
        cfg = Config(drive_profile="velstand-v8")
        start = GaitStart()
        mixed = (1625, 1625, 1500, 1500)
        move, _ = map_channels(mixed, cfg)
        first = start.apply(move, mixed, cfg, 10)
        self.assertEqual(first["vx"], move["vx"])
        self.assertEqual(first["vyaw"], 0)
        rising = start.apply(move, mixed, cfg, 10.15)
        self.assertGreater(rising["vx"], move["vx"])
        self.assertTrue(move["vyaw"] < rising["vyaw"] < 0)
        self.assertEqual(start.apply(move, mixed, cfg, 11), move)

        start.reset()
        start.apply(move, mixed, cfg, 12)
        reverse = (1625, 1375, 1500, 1500)
        reverse_move, _ = map_channels(reverse, cfg)
        self.assertEqual(start.apply(reverse_move, reverse, cfg, 12.1), reverse_move)
        self.assertEqual(start.apply(move, mixed, cfg, 12.2), move)

    def test_steering_added_during_forward_start_ramps_from_entry(self):
        cfg = Config(drive_profile="velstand-v8")
        start = GaitStart()
        forward = (1500, 1625, 1500, 1500)
        diagonal = (1375, 1625, 1500, 1500)
        start.apply(map_channels(forward, cfg)[0], forward, cfg, 10)
        move = map_channels(diagonal, cfg)[0]
        self.assertEqual(start.apply(move, diagonal, cfg, 10.2)["vyaw"], 0)
        self.assertGreater(start.apply(move, diagonal, cfg, 10.4)["vyaw"], 0)
        self.assertEqual(start.apply(move, diagonal, cfg, 11), move)

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
