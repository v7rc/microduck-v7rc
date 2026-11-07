#!/usr/bin/env python3
"""V7RC SRT datagrams to Microduck robotd; Python standard library only."""
from platform_support import robot_socket

import argparse
from collections import deque
from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import re
import select
import signal
import socket
import time

LOG = logging.getLogger("v7rc")
FRAME = re.compile(rb"SRT([0-9]{4})([0-9]{4})([0-9]{4})([0-9]{4})#")

# Input fractions are after the default 8% deadzone. Output fractions scale
# with the configured limits, using the flat MuJoCo velstand v8 measurements.
REVERSE_CURVE = ((0, 0), (17 / 92, .185 / .3), (42 / 92, .22 / .3),
                 (67 / 92, .26 / .3), (1, 1))
FORWARD_CURVE = ((0, 0), (17 / 92, .102 / .3), (42 / 92, .145 / .3),
                 (67 / 92, .213 / .3), (1, 1))
LEFT_CURVE = ((0, 0), (17 / 92, .22 / .8), (42 / 92, 42 / 92), (1, 1))
RIGHT_CURVE = ((0, 0), (17 / 92, .165 / .8), (42 / 92, .21 / .8),
               (67 / 92, .42 / .8), (1, .9))


def interpolate_curve(travel, points):
    for (left, low), (right, high) in zip(points, points[1:]):
        if travel <= right:
            return low + (high - low) * (travel - left) / (right - left)
    return points[-1][1]


@dataclass(frozen=True)
class Config:
    low: int = 1000
    center: int = 1500
    high: int = 2000
    deadzone: float = 0.08
    max_forward: float = 0.3
    max_turn: float = 0.8
    max_head_yaw: float = 0.4
    max_head_pitch: float = 0.25
    invert: tuple = (False, False, False, False)
    timeout: float = 0.3
    drive_profile: str = "linear"


def parse_srt(payload, cfg):
    match = FRAME.fullmatch(payload)
    if match is None:
        raise ValueError("Expected exactly 20 ASCII bytes: SRT + four 4-digit channels + #")
    channels = tuple(int(value) for value in match.groups())
    if any(not cfg.low <= value <= cfg.high for value in channels):
        raise ValueError("Channel outside configured PWM range")
    return channels


def axis(value, cfg):
    span = cfg.high - cfg.center if value >= cfg.center else cfg.center - cfg.low
    value = (value - cfg.center) / span
    if abs(value) <= cfg.deadzone:
        return 0.0
    return math.copysign((abs(value) - cfg.deadzone) / (1 - cfg.deadzone), value)


def map_channels(channels, cfg):
    a = tuple(axis(value, cfg) * (-1 if cfg.invert[i] else 1) for i, value in enumerate(channels))
    # Increasing steering/head-yaw PWM means right; robotd's positive yaw means left.
    move = {"vx": a[1] * cfg.max_forward, "vy": 0.0, "vyaw": -a[0] * cfg.max_turn}
    if cfg.drive_profile == "velstand-v8":
        travel = abs(a[1])
        forward_curve = REVERSE_CURVE if a[1] < 0 else FORWARD_CURVE
        yaw_curve = RIGHT_CURVE if a[0] > 0 else LEFT_CURVE
        move["vx"] = math.copysign(cfg.max_forward * interpolate_curve(travel, forward_curve), a[1])
        move["vyaw"] = math.copysign(cfg.max_turn * interpolate_curve(abs(a[0]), yaw_curve), -a[0])
    head = {"neck_pitch": 0.0, "head_pitch": -a[2] * cfg.max_head_pitch,
            "head_yaw": -a[3] * cfg.max_head_yaw, "head_roll": 0.0}
    return move, head


class GaitStart:
    """Briefly bring the simulated velstand policy out of its standing gait."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.direction = None
        self.started = None
        self.mixed = False

    def apply(self, move, channels, cfg, now):
        if cfg.drive_profile != "velstand-v8":
            return move
        active = [axis for axis in ("vx", "vyaw") if move[axis]]
        if not active:
            self.reset()
            return move
        if len(active) > 1:
            self.mixed = True
            return move
        component = active[0]
        target = move[component]
        direction = (component, target > 0)
        limit = cfg.max_forward if component == "vx" else cfg.max_turn
        if component == "vyaw" and target < 0:
            limit = max(abs(target), limit * 0.825)
        travel = abs(axis(channels[1 if component == "vx" else 0], cfg))
        # At 25% raw stick travel, the default deadzone leaves about 18.5%.
        # Smaller inputs receive a proportionally smaller assist.
        assist = min(1.0, travel / 0.18)
        if direction != self.direction:
            self.started = now if self.direction is None and not self.mixed else None
            self.direction = direction
        if self.started is None or self.mixed:
            return move
        elapsed = now - self.started
        if component == "vx" and target < 0:
            hold, release = 1.75, 0.10
        else:
            hold, release = 0.55, 0.35
        fade = min(1.0, max(0.0, (hold + release - elapsed) / release))
        fade = fade * fade * (3.0 - 2.0 * fade)
        boost = (math.copysign(limit, target) - target) * assist * fade
        return {**move, component: target + boost}


class InputState:
    """Only valid, neutral-armed input from one sender IP can refresh the watchdog."""
    def __init__(self, cfg, source_ip=None):
        self.cfg = cfg
        self.owner = source_ip
        self.armed = False
        self.last_at = None
        self.channels = (cfg.center,) * 4
        self.valid = self.invalid = self.foreign = self.waiting_neutral = 0
        self.received = deque(maxlen=10000)
        self.received_total = 0
        self.last_received_at = None
        self.last_received_channels = self.channels

    def disarm(self):
        self.armed = False
        self.last_at = None
        self.channels = (self.cfg.center,) * 4

    def expire(self, now):
        if self.armed and now - self.last_at >= self.cfg.timeout:
            self.disarm()
            return True
        return False

    def accept(self, payload, sender_ip, now):
        # The event loop checks expiry before draining packets; never let a late packet
        # silently renew an expired non-neutral command.
        if self.owner is not None and sender_ip != self.owner:
            self.foreign += 1
            return False
        try:
            channels = parse_srt(payload, self.cfg)
        except ValueError:
            self.invalid += 1
            return False
        self.received.append(now)
        self.received_total += 1
        self.last_received_at = now
        self.last_received_channels = channels
        if not self.armed:
            if any(axis(value, self.cfg) != 0 for value in channels):
                self.waiting_neutral += 1
                return False
            self.owner = sender_ip
            self.armed = True
            LOG.info("armed sender=%s after neutral SRT frame", sender_ip)
        self.channels, self.last_at = channels, now
        self.valid += 1
        return True


class Robot:
    def __init__(self, path):
        self.path = str(path)
        self.connection = None

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None

    def connect(self):
        self.close()
        connection = socket.socket(socket.AF_UNIX)
        connection.settimeout(0.15)
        try:
            connection.connect(self.path)
            connection.sendall(b'{"jsonrpc":"2.0","id":1,"method":"robot.health"}\n')
            line = bytearray()
            while not line.endswith(b"\n") and len(line) <= 65536:
                chunk = connection.recv(1)
                if not chunk:
                    raise ConnectionError("robotd closed during health check")
                line.extend(chunk)
            reply = json.loads(line)
            if reply.get("id") != 1 or not reply.get("result", {}).get("healthy"):
                raise ConnectionError("robotd not healthy")
            self.connection = connection
        except Exception:
            connection.close()
            raise

    def send(self, move, head):
        # Continuous intents are notifications: no unread response backlog at 20 Hz.
        messages = [{"jsonrpc": "2.0", "method": name, "params": params}
                    for name, params in [("robot.move", move), ("robot.head", head)]]
        self.connection.sendall(b"".join((json.dumps(m) + "\n").encode() for m in messages))


def run(args, cfg):
    state = InputState(cfg, args.source_ip)
    robot = Robot(args.socket)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # No SO_REUSEPORT: a second bridge must fail rather than split control packets.
    udp.bind((args.bind, args.port))
    udp.setblocking(False)
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    neutral = map_channels((cfg.center,) * 4, cfg)
    next_tick = next_retry = 0.0
    next_telemetry = 0.0
    next_status = time.monotonic()
    last_command = None
    gait_start = GaitStart()

    def expire_input(now):
        nonlocal last_command
        if state.expire(now):
            gait_start.reset()
            LOG.warning("UDP input expired; zeroing movement/head; neutral required")
            if robot.connection:
                try:
                    robot.send(*neutral)
                except OSError:
                    robot.close()
            last_command = None

    LOG.info("listening udp=%s:%s protocol=SRT socket=%s timeout=%.3fs; waiting for neutral", args.bind, args.port, args.socket, cfg.timeout)
    try:
        while running:
            now = time.monotonic()
            if now >= next_telemetry:
                while state.received and state.received[0] <= now - 1:
                    state.received.popleft()
                telemetry = {"published_monotonic": now, "last_received_monotonic": state.last_received_at,
                             "drive_profile": cfg.drive_profile,
                             "port": args.port, "pwm_min": cfg.low, "pwm_center": cfg.center, "pwm_max": cfg.high,
                             "channels": state.last_received_channels, "fps": len(state.received),
                             "received_total": state.received_total, "armed": state.armed,
                             "owner": state.owner, "invalid": state.invalid,
                             "robot_connected": robot.connection is not None, "timeout_s": cfg.timeout}
                args.telemetry_file.parent.mkdir(parents=True, exist_ok=True)
                temporary = args.telemetry_file.with_suffix(f".{os.getpid()}.tmp")
                temporary.write_text(json.dumps(telemetry) + "\n")
                temporary.replace(args.telemetry_file)
                next_telemetry = now + 0.1
            expire_input(now)
            if robot.connection is None and now >= next_retry:
                state.disarm()
                gait_start.reset()
                try:
                    robot.connect()
                    robot.send(*neutral)
                    LOG.info("robotd connected; neutral SRT required")
                except (OSError, ValueError, ConnectionError) as error:
                    robot.close()
                    LOG.warning("robotd unavailable: %s", error)
                next_retry = time.monotonic() + 1.0
            # Always recheck age after potentially blocking IPC work.
            now = time.monotonic()
            expire_input(now)
            if now >= next_tick:
                if state.armed and now - state.last_at < cfg.timeout and robot.connection:
                    move, head = map_channels(state.channels, cfg)
                    move = gait_start.apply(move, state.channels, cfg, now)
                    try:
                        robot.send(move, head)
                        command = (move, head)
                        if command != last_command:
                            LOG.info("control channels=%s move=%s head=%s", state.channels, move, head)
                            last_command = command
                    except OSError as error:
                        LOG.warning("robotd disconnected: %s; input discarded", error)
                        robot.close()
                        state.disarm()
                next_tick = time.monotonic() + 1 / args.hz
            if now >= next_status:
                LOG.info("status armed=%s owner=%s accepted=%s invalid=%s foreign=%s waiting_neutral=%s", state.armed, state.owner, state.valid, state.invalid, state.foreign, state.waiting_neutral)
                next_status = now + 5
            delay = min(0.02, max(0, next_tick - time.monotonic()))
            ready, _, _ = select.select([udp], [], [], delay)
            if ready:
                # Bound draining so malformed/flooded input cannot starve expiry handling.
                for _ in range(64):
                    try:
                        payload, sender = udp.recvfrom(65535)
                    except BlockingIOError:
                        break
                    # Offline packets are consumed but cannot arm or survive a reconnect.
                    if robot.connection:
                        expire_input(time.monotonic())
                        state.accept(payload, sender[0], time.monotonic())
    finally:
        if robot.connection:
            try:
                robot.send(*neutral)
            except OSError:
                pass
        robot.close()
        udp.close()
        LOG.info("bridge stopped; neutral requested")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=6188)
    parser.add_argument("--socket", type=Path, default=robot_socket())
    parser.add_argument("--telemetry-file", type=Path, default=Path(__file__).resolve().parents[1] / ".runtime/v7rc-input.json")
    parser.add_argument("--source-ip", help="Only accept this phone IPv4 address")
    parser.add_argument("--hz", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=0.3)
    parser.add_argument("--pwm-min", type=int, default=1000)
    parser.add_argument("--pwm-center", type=int, default=1500)
    parser.add_argument("--pwm-max", type=int, default=2000)
    parser.add_argument("--deadzone", type=float, default=0.08)
    parser.add_argument("--invert", type=int, nargs="*", choices=[1, 2, 3, 4], default=[])
    parser.add_argument("--max-forward", type=float, default=0.3)
    parser.add_argument("--max-turn", type=float, default=0.8)
    parser.add_argument("--max-head-yaw", type=float, default=0.4)
    parser.add_argument("--max-head-pitch", type=float, default=0.25)
    parser.add_argument("--drive-profile", choices=("linear", "velstand-v8"), default="linear")
    args = parser.parse_args()
    if not (1 <= args.port <= 65535 and 5 <= args.hz <= 50 and 0.1 <= args.timeout <= 0.5):
        parser.error("port 1..65535, hz 5..50, timeout 0.1..0.5 required")
    if not (0 <= args.pwm_min < args.pwm_center < args.pwm_max <= 9999 and 0 <= args.deadzone < 0.5):
        parser.error("Invalid PWM endpoints or deadzone")
    limits = [(args.max_forward, 0.3), (args.max_turn, 1.5), (args.max_head_yaw, 0.5), (args.max_head_pitch, 0.4)]
    if any(not math.isfinite(value) or not 0 < value <= limit for value, limit in limits):
        parser.error("Invalid command limit: forward <=0.3, turn <=1.5, head yaw <=0.5, pitch <=0.4")
    cfg = Config(args.pwm_min, args.pwm_center, args.pwm_max, args.deadzone,
                 args.max_forward, args.max_turn, args.max_head_yaw, args.max_head_pitch,
                 tuple(i in args.invert for i in range(1, 5)), args.timeout, args.drive_profile)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        run(args, cfg)
    except OSError as error:
        parser.exit(1, f"Bridge could not run: {error}\n")


if __name__ == "__main__":
    main()
