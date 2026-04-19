"""Quick smoke test — run 500 ticks with LLM disabled, print a status summary.

Use this to verify the world runs end-to-end without a GPU / Ollama.
Run:  python smoke_run.py
"""
import logging
import random
import time

import config

# Deterministic + fully local: no LLM, aggressive compression cadence
config.LLM_ENABLED = False
config.SOUL_COMPRESSION_CHECK_INTERVAL = 50
config.SOUL_MEMORY_COMPRESSION_THRESHOLD = 15

logging.basicConfig(level=logging.WARNING)
random.seed(42)

from core.world import World  # noqa: E402


def main():
    w = World()
    for _ in range(10):
        w.spawn_entity()
    print(f"initial entities: {len(w.entities)}", flush=True)

    t0 = time.time()
    ticks = 200
    for i in range(ticks):
        w.step()
        if (i + 1) % 50 == 0:
            alive = sum(1 for e in w.entities if e.alive)
            print(f"  tick {i+1}/{ticks} alive={alive} settlements={len(w.settlements)} "
                  f"souls={len(w.souls or {})}", flush=True)
    elapsed = time.time() - t0

    alive = sum(1 for e in w.entities if e.alive)
    settlements = len(getattr(w, "settlements", {}) or {})
    souls = getattr(w, "souls", {}) or {}

    print(f"tick={w.tick} elapsed={elapsed:.2f}s ({ticks / elapsed:.1f} ticks/s)")
    print(f"alive={alive} settlements={settlements} souls={len(souls)}")
    print(f"total_code_generated={w.total_code_generated}")
    print(f"total_born={w.total_born} total_died={w.total_died}")

    if souls:
        print("\n=== Sample souls ===")
        for s in list(souls.values())[:3]:
            print(f"\n-- {s.name} ({s.role}) entity#{s.entity_id} --")
            print(f"   memories={len(s.memory)} skills={len(s.skills)}")
            refl = (s.reflection or "(no reflection yet)")[:140]
            print(f"   reflection: {refl}")
            prof = (s.profile or "(no profile yet)")[:140]
            print(f"   profile:    {prof}")
            if s.skills:
                names = [sk["name"] for sk in s.skills[:5]]
                print(f"   top skills: {names}")
    else:
        print("(no souls granted — not enough settlements/achievements yet)")


if __name__ == "__main__":
    main()
