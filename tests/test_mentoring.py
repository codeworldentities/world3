"""Tests for systems/mentoring.py — Teacher + Judge behaviour."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from core.enums import CodeLanguage, EntityType, Gender, Role
from core.models import CodeSnippet, Entity
from systems.mentoring import (
    grant_commit_xp,
    process_judgement,
    process_teaching,
    JUDGE_REWARD_QUALITY,
)


@dataclass
class _StubWorld:
    tick: int = 100
    entities: List[Entity] = field(default_factory=list)
    code_snippets: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def log_event(self, msg: str) -> None:
        self.events.append(msg)


def _mk_dev(eid: int, x: float = 0.0, y: float = 0.0,
            langs: list | None = None) -> Entity:
    e = Entity(
        id=eid, x=x, y=y,
        entity_type=EntityType.DEVELOPER,
        energy=0.6, gender=Gender.FRONTEND_SPEC,
        role=Role.NONE,
    )
    if langs:
        e.languages_known = list(langs)
    return e


def _mk_teacher(eid: int, x: float = 0.0, y: float = 0.0,
                langs: list | None = None) -> Entity:
    e = Entity(
        id=eid, x=x, y=y,
        entity_type=EntityType.TEACHER,
        energy=0.8, gender=Gender.FRONTEND_SPEC,
    )
    e.languages_known = list(langs or list(CodeLanguage))
    return e


def _mk_judge(eid: int, x: float = 0.0, y: float = 0.0) -> Entity:
    return Entity(
        id=eid, x=x, y=y,
        entity_type=EntityType.JUDGE,
        energy=0.8, gender=Gender.BACKEND_SPEC,
    )


def _mk_snippet(sid: int, author_id: int,
                lang: CodeLanguage = CodeLanguage.PYTHON,
                quality: float = 0.5, has_bugs: bool = False) -> CodeSnippet:
    return CodeSnippet(
        id=sid,
        author_id=author_id,
        language=lang,
        content="print('x')",
        description="unit",
        quality=quality,
        tick_created=1,
        lines=1,
        filename=f"s{sid}.py",
        has_bugs=has_bugs,
    )


# ─── grant_commit_xp ─────────────────────────────────────────────

def test_grant_commit_xp_accumulates_per_language():
    dev = _mk_dev(1)
    grant_commit_xp(dev, CodeLanguage.PYTHON, 0.7)
    grant_commit_xp(dev, CodeLanguage.PYTHON, 0.6)
    grant_commit_xp(dev, CodeLanguage.RUST, 0.5)
    assert "python" in dev.language_xp
    assert "rust" in dev.language_xp
    assert dev.language_xp["python"] > dev.language_xp["rust"]


def test_grant_commit_xp_rewards_higher_quality():
    a = _mk_dev(1)
    b = _mk_dev(2)
    grant_commit_xp(a, CodeLanguage.PYTHON, 1.0)
    grant_commit_xp(b, CodeLanguage.PYTHON, 0.4)
    assert a.language_xp["python"] > b.language_xp["python"]


# ─── Teacher ──────────────────────────────────────────────────────

def test_teacher_teaches_new_language_in_range():
    world = _StubWorld()
    teacher = _mk_teacher(1, x=0.0, y=0.0, langs=[CodeLanguage.RUST])
    student = _mk_dev(2, x=30.0, y=0.0, langs=[CodeLanguage.PYTHON])
    world.entities = [teacher, student]

    # Force deterministic transfer by running many iterations.
    import random
    random.seed(42)
    mentored = 0
    for _ in range(20):
        mentored += process_teaching(world)
        if CodeLanguage.RUST in student.languages_known:
            break
    assert CodeLanguage.RUST in student.languages_known
    assert teacher.students_taught >= 1


def test_teacher_ignores_out_of_range_students():
    world = _StubWorld()
    teacher = _mk_teacher(1, x=0.0, y=0.0, langs=[CodeLanguage.GO])
    far = _mk_dev(2, x=1000.0, y=1000.0, langs=[CodeLanguage.PYTHON])
    world.entities = [teacher, far]

    mentored = process_teaching(world)
    assert mentored == 0
    assert CodeLanguage.GO not in far.languages_known


def test_teacher_boosts_xp_when_language_already_known():
    world = _StubWorld()
    teacher = _mk_teacher(1, x=0.0, y=0.0, langs=[CodeLanguage.PYTHON])
    # student already knows python
    student = _mk_dev(2, x=10.0, y=0.0, langs=[CodeLanguage.PYTHON])
    world.entities = [teacher, student]

    process_teaching(world)
    assert student.language_xp.get("python", 0.0) > 0.0


# ─── Judge ────────────────────────────────────────────────────────

def test_judge_rewards_high_quality_commit():
    world = _StubWorld()
    author = _mk_dev(1, x=0.0, y=0.0, langs=[CodeLanguage.PYTHON])
    judge = _mk_judge(2, x=20.0, y=0.0)
    snip = _mk_snippet(10, author_id=1, quality=0.9, has_bugs=False)
    world.entities = [author, judge]
    world.code_snippets[snip.id] = snip

    initial_energy = author.energy
    rewards, penalties = process_judgement(world)
    assert rewards == 1
    assert penalties == 0
    assert author.energy > initial_energy
    assert author.judge_rewards > 0
    assert "python" in author.language_xp
    assert getattr(snip, "_judged", False) is True


def test_judge_penalises_buggy_commit():
    world = _StubWorld()
    author = _mk_dev(1, x=0.0, y=0.0, langs=[CodeLanguage.PYTHON])
    judge = _mk_judge(2, x=10.0, y=0.0)
    snip = _mk_snippet(11, author_id=1, quality=0.3, has_bugs=True)
    world.entities = [author, judge]
    world.code_snippets[snip.id] = snip

    initial_energy = author.energy
    rewards, penalties = process_judgement(world)
    assert penalties == 1
    assert rewards == 0
    assert author.energy < initial_energy
    assert author.judge_penalties > 0


def test_judge_skips_when_no_judge_in_range():
    world = _StubWorld()
    author = _mk_dev(1, x=0.0, y=0.0, langs=[CodeLanguage.PYTHON])
    far_judge = _mk_judge(2, x=9999.0, y=9999.0)
    snip = _mk_snippet(12, author_id=1, quality=0.9, has_bugs=False)
    world.entities = [author, far_judge]
    world.code_snippets[snip.id] = snip

    rewards, penalties = process_judgement(world)
    assert rewards == 0 and penalties == 0
    # not judged yet — judge may roam into range later
    assert not getattr(snip, "_judged", False)


def test_judge_ignores_already_judged_snippets():
    world = _StubWorld()
    author = _mk_dev(1, x=0.0, y=0.0)
    judge = _mk_judge(2, x=0.0, y=0.0)
    snip = _mk_snippet(13, author_id=1, quality=0.9)
    snip._judged = True
    world.entities = [author, judge]
    world.code_snippets[snip.id] = snip

    rewards, penalties = process_judgement(world)
    assert rewards == 0 and penalties == 0


def test_no_judges_no_effect():
    world = _StubWorld()
    author = _mk_dev(1)
    snip = _mk_snippet(14, author_id=1, quality=0.95)
    world.entities = [author]
    world.code_snippets[snip.id] = snip

    rewards, penalties = process_judgement(world)
    assert (rewards, penalties) == (0, 0)
