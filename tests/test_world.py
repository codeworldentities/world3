"""World init + step smoke tests."""
from __future__ import annotations


def test_world_initialises(fresh_world):
    w = fresh_world
    assert len(w.entities) > 0
    assert w.tick == 0
    assert hasattr(w, "souls")
    assert isinstance(w.souls, dict)


def test_world_steps_without_error(fresh_world):
    w = fresh_world
    for _ in range(20):
        w.step()
    assert w.tick == 20
    assert any(e.alive for e in w.entities)


def test_stats_recorded(fresh_world):
    w = fresh_world
    for _ in range(10):
        w.step()
    assert len(w.pop_total) > 0
