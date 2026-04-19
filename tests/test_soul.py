"""Soul system tests — grant, persist, reincarnate."""
from __future__ import annotations

import os
import tempfile


def test_grant_soul(fresh_world):
    from systems.soul_system import grant_soul

    w = fresh_world
    for _ in range(3):
        w.step()
    e = next(x for x in w.entities if x.alive)
    soul = grant_soul(w, e)
    assert soul is not None
    assert soul.id in w.souls
    assert e.soul_id == soul.id
    assert soul.name
    assert soul.memory  # should have a birth memory


def test_grant_idempotent(fresh_world):
    from systems.soul_system import grant_soul, eligible_for_soul

    w = fresh_world
    for _ in range(3):
        w.step()
    e = next(x for x in w.entities if x.alive)
    grant_soul(w, e)
    assert not eligible_for_soul(w, e)  # already has one


def test_soul_save_load(fresh_world):
    from systems.soul_system import grant_soul
    import persistence.soul_store as store

    w = fresh_world
    for _ in range(3):
        w.step()
    e = next(x for x in w.entities if x.alive)
    soul = grant_soul(w, e)
    soul.remember(w.tick, "achievement", "shipped v1", weight=0.9)
    store.save_soul(soul)

    loaded = store.load_all_souls()
    assert soul.id in loaded
    restored = loaded[soul.id]
    assert restored.name == soul.name
    assert any(m.text == "shipped v1" for m in restored.memory)


def test_world_save_preserves_soul_id(fresh_world, tmp_path):
    from systems.soul_system import grant_soul
    from persistence.save_load import save_world, load_world
    from core.world import World

    w = fresh_world
    for _ in range(3):
        w.step()
    e = next(x for x in w.entities if x.alive)
    soul = grant_soul(w, e)
    target_id = e.id
    soul_id = soul.id

    path = os.path.join(tmp_path, "save.json")
    save_world(w, filepath=path)

    w2 = World()
    assert load_world(w2, path)
    e2 = next((x for x in w2.entities if x.id == target_id), None)
    assert e2 is not None
    assert e2.soul_id == soul_id
