"""Structured audit log — append-only JSONL of notable world events.

Useful for:
  - B2B compliance / replay
  - debugging without re-running the sim
  - feeding external systems (OpenClaw, Grafana, webhooks)

Format: each line is a JSON object with fields
    { "ts": ISO8601, "tick": int, "kind": str, "data": {...} }

File rotates per calendar day: saves/audit/world-YYYY-MM-DD.jsonl
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("persistence.audit")

AUDIT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "saves", "audit"
)

_lock = threading.Lock()


def _path_for_today() -> str:
    os.makedirs(AUDIT_DIR, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("world-%Y-%m-%d.jsonl")
    return os.path.join(AUDIT_DIR, name)


def record(kind: str, tick: int, **data: Any) -> None:
    """Append one audit event. Best-effort; swallows IO errors."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tick": int(tick),
        "kind": str(kind)[:64],
        "data": data,
    }
    line = json.dumps(entry, ensure_ascii=False, default=str)
    try:
        with _lock, open(_path_for_today(), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as exc:
        log.debug("audit write failed: %s", exc)


def tail(n: int = 100) -> list[dict]:
    """Return the last N events across today's + yesterday's files."""
    if not os.path.isdir(AUDIT_DIR):
        return []
    files = sorted(os.listdir(AUDIT_DIR))
    out: list[dict] = []
    for fname in reversed(files[-2:]):
        try:
            with open(os.path.join(AUDIT_DIR, fname), "r", encoding="utf-8") as f:
                for line in f.readlines()[-n:]:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
        if len(out) >= n:
            break
    return out[-n:]
