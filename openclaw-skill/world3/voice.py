"""voice — speak as a bound soul. The LLM in world3 generates the reply
in-character using that soul's persona + long-term memory.

    python voice.py <soul_id> "your question here"
"""
from __future__ import annotations

import json
import sys

from _http import post


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print('usage: voice.py <soul_id> "<question>"', file=sys.stderr)
        return 2
    soul_id = argv[1]
    question = " ".join(argv[2:])
    out = post(f"/api/soul/{soul_id}/speak", {"question": question})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
