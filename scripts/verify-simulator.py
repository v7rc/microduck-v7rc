#!/usr/bin/env python3
"""Measure the live MuJoCo body while commanding the real robotd; no synthetic telemetry."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bridge'))
from platform_support import robot_socket
import argparse
import datetime
import json
import math
import socket
import time


class Connection:
    def __init__(self, address, unix=False):
        self.socket = socket.socket(socket.AF_UNIX if unix else socket.AF_INET)
        self.socket.settimeout(3)
        self.socket.connect(address)
        self.file = self.socket.makefile("rw")
        self.identifier = 0

    def exchange(self, message):
        self.file.write(json.dumps(message) + "\n")
        self.file.flush()
        line = self.file.readline()
        if not line:
            raise RuntimeError("Connection closed")
        reply = json.loads(line)
        if "error" in reply:
            raise RuntimeError(reply["error"])
        return reply

    def rpc(self, method, params=None):
        self.identifier += 1
        message = {"jsonrpc": "2.0", "id": self.identifier, "method": method}
        if params is not None:
            message["params"] = params
        reply = self.exchange(message)
        if reply.get("id") != self.identifier:
            raise RuntimeError("Unexpected RPC response")
        return reply["result"]

    def close(self):
        try:
            self.file.close()
        except OSError:
            pass
        finally:
            self.socket.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", default=str(robot_socket()))
    parser.add_argument("--port", type=int, default=7801)
    parser.add_argument("--walking-speed", type=float, default=0.3)
    parser.add_argument("--turning-speed", type=float, default=0.8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    robot = Connection(args.socket, unix=True)
    body = Connection(("127.0.0.1", args.port))
    body.exchange({"op": "hello", "protocol": 1, "joints": 15})
    min_forward = max(0.30, abs(args.walking_speed) * 8 * 0.25)
    if args.walking_speed <= 0 or args.turning_speed <= 0:
        parser.error("Walking and turning speeds must be positive")
    report = {
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "CPU MuJoCo physics + real robotd, no physical robot or V7RC",
        "thresholds": {"min_trunk_m": 0.095, "max_tilt_deg": 30,
                       "min_forward_m": min_forward, "min_signed_turn_deg": 30,
                       "min_realtime": 0.95, "max_realtime": 1.05,
                       "max_idle_drift_m": 0.10},
        "phases": [],
    }
    rows_file = (args.output / "samples.jsonl").open("w")
    health_file = (args.output / "health.jsonl").open("w")
    summary = args.output / "summary.json"

    def phase(name, seconds, vx=0.0, vyaw=0.0, command=True):
        samples = []
        healths = []
        start = time.monotonic()
        for index in range(round(seconds * 10) + 1):
            if command:
                accepted = robot.rpc("robot.move", {"vx": vx, "vy": 0.0, "vyaw": vyaw})
                if not accepted.get("accepted", False):
                    raise RuntimeError(f"Movement refused: {accepted}")
            sensors = body.exchange({"op": "read"})
            w, x, y, z = sensors["imu"]["quat"]
            sensors["yaw_rad"] = math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
            sensors["tilt_deg"] = math.degrees(math.acos(max(-1.0, min(1.0, -sensors["imu"]["gravity"][2]))))
            sensors["wall_elapsed_s"] = time.monotonic() - start
            samples.append(sensors)
            rows_file.write(json.dumps({"phase": name, **sensors}) + "\n")
            if index % 10 == 0:
                health = robot.rpc("robot.health")
                healths.append(health)
                health_file.write(json.dumps({"phase": name, "elapsed_s": sensors["wall_elapsed_s"], **health}) + "\n")
            if index < round(seconds * 10):
                time.sleep(max(0, start + (index + 1) / 10 - time.monotonic()))
        a, b = samples[0], samples[-1]
        dx, dy = b["trunk"][0] - a["trunk"][0], b["trunk"][1] - a["trunk"][1]
        turn = sum(math.atan2(math.sin(q["yaw_rad"]-p["yaw_rad"]), math.cos(q["yaw_rad"]-p["yaw_rad"]))
                   for p, q in zip(samples, samples[1:]))
        real = (b["sim_time"] - a["sim_time"]) / (b["wall_elapsed_s"] - a["wall_elapsed_s"])
        result = {"name": name, "duration_s": seconds, "command_vx_m_s": vx,
                  "command_vyaw_rad_s": vyaw, "commands_sent": command,
                  "samples": len(samples), "start_xyz_m": a["trunk"], "end_xyz_m": b["trunk"],
                  "displacement_m": math.hypot(dx, dy),
                  "forward_displacement_m": dx * math.cos(a["yaw_rad"]) + dy * math.sin(a["yaw_rad"]),
                  "turn_deg": math.degrees(turn), "realtime_factor": real,
                  "min_trunk_m": min(s["trunk_z"] for s in samples),
                  "max_tilt_deg": max(s["tilt_deg"] for s in samples),
                  "all_healthy": all(h["healthy"] for h in healths)}
        checks = {"upright": result["min_trunk_m"] > 0.095 and result["max_tilt_deg"] < 30,
                  "realtime": 0.95 <= real <= 1.05, "healthy": result["all_healthy"]}
        if vx:
            checks["forward_movement"] = result["forward_displacement_m"] > min_forward
        if vyaw:
            checks["correct_turn"] = result["turn_deg"] * (1 if vyaw > 0 else -1) > 30
        if name == "standing":
            checks["idle_drift"] = result["displacement_m"] < 0.10
        if not command:
            # Evaluate the last second, leaving 2 s for command expiry and settling.
            last = samples[-11]
            result["last_second_drift_m"] = math.dist(last["trunk"][:2], b["trunk"][:2])
            checks["settled_after_expiry"] = result["last_second_drift_m"] < 0.10
        result["checks"] = checks
        result["passed"] = all(checks.values())
        report["phases"].append(result)
        summary.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(result), flush=True)

    try:
        phase("standing", 10)
        phase("walking", 8, vx=args.walking_speed)
        phase("walk_expiry", 3, command=False)
        phase("turn_left", 6, vyaw=args.turning_speed)
        phase("left_expiry", 3, command=False)
        phase("turn_right", 6, vyaw=-args.turning_speed)
        phase("right_expiry", 3, command=False)
        report["passed"] = all(p["passed"] for p in report["phases"])
        if not report["passed"]:
            raise RuntimeError("Failed phases: " + ", ".join(p["name"] for p in report["phases"] if not p["passed"]))
    except Exception as error:
        report["passed"] = False
        report["error"] = str(error)
        raise
    finally:
        try:
            robot.rpc("robot.move", {"vx": 0.0, "vy": 0.0, "vyaw": 0.0})
        except OSError as error:
            report["cleanup_error"] = str(error)
        finally:
            rows_file.close()
            health_file.close()
            summary.write_text(json.dumps(report, indent=2) + "\n")
            robot.close()
            body.close()


if __name__ == "__main__":
    main()
