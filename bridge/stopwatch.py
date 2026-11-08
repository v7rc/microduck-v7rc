"""A single monotonic stopwatch shared by the console and simulator HUD."""
import json
from pathlib import Path
import tempfile
import time


def read_timer(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"elapsed_ns": 0, "started_ns": None}


def elapsed_ns(timer, now):
    started = timer["started_ns"]
    return timer["elapsed_ns"] + (max(0, now - started) if started is not None else 0)


def update_timer(path, action):
    timer = read_timer(path)
    now = time.monotonic_ns()
    if action == "reset":
        timer = {"elapsed_ns": 0, "started_ns": None}
    elif action == "start" and timer["started_ns"] is None:
        timer["started_ns"] = now
    elif action == "stop":
        timer = {"elapsed_ns": elapsed_ns(timer, now), "started_ns": None}
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
        json.dump(timer, temp)
    Path(temp.name).replace(path)
    return timer


def format_timer(nanoseconds):
    minutes, rest = divmod(nanoseconds // 1_000_000, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"
