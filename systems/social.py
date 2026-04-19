"""Social — pair programming, code review, feature creation."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import (
    EntityType, Gender, Instinct, KnowledgeType, CodeLanguage,
)
from config import (
    INTERACTION_RADIUS, FEATURE_CHANCE, MAX_ENTITIES,
    COOLDOWN_AFTER_FEATURE, COOLDOWN_AFTER_REVIEW,
    KNOWLEDGE_INHERIT_CHANCE, KNOWLEDGE_TO_LANG,
    PROJECT_MIN_TEAM_SIZE, PROJECT_MAX_TEAM,
)
from core.models import Culture, InstinctState

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity


def interact(world: World, a: Entity, b: Entity, dist: float):
    """Interaction between two entities (pair programming, mentoring, etc.)."""
    world.total_interactions += 1
    same = a.entity_type == b.entity_type

    coop_a = a.sociability
    if a.group_id is not None and a.group_id in world.group_cultures:
        coop_a = (coop_a + world.group_cultures[a.group_id].cooperation) / 2

    if same:
        # pair programming bonus
        transfer = 0.002 * coop_a
        if a.energy > b.energy:
            a.energy -= transfer
            b.energy += transfer
        a.update_relationship(b.id, 0.008)
        b.update_relationship(a.id, 0.008)

        # language sharing (pair programming: learn from each other)
        if random.random() < 0.002:
            for lang in a.languages_known:
                if lang not in b.languages_known and random.random() < 0.3:
                    b.languages_known.append(lang)
                    break
            for lang in b.languages_known:
                if lang not in a.languages_known and random.random() < 0.3:
                    a.languages_known.append(lang)
                    break
    else:
        if a.aggression > 0.7 and b.aggression > 0.7:
            a.energy -= 0.008
            b.energy -= 0.008
            a.update_relationship(b.id, -0.04)
            b.update_relationship(a.id, -0.04)
            if random.random() < 0.05:
                world.spawn_particles(
                    (a.x + b.x) / 2, (a.y + b.y) / 2,
                    (255, 200, 100), count=4, speed=1.5,
                )

    rel = a.get_relationship(b.id)

    # team formation
    if same and rel > 0.1 and a.sociability > 0.2 and b.sociability > 0.2:
        _try_form_group(world, a, b)

    # feature creation (reproduction → new developer)
    if (a.can_mate and b.can_mate
            and same and a.gender != b.gender
            and rel > 0.02
            and random.random() < FEATURE_CHANCE
            and len(world.entities) < MAX_ENTITIES):
        _create_feature(world, a, b)


def _try_form_group(world: World, a: Entity, b: Entity):
    """Team formation or disbanding."""
    if a.group_id is None and b.group_id is None:
        # Only create a group when there is a viable nearby core.
        # This avoids noisy 2-person groups that cannot found a project.
        nearby_ungrouped = []
        for e in world.entities:
            if not e.alive or e.group_id is not None:
                continue
            if e.entity_type != a.entity_type:
                continue
            if math.hypot(e.x - a.x, e.y - a.y) <= INTERACTION_RADIUS * 2:
                nearby_ungrouped.append(e)

        if len(nearby_ungrouped) < PROJECT_MIN_TEAM_SIZE:
            return

        random.shuffle(nearby_ungrouped)
        initial_members = nearby_ungrouped[:PROJECT_MAX_TEAM]

        gid = world.next_group_id
        world.next_group_id += 1
        world.groups[gid] = []
        for member in initial_members:
            member.group_id = gid
            world.groups[gid].append(member.id)

        world.group_cultures[gid] = Culture(
            food_pref=(a.curiosity + b.curiosity) / 2,
            aggression_norm=(a.aggression + b.aggression) / 2,
            nocturnal=random.random() * 0.4,
            cooperation=(a.sociability + b.sociability) / 2,
            wander_range=(a.curiosity + b.curiosity) / 2,
        )
        for member in initial_members:
            member.nocturnal = world.group_cultures[gid].nocturnal

        world.log_event(
            f"⚡ Team #{gid} formed with {len(initial_members)} devs "
            f"(project-ready: min {PROJECT_MIN_TEAM_SIZE})"
        )
    elif a.group_id is not None and b.group_id is None:
        b.group_id = a.group_id
        members = world.groups.setdefault(a.group_id, [])
        if b.id not in members:
            members.append(b.id)
        if a.group_id in world.group_cultures:
            b.nocturnal = world.group_cultures[a.group_id].nocturnal

        if len(members) == PROJECT_MIN_TEAM_SIZE:
            world.log_event(
                f"📈 Team #{a.group_id} reached project-ready size "
                f"({len(members)} devs)"
            )
    elif b.group_id is not None and a.group_id is None:
        a.group_id = b.group_id
        members = world.groups.setdefault(b.group_id, [])
        if a.id not in members:
            members.append(a.id)
        if b.group_id in world.group_cultures:
            a.nocturnal = world.group_cultures[b.group_id].nocturnal

        if len(members) == PROJECT_MIN_TEAM_SIZE:
            world.log_event(
                f"📈 Team #{b.group_id} reached project-ready size "
                f"({len(members)} devs)"
            )


def _create_feature(world: World, a: Entity, b: Entity):
    """Two developers collaborate → new dev/feature."""
    initiator = a if a.gender == Gender.FRONTEND_SPEC else b
    completer = b if a.gender == Gender.FRONTEND_SPEC else a

    child_type = initiator.entity_type
    roll = random.random()
    if roll < 0.01:
        child_type = EntityType.SENIOR_DEV
        world.log_event("⭐ Senior Dev mutation!")
    elif roll < 0.03:
        child_type = EntityType.REFACTORER
    elif roll < 0.05:
        child_type = EntityType.AI_COPILOT
    elif roll < 0.06:
        child_type = EntityType.INTERN

    gen = max(initiator.generation, completer.generation) + 1
    child_instincts = InstinctState.inherit(initiator.instincts, completer.instincts, mutation=0.08)

    child = world.spawn_entity(
        x=(initiator.x + completer.x) / 2 + random.uniform(-15, 15),
        y=(initiator.y + completer.y) / 2 + random.uniform(-15, 15),
        entity_type=child_type, energy=0.5, generation=gen,
        parent_a=initiator.id, parent_b=completer.id,
        instincts=child_instincts,
    )
    if not child:
        return

    mut = 0.12
    child.aggression = max(0, min(1, (initiator.aggression + completer.aggression) / 2 + random.uniform(-mut, mut)))
    child.curiosity = max(0, min(1, (initiator.curiosity + completer.curiosity) / 2 + random.uniform(-mut, mut)))
    child.sociability = max(0, min(1, (initiator.sociability + completer.sociability) / 2 + random.uniform(-mut, mut)))
    child.resilience = max(0, min(1, (initiator.resilience + completer.resilience) / 2 + random.uniform(-mut, mut)))
    child.speed = max(0.3, min(3.5, (initiator.speed + completer.speed) / 2 + random.uniform(-0.2, 0.2)))
    child.group_id = initiator.group_id

    if initiator.group_id is not None and initiator.group_id in world.group_cultures:
        culture = world.group_cultures[initiator.group_id]
        child.nocturnal = max(0, min(1, culture.nocturnal + random.uniform(-0.05, 0.05)))
        child.aggression = max(0, min(1, child.aggression * 0.7 + culture.aggression_norm * 0.3))
    else:
        child.nocturnal = (initiator.nocturnal + completer.nocturnal) / 2 + random.uniform(-0.05, 0.05)

    # Knowledge inheritance
    if initiator.group_id is not None:
        group_k = world.group_knowledge.get(initiator.group_id, [])
        for kt in group_k:
            if random.random() < KNOWLEDGE_INHERIT_CHANCE:
                if kt not in child.known_knowledge:
                    child.known_knowledge.append(kt)

    for parent in (initiator, completer):
        for kt in parent.known_knowledge:
            if kt not in child.known_knowledge:
                if random.random() < KNOWLEDGE_INHERIT_CHANCE:
                    child.known_knowledge.append(kt)

    # language inheritance
    for parent in (initiator, completer):
        for lang in parent.languages_known:
            if lang not in child.languages_known:
                if random.random() < 0.5:
                    child.languages_known.append(lang)

    # Specialisation XP inheritance — child inherits ~40% of the best
    # parent's XP per language (capped). Keeps generational learning
    # compounding so later generations are stronger specialists.
    for lang_key in set(initiator.language_xp) | set(completer.language_xp):
        best_xp = max(
            initiator.language_xp.get(lang_key, 0.0),
            completer.language_xp.get(lang_key, 0.0),
        )
        if best_xp > 0:
            child.language_xp[lang_key] = min(best_xp * 0.4, 50.0)

    # if parents didn't know a language, child gets a basic one
    if not child.languages_known and child.entity_type != EntityType.BUG:
        known_k = child.known_knowledge
        for kt in known_k:
            if kt in KNOWLEDGE_TO_LANG:
                child.languages_known.append(KNOWLEDGE_TO_LANG[kt])
                break
        if not child.languages_known:
            child.languages_known.append(random.choice(list(CodeLanguage)))

    initiator.energy -= 0.18
    completer.energy -= 0.12
    initiator.mate_cooldown = COOLDOWN_AFTER_FEATURE
    completer.mate_cooldown = COOLDOWN_AFTER_REVIEW

    world.total_matings += 1
    world.spawn_particles(child.x, child.y, (100, 200, 255), count=12, speed=2.0, size=2.5)
    initiator.remember(world.tick, "created_feature", child.id)
    completer.remember(world.tick, "created_feature", child.id)
    child.remember(world.tick, "spawned", initiator.id)
    initiator.instincts.set_cooldown(Instinct.COLLABORATE, COOLDOWN_AFTER_FEATURE)
    completer.instincts.set_cooldown(Instinct.COLLABORATE, COOLDOWN_AFTER_REVIEW)

    world._pending_matings.append({
        "mother_id": initiator.id, "father_id": completer.id,
        "child_id": child.id, "tick": world.tick,
    })

    if gen > 1:
        sym = "FE" if child.gender == Gender.FRONTEND_SPEC else "BE"
        world.log_event(f"👨‍💻 #{child.id}[{sym}] created (gen {gen})")
