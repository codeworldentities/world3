"""Tests for systems/memory_compression.py (Phase 7)."""
from __future__ import annotations

import pytest

from core.soul import Soul, SoulMemory
from systems import memory_compression as mc


def _make_soul(n_memories: int = 50) -> Soul:
    s = Soul(
        id="abc123",
        entity_id=1,
        name="Testy",
        role="Tester",
        born_tick=0,
        personality_summary="A test subject.",
        traits={"curiosity": 0.7},
    )
    for i in range(n_memories):
        s.memory.append(SoulMemory(
            tick=i,
            kind="event",
            text=f"event-{i} happened",
            weight=(i % 5) / 5.0,   # varies so top-K selection works
        ))
    return s


def test_needs_compression_threshold():
    s_small = _make_soul(5)
    s_big = _make_soul(100)
    assert not mc.needs_compression(s_small)
    assert mc.needs_compression(s_big)


def test_compression_shrinks_memory_and_sets_reflection(monkeypatch):
    # Force LLM path to return None so deterministic fallback runs (no network).
    monkeypatch.setattr(mc, "_summarise_via_ollama", lambda texts: None)

    s = _make_soul(60)
    before = len(s.memory)
    changed = mc.compress_soul_memory(s, tick=999)
    assert changed
    # After compression: 1 reflection + KEEP_IMPORTANT + KEEP_RECENT
    from config import SOUL_MEMORY_KEEP_IMPORTANT, SOUL_MEMORY_KEEP_RECENT
    expected_max = 1 + SOUL_MEMORY_KEEP_IMPORTANT + SOUL_MEMORY_KEEP_RECENT
    assert len(s.memory) <= expected_max
    assert len(s.memory) < before
    # Reflection was written
    assert s.reflection
    assert s.reflection_tick == 999
    # First memory is the reflection
    assert s.memory[0].kind == "reflection"
    # Recent tail preserved intact
    assert s.memory[-1].text == "event-59 happened"


def test_compression_noop_when_under_threshold(monkeypatch):
    monkeypatch.setattr(mc, "_summarise_via_ollama", lambda texts: None)
    s = _make_soul(10)
    assert not mc.compress_soul_memory(s, tick=1)
    assert len(s.memory) == 10


def test_deterministic_summary_bounded():
    texts = [f"event-{i}" for i in range(100)]
    out = mc._deterministic_summary(texts, max_chars=120)
    assert 0 < len(out) <= 120


def test_grant_skill_dedup_and_cap():
    s = _make_soul(1)
    assert mc.grant_skill(s, "python:api", "wrote api", tick=10)
    assert not mc.grant_skill(s, "python:api", "again", tick=20)  # dedup
    assert s.skills[0]["uses"] == 2
    assert s.skills[0]["last_tick"] == 20

    # Cap enforcement
    from config import SOUL_SKILLS_MAX
    for i in range(SOUL_SKILLS_MAX + 5):
        mc.grant_skill(s, f"skill-{i}", "", tick=30 + i)
    assert len(s.skills) <= SOUL_SKILLS_MAX


def test_soul_roundtrip_preserves_new_fields():
    s = _make_soul(3)
    s.profile = "I am careful and curious."
    s.profile_tick = 42
    mc.grant_skill(s, "go:grpc", "built gRPC service", tick=5)
    d = s.to_dict()
    s2 = Soul.from_dict(d)
    assert s2.profile == s.profile
    assert s2.profile_tick == 42
    assert len(s2.skills) == 1
    assert s2.skills[0]["name"] == "go:grpc"


def test_tick_compression_smoke(monkeypatch):
    monkeypatch.setattr(mc, "_summarise_via_ollama", lambda texts: None)
    monkeypatch.setattr(mc, "_build_profile_via_ollama",
                        lambda name, role, traits, refl: None)
    souls = [_make_soul(60), _make_soul(5), _make_soul(80)]
    stats = mc.tick_compression(souls, tick=1000)
    assert stats["compressed"] >= 1
    # No exceptions, shape correct
    assert set(stats.keys()) == {"compressed", "reflections_refreshed", "profiles_refreshed"}
