"""Performance regression tests — keep step() fast at large populations."""
from __future__ import annotations

import time

import pytest


def test_quadtree_proximity_faster_than_brute_force():
    """Building a QuadTree + radius queries must beat N×N distance checks."""
    import math
    import random

    from core.spatial import build_entity_tree

    class _E:
        __slots__ = ("id", "x", "y", "alive")

        def __init__(self, i, x, y):
            self.id, self.x, self.y, self.alive = i, x, y, True

    random.seed(42)
    N = 1200
    W, H = 2000, 2000
    R = 50.0
    entities = [_E(i, random.uniform(0, W), random.uniform(0, H)) for i in range(N)]

    # --- Brute force ---
    t0 = time.perf_counter()
    bf_count = 0
    for e in entities:
        for o in entities:
            if o.id == e.id:
                continue
            if math.hypot(e.x - o.x, e.y - o.y) <= R:
                bf_count += 1
    t_brute = time.perf_counter() - t0

    # --- QuadTree ---
    t0 = time.perf_counter()
    tree = build_entity_tree(entities, W, H)
    qt_count = 0
    for e in entities:
        nearby = tree.query_radius(e.x, e.y, R)
        for o in nearby:
            if o.id != e.id:
                qt_count += 1
    t_qt = time.perf_counter() - t0

    # Counts must match (correctness)
    assert bf_count == qt_count, f"QuadTree missed neighbours: {bf_count} vs {qt_count}"
    # QuadTree should be meaningfully faster at N=1200
    assert t_qt < t_brute, f"QuadTree ({t_qt:.3f}s) not faster than brute ({t_brute:.3f}s)"


@pytest.mark.slow
def test_world_step_under_budget():
    """At moderate population, 50 ticks should complete within a budget.

    Regression guard against reintroducing O(n²) loops.
    """
    from core.world import World

    w = World()
    w.brain = None  # isolate from LLM

    # World seeds ~INITIAL_ENTITY_COUNT at construction.
    t0 = time.perf_counter()
    for _ in range(50):
        w.step()
    elapsed = time.perf_counter() - t0

    # Very lenient budget — tight enough to catch serious regressions on CI.
    assert elapsed < 20.0, f"50 ticks took {elapsed:.2f}s (> 20s budget)"
