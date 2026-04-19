"""act — write-side operations for the world3 skill.

    python act.py remember <soul_id> <text> [--kind=external] [--weight=0.7]
    python act.py bind    <soul_id> [--unbind]
"""
from __future__ import annotations

import json
import sys

from _http import post


def _parse_flags(args: list[str]) -> tuple[list[str], dict]:
    pos: list[str] = []
    flags: dict = {}
    for a in args:
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            flags[k] = v if v != "" else True
        else:
            pos.append(a)
    return pos, flags


def cmd_remember(soul_id: str, text: str, kind: str, weight: float) -> dict:
    return post(f"/api/soul/{soul_id}/memory",
                {"text": text, "kind": kind, "weight": weight})


def cmd_bind(soul_id: str, bound: bool) -> dict:
    return post(f"/api/soul/{soul_id}/bind", {"bound": bound})


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: act.py remember|bind ...", file=sys.stderr)
        return 2
    cmd = argv[1]
    pos, flags = _parse_flags(argv[2:])
    if cmd == "remember":
        if len(pos) < 2:
            print("usage: act.py remember <soul_id> <text>", file=sys.stderr)
            return 2
        soul_id, text = pos[0], " ".join(pos[1:])
        kind = str(flags.get("kind", "external"))
        try:
            weight = float(flags.get("weight", 0.7))
        except (TypeError, ValueError):
            weight = 0.7
        out = cmd_remember(soul_id, text, kind, weight)
    elif cmd == "bind":
        if len(pos) < 1:
            print("usage: act.py bind <soul_id> [--unbind]", file=sys.stderr)
            return 2
        out = cmd_bind(pos[0], not bool(flags.get("unbind")))
    else:
        print("usage: act.py remember|bind ...", file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
