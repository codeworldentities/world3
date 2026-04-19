"""peek — read-only view of the world3 simulation.

Usage from OpenClaw (or plain CLI):

    python peek.py status
    python peek.py souls
    python peek.py soul <soul_id>
"""
from __future__ import annotations

import json
import sys

from _http import get


def cmd_status() -> dict:
    return get("/api/status")


def cmd_souls() -> dict:
    return get("/api/souls")


def cmd_soul(soul_id: str) -> dict:
    return get(f"/api/soul/{soul_id}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: peek.py status|souls|soul <id>", file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd == "status":
        out = cmd_status()
    elif cmd == "souls":
        out = cmd_souls()
    elif cmd == "soul" and len(argv) >= 3:
        out = cmd_soul(argv[2])
    else:
        print("usage: peek.py status|souls|soul <id>", file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
