"""Inheritance — after a Developer dies, a successor continues the work.

Logic:
  1. Developer dies (energy <= 0, age or war)
  2. A successor appears — heir/apprentice
  3. The successor receives:
     - Parent's settlement/project (if not yet completed)
     - Parent's languages (85% probability)
     - Parent's knowledge (85%)
     - code_quality baseline (parent's 60% + rest from base)
     - Memory: "who was my mentor"
  4. If the project was completed — successor is free, starts a new project
  5. Bugs do not leave successors (they respawn anyway)
"""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, Gender, CodeLanguage, Instinct
from core.models import InstinctState
from config import (
    CODE_MAX_PER_PROJECT, KNOWLEDGE_INHERIT_CHANCE,
    KNOWLEDGE_TO_LANG, MAX_ENTITIES,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity


# Probability that a successor appears (100% = always)
SUCCESSION_CHANCE = 0.85

# Bugs and refactorers do not leave successors
_SUCCESSOR_TYPES = {
    EntityType.DEVELOPER, EntityType.SENIOR_DEV,
    EntityType.AI_COPILOT, EntityType.INTERN,
}


def process_legacy(world: World, dead_entities: list['Entity']):
    """Create successors for dead developers.

    Called in world.step(), during dead entity cleanup.
    """
    for dead in dead_entities:
        if dead.entity_type not in _SUCCESSOR_TYPES:
            continue

        if len(world.entities) >= MAX_ENTITIES:
            break

        if random.random() > SUCCESSION_CHANCE:
            continue

        _spawn_successor(world, dead)


def _spawn_successor(world: World, parent: 'Entity'):
    """Create successor — inheriting parent traits."""

    # Type mutation (small chance)
    child_type = parent.entity_type
    roll = random.random()
    if roll < 0.02:
        child_type = EntityType.SENIOR_DEV  # Rare "inexperienced genius"
    elif roll < 0.06:
        child_type = EntityType.INTERN  # Novice apprentice (common)

    # Instinct inheritance (from one parent + mutation)
    child_instincts = InstinctState.create_for_type(child_type, mutation=0.1)
    if parent.instincts:
        # Partial inheritance of parent's instincts
        for inst, w in parent.instincts.weights.items():
            if inst in child_instincts.weights:
                child_instincts.weights[inst] = (
                    child_instincts.weights[inst] * 0.5 + w * 0.5
                    + random.uniform(-0.05, 0.05)
                )

    # Spawn position — near parent
    offset = 25
    child = world.spawn_entity(
        x=parent.x + random.uniform(-offset, offset),
        y=parent.y + random.uniform(-offset, offset),
        entity_type=child_type,
        energy=0.55,
        generation=parent.generation + 1,
        parent_a=parent.id,
        parent_b=None,
        gender=random.choice([Gender.FRONTEND_SPEC, Gender.BACKEND_SPEC]),
        instincts=child_instincts,
    )

    if child is None:
        return  # MAX_ENTITIES

    # --- Trait inheritance ---
    mut = 0.10
    child.aggression = max(0, min(1, parent.aggression * 0.7 + 0.3 * random.random() + random.uniform(-mut, mut)))
    child.curiosity = max(0, min(1, parent.curiosity * 0.7 + 0.3 * random.random() + random.uniform(-mut, mut)))
    child.sociability = max(0, min(1, parent.sociability * 0.7 + 0.3 * random.random() + random.uniform(-mut, mut)))
    child.resilience = max(0, min(1, parent.resilience * 0.7 + 0.3 * random.random() + random.uniform(-mut, mut)))
    child.speed = max(0.5, min(3.0, parent.speed * 0.8 + random.uniform(0.1, 0.5)))

    # --- Language inheritance (85%) ---
    child.languages_known = []
    for lang in parent.languages_known:
        if random.random() < KNOWLEDGE_INHERIT_CHANCE:
            child.languages_known.append(lang)
    # Minimum 1 language
    if not child.languages_known and parent.languages_known:
        child.languages_known.append(random.choice(parent.languages_known))
    elif not child.languages_known and child_type != EntityType.BUG:
        child.languages_known.append(random.choice(list(CodeLanguage)))

    # --- Knowledge inheritance (85%) ---
    for kt in parent.known_knowledge:
        if kt not in child.known_knowledge:
            if random.random() < KNOWLEDGE_INHERIT_CHANCE:
                child.known_knowledge.append(kt)

    # Group's knowledge too
    if parent.group_id is not None:
        group_k = world.group_knowledge.get(parent.group_id, [])
        for kt in group_k:
            if kt not in child.known_knowledge:
                if random.random() < KNOWLEDGE_INHERIT_CHANCE * 0.7:
                    child.known_knowledge.append(kt)

    # --- Code quality: parent's 60% + base, boosted by reputation ---
    parent_rep = getattr(parent, 'reputation', 0.5)
    rep_bonus = max(0.0, (parent_rep - 0.5) * 0.2)  # up to +0.1 for rep=1.0
    child.code_quality = parent.code_quality * 0.6 + 0.5 * 0.4 + rep_bonus
    child.reputation = min(1.0, 0.5 + rep_bonus)  # slight head start

    # --- Project/settlement inheritance ---
    if parent.settlement_id is not None:
        sett = world.settlements.get(parent.settlement_id)
        if sett:
            # Project not yet completed?
            if len(sett.codebase) < CODE_MAX_PER_PROJECT:
                # Child joins the same project
                child.settlement_id = parent.settlement_id
                child.group_id = parent.group_id
                child.home_x = parent.home_x if parent.home_x else sett.x + random.uniform(-30, 30)
                child.home_y = parent.home_y if parent.home_y else sett.y + random.uniform(-30, 30)

                # Register in group too
                if parent.group_id is not None:
                    world.groups.setdefault(parent.group_id, []).append(child.id)
            else:
                # Project completed — successor is free, will start new work
                child.settlement_id = None
                child.group_id = None
    else:
        # Parent was without a project
        child.group_id = parent.group_id
        if parent.group_id is not None:
            world.groups.setdefault(parent.group_id, []).append(child.id)

    # --- Memory ---
    child.remember(world.tick, "mentor_legacy", parent.id, 1.0)
    child.remember(world.tick, "spawned_as_successor", None, 0.8)

    # --- Nocturnality ---
    child.nocturnal = max(0, min(1, parent.nocturnal + random.uniform(-0.05, 0.05)))

    # --- Culture ---
    if parent.group_id is not None and parent.group_id in world.group_cultures:
        culture = world.group_cultures[parent.group_id]
        child.nocturnal = max(0, min(1, culture.nocturnal + random.uniform(-0.05, 0.05)))
        child.aggression = max(0, min(1, child.aggression * 0.7 + culture.aggression_norm * 0.3))

    # --- Visual ---
    world.spawn_particles(child.x, child.y, (100, 220, 180), count=10, speed=2.0, size=2.0)

    # --- Log ---
    project_note = ""
    if child.settlement_id is not None:
        sett = world.settlements.get(child.settlement_id)
        if sett:
            project_note = f" → {sett.project_name}"
    world.log_event(
        f"🧬 #{child.id} ({child.entity_type.value}) successor of "
        f"#{parent.id} (gen {child.generation}){project_note}")


# ================== Era naming (narrative layer) ==================

def detect_era_name(world: 'World') -> str:
    """Give the current era a human-readable name based on world flags
    and coarse statistics. Pure function — no side effects, no LLM."""
    gov = getattr(world, "governance", None)
    flags = getattr(gov, "flags", {}) if gov else {}

    if flags.get("architecture") == "adopt_microservices":
        return "Era of Microservices"
    if flags.get("review_policy") == "embrace_strict_reviews":
        return "Era of Rigour"
    if flags.get("refactor_priority") == "encourage_refactoring":
        return "Era of Refinement"
    if flags.get("test_focus") == "invest_in_testing":
        return "Era of Verification"

    # Fallback by metrics
    bug_reports = getattr(world, "total_bug_reports", 0)
    code = getattr(world, "total_code_generated", 0)
    settlements = len(getattr(world, "settlements", {}) or {})

    if bug_reports > 50 and bug_reports > code // 2:
        return "Era of Conflicts"
    if settlements >= 5:
        return "Era of Expansion"
    if code > 200:
        return "Era of Foundations"
    return "Era of Beginnings"


def maybe_log_era_change(world: 'World') -> bool:
    """If the era name has changed since last check, log it and remember.
    Returns True if a transition was logged."""
    name = detect_era_name(world)
    prev = getattr(world, "_last_era_name", None)
    if name != prev:
        world._last_era_name = name
        if prev is not None:
            world.log_event(f"📜 Entered {name} (v{world.era}.0)")
        else:
            # Seed without a noisy event at boot
            pass
        return True
    return False

