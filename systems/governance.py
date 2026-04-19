"""Governance — collective decision-making layer.

Entities vote on civilization-wide proposals. The vote is deterministic and
LLM-free: each voter's weight is derived from their personality traits, so
curious and sociable entities carry more influence than, say, a Bug.

Proposals are stored on the World so the UI and later ticks can react.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from core.enums import EntityType

if TYPE_CHECKING:
    from core.models import Entity
    from core.world import World

log = logging.getLogger("systems.governance")


# ================== Data model ==================

@dataclass
class Proposal:
    id: str
    title: str                     # short key, e.g. "adopt_microservices"
    description: str = ""
    created_tick: int = 0
    yes: int = 0
    no: int = 0
    weight_yes: float = 0.0
    weight_no: float = 0.0
    passed: Optional[bool] = None  # None = undecided
    decided_tick: int = 0
    voter_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_tick": self.created_tick,
            "yes": self.yes,
            "no": self.no,
            "weight_yes": round(self.weight_yes, 2),
            "weight_no": round(self.weight_no, 2),
            "passed": self.passed,
            "decided_tick": self.decided_tick,
            "voter_count": self.voter_count,
        }


@dataclass
class GovernanceState:
    proposals: list[Proposal] = field(default_factory=list)
    flags: dict = field(default_factory=dict)  # e.g. {"architecture": "microservices"}
    max_history: int = 40

    def log(self, p: Proposal) -> None:
        self.proposals.append(p)
        if len(self.proposals) > self.max_history:
            self.proposals = self.proposals[-self.max_history:]


# ================== Voting math ==================

def _voter_weight(e: "Entity") -> float:
    """Non-Bug entities vote. Weight comes from curiosity + sociability
    (our analogue of 'intelligence + loyalty'). Bounded to [0.1, 2.0]."""
    if e.entity_type == EntityType.BUG:
        return 0.0
    base = (getattr(e, "curiosity", 0.5) + getattr(e, "sociability", 0.5))
    # age gives a tiny seniority bonus
    bonus = min(0.5, getattr(e, "age", 0) / 2000.0)
    return max(0.1, min(2.0, base + bonus))


def _decide(proposal_key: str, voter_seed: int) -> bool:
    """Deterministic per-voter decision. Different voters and proposals
    produce uncorrelated outcomes without spending RNG state."""
    h = hashlib.md5(f"{proposal_key}|{voter_seed}".encode()).digest()
    # first byte in [0,255]; accept if < 128 (50/50 baseline, trait-weighted below)
    return h[0] < 128


def vote(world: "World", title: str, description: str = "") -> Proposal:
    """Run one collective vote. Returns the finalised Proposal."""
    state = _ensure_state(world)
    p = Proposal(
        id=f"p{int(time.time() * 1000) % 10_000_000:07d}",
        title=title,
        description=description,
        created_tick=world.tick,
    )

    for e in world.entities:
        if not e.alive:
            continue
        w = _voter_weight(e)
        if w <= 0:
            continue
        # Trait-biased: higher weight = higher probability to vote YES
        # when they lean positively (curiosity > 0.5), else NO.
        base_yes = _decide(title, e.id)
        leans_positive = getattr(e, "curiosity", 0.5) >= 0.5
        decision = base_yes if leans_positive else (not base_yes)

        if decision:
            p.yes += 1
            p.weight_yes += w
        else:
            p.no += 1
            p.weight_no += w
        p.voter_count += 1

    p.passed = p.weight_yes > p.weight_no
    p.decided_tick = world.tick
    state.log(p)
    log.info("vote '%s' -> %s  (yes=%d/%.1f  no=%d/%.1f  voters=%d)",
             title, "PASS" if p.passed else "FAIL",
             p.yes, p.weight_yes, p.no, p.weight_no, p.voter_count)
    return p


# ================== World integration ==================

def _ensure_state(world: "World") -> GovernanceState:
    st = getattr(world, "governance", None)
    if st is None:
        st = GovernanceState()
        world.governance = st
    return st


# Pool of civilization-level questions that can be auto-proposed by the
# world when interesting conditions are met. Adding entries is cheap.
_AUTO_PROPOSALS: list[tuple[str, str, str]] = [
    # (title,            description,                                        flag_key)
    ("adopt_microservices", "Should the civilization move to microservices?", "architecture"),
    ("embrace_strict_reviews", "Require reviews on every commit?",            "review_policy"),
    ("encourage_refactoring",  "Dedicate cycles to refactoring over features?", "refactor_priority"),
    ("invest_in_testing",      "Allocate more entities to testing roles?",    "test_focus"),
]


def maybe_auto_propose(world: "World", interval: int = 2000) -> Optional[Proposal]:
    """Every `interval` ticks pick the next unresolved proposal and run a vote.

    Returns the Proposal if one was held, else None. No LLM is used.
    """
    if world.tick == 0 or world.tick % interval != 0:
        return None
    state = _ensure_state(world)
    seen = {p.title for p in state.proposals}
    for title, desc, flag in _AUTO_PROPOSALS:
        if title in seen:
            continue
        p = vote(world, title, desc)
        if p.passed:
            # Flip the matching flag — used by narrative layers (era naming).
            state.flags[flag] = title
        return p
    return None
