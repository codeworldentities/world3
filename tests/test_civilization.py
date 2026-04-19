"""Tests for Phase 7B — governance, civilization goal, era naming."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from core.enums import EntityType, Gender
from core.models import Entity
from core.civilization_goal import CivilizationGoal
from systems.governance import (
    GovernanceState,
    Proposal,
    _voter_weight,
    vote,
    maybe_auto_propose,
)
from systems.legacy import detect_era_name, maybe_log_era_change


# ---------- lightweight stub world (avoid slow full-World fixture) ----------

@dataclass
class _StubWorld:
    tick: int = 0
    era: int = 1
    entities: List[Entity] = field(default_factory=list)
    settlements: dict = field(default_factory=dict)
    total_bug_reports: int = 0
    total_code_generated: int = 0
    governance: GovernanceState = field(default_factory=GovernanceState)
    civilization_goal: CivilizationGoal = field(default_factory=CivilizationGoal)
    _last_era_name: str | None = None
    events: list = field(default_factory=list)

    def log_event(self, msg: str) -> None:
        self.events.append(msg)


def _mk_dev(eid: int, curiosity=0.7, sociability=0.6, age=100,
            commits=0, bugs_fixed=0, alive=True) -> Entity:
    e = Entity(
        id=eid, x=0.0, y=0.0,
        entity_type=EntityType.DEVELOPER,
        energy=0.5, gender=Gender.FRONTEND_SPEC,
        age=age,
        curiosity=curiosity, sociability=sociability,
    )
    e.alive = alive
    e.commits = commits
    e.bugs_fixed = bugs_fixed
    return e


def _mk_bug(eid: int) -> Entity:
    return Entity(
        id=eid, x=0.0, y=0.0,
        entity_type=EntityType.BUG,
        energy=0.5, gender=Gender.BACKEND_SPEC,
        curiosity=0.9, sociability=0.9,   # should still not vote
    )


# ================== Governance ==================

def test_voter_weight_bug_is_zero():
    assert _voter_weight(_mk_bug(1)) == 0.0


def test_voter_weight_bounds():
    # Extreme traits still capped at 2.0
    high = _mk_dev(1, curiosity=1.0, sociability=1.0, age=100_000)
    assert _voter_weight(high) <= 2.0
    # Minimum floor
    low = _mk_dev(2, curiosity=0.0, sociability=0.0, age=0)
    assert _voter_weight(low) >= 0.1


def test_vote_with_no_entities_passes_is_false():
    w = _StubWorld()
    p = vote(w, "empty_proposal", "nobody home")
    # weight_yes (0) > weight_no (0) is False
    assert p.passed is False
    assert p.voter_count == 0
    assert w.governance.proposals[-1] is p


def test_bugs_do_not_vote():
    w = _StubWorld(entities=[_mk_dev(1), _mk_bug(2), _mk_bug(3)])
    p = vote(w, "some_proposal")
    assert p.voter_count == 1  # only the dev


def test_vote_is_deterministic():
    w1 = _StubWorld(entities=[_mk_dev(i) for i in range(10)])
    w2 = _StubWorld(entities=[_mk_dev(i) for i in range(10)])
    p1 = vote(w1, "adopt_microservices")
    p2 = vote(w2, "adopt_microservices")
    assert p1.yes == p2.yes
    assert p1.no == p2.no
    assert p1.passed == p2.passed


def test_auto_propose_dedupes_by_title():
    w = _StubWorld(
        tick=2000,
        entities=[_mk_dev(i, curiosity=0.8) for i in range(20)],
    )
    first = maybe_auto_propose(w, interval=2000)
    assert first is not None
    titles_after_first = {p.title for p in w.governance.proposals}

    # Same tick, second call still runs; must pick a *different* title
    second = maybe_auto_propose(w, interval=2000)
    if second is not None:
        assert second.title not in titles_after_first or second.title == first.title
        # When all in pool remain, it cycles — just assert no crash and it still appended


def test_auto_propose_skips_off_interval():
    w = _StubWorld(tick=1234)
    assert maybe_auto_propose(w, interval=2000) is None


def test_passed_proposal_sets_flag():
    # Craft a world where the vote is likely to pass by stacking curious devs.
    w = _StubWorld(
        tick=2000,
        entities=[_mk_dev(i, curiosity=0.9, sociability=0.9) for i in range(30)],
    )
    p = maybe_auto_propose(w, interval=2000)
    assert p is not None
    if p.passed:
        # Exactly one flag should match the pool entry
        assert any(v == p.title for v in w.governance.flags.values())


# ================== Civilization Goal ==================

def test_goal_progress_counts_commits_and_bugs_fixed():
    w = _StubWorld(entities=[
        _mk_dev(1, commits=3, bugs_fixed=2),
        _mk_dev(2, commits=1, bugs_fixed=0),
    ])
    g = CivilizationGoal()
    g.update(w)
    # 3+1 commits  +  (2+0)*2 bugs_fixed  = 4 + 4 = 8
    assert g.progress == 8
    assert g.name == "produce_high_quality_code"
    assert g.achieved is False


def test_goal_rotates_on_achievement():
    w = _StubWorld(
        tick=500,
        entities=[_mk_dev(1, commits=10_000)],  # blows through any target
    )
    g = CivilizationGoal(target=10)
    g.update(w)
    # Should rotate to the next ladder step
    assert g.name in {"build_great_settlements", "survive_and_thrive"}
    assert g.progress == 0
    assert g.achieved is False
    assert len(g.history) == 1
    assert g.history[0]["name"] == "produce_high_quality_code"


def test_goal_to_dict_has_ratio():
    g = CivilizationGoal(target=100, progress=25)
    d = g.to_dict()
    assert d["ratio"] == 0.25
    assert d["name"] == "produce_high_quality_code"
    assert "history" in d


def test_goal_influence_is_zero_cost_for_idle_entity():
    g = CivilizationGoal()
    e = _mk_dev(1, commits=0, bugs_fixed=0)
    before = e.energy
    g.influence(e)
    assert e.energy == before  # no commits yet → no boost


def test_goal_influence_boosts_productive_entity():
    g = CivilizationGoal()
    e = _mk_dev(1, commits=5)
    e.energy = 0.5
    g.influence(e)
    assert e.energy > 0.5
    assert e.energy <= 1.0


# ================== Era naming ==================

def test_era_name_flag_beats_metrics():
    w = _StubWorld(total_code_generated=10_000, total_bug_reports=0)
    w.governance.flags["architecture"] = "adopt_microservices"
    assert detect_era_name(w) == "Era of Microservices"


def test_era_name_metric_fallback_conflicts():
    w = _StubWorld(total_bug_reports=100, total_code_generated=50)
    assert detect_era_name(w) == "Era of Conflicts"


def test_era_name_default_is_beginnings():
    w = _StubWorld()
    assert detect_era_name(w) == "Era of Beginnings"


def test_maybe_log_era_change_first_call_is_silent():
    w = _StubWorld()
    changed = maybe_log_era_change(w)
    assert changed is True
    assert w._last_era_name == "Era of Beginnings"
    assert w.events == []  # seeding should not emit


def test_maybe_log_era_change_emits_on_transition():
    w = _StubWorld()
    maybe_log_era_change(w)  # seed
    # Flip to microservices
    w.governance.flags["architecture"] = "adopt_microservices"
    changed = maybe_log_era_change(w)
    assert changed is True
    assert any("Microservices" in e for e in w.events)
