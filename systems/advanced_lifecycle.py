"""Advanced Lifecycle — 8 new behavioural systems (Phase 8).

1. Mentorship Chain — Senior→Junior XP transfer
2. Burnout Recovery — vacation mode instead of instant death
3. Reputation System — cumulative score from Judge verdicts + code quality
4. Skill Decay — language XP fades if unused
5. Team Memory — completed project knowledge carries forward
6. Personality Evolution — traits shift based on lived experience
7. Cascade Bugs — critical bugs spread to neighbouring files
8. Project Migration — strong devs leave and start new work

All systems are called from world.step() via `process_advanced_lifecycle`.
"""

from __future__ import annotations

import math
import random
import logging
from typing import TYPE_CHECKING

from core.enums import EntityType, Role, CodeLanguage
from config import (
    SENIOR_MENTOR_RADIUS, SENIOR_XP_TRANSFER, SENIOR_TRAIT_BOOST,
    SENIOR_MENTOR_CHANCE, BURNOUT_ENERGY_THRESHOLD,
    BURNOUT_RECOVERY_TICKS, BURNOUT_REGEN_RATE, REP_GOOD_CODE,
    REP_BAD_CODE, REP_JUDGE_REWARD, REP_JUDGE_PENALTY, REP_DECAY_RATE,
    SKILL_DECAY_INTERVAL, SKILL_DECAY_UNUSED_AFTER, SKILL_DECAY_RATE,
    SKILL_FORGET_THRESHOLD, TEAM_MEMORY_QUALITY_BONUS, TEAM_MEMORY_MAX,
    PERSONALITY_SHIFT_RATE, CASCADE_BUG_QUALITY_THRESHOLD,
    CASCADE_SPREAD_CHANCE, CASCADE_MAX_SPREAD,
    MIGRATION_REPUTATION_THRESHOLD, MIGRATION_ENERGY_THRESHOLD,
    MIGRATION_CHANCE,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity

log = logging.getLogger("systems.advanced_lifecycle")


# ══════════════════════════════════════════════════════════════════════
# 1. MENTORSHIP CHAIN — Senior / AI_Copilot → Intern / Developer
# ══════════════════════════════════════════════════════════════════════

def _process_mentorship_chain(world: "World"):
    """Senior devs & AI Copilots mentor nearby juniors.
    
    Unlike Teacher entities (who teach languages), this transfers
    specialisation XP and improves traits directly.
    """
    seniors = [e for e in world.entities
               if e.alive and e.entity_type in (EntityType.SENIOR_DEV,
                                                  EntityType.AI_COPILOT)]
    if not seniors:
        return

    juniors = [e for e in world.entities
               if e.alive and e.entity_type in (EntityType.DEVELOPER,
                                                  EntityType.INTERN)
               and not getattr(e, 'burnout', False)]
    if not juniors:
        return

    for senior in seniors:
        if senior.energy < 0.15:
            continue
        mentored = 0
        for junior in juniors:
            if mentored >= 3:
                break
            d = math.hypot(senior.x - junior.x, senior.y - junior.y)
            if d > SENIOR_MENTOR_RADIUS:
                continue
            if random.random() > SENIOR_MENTOR_CHANCE:
                continue

            # Transfer best language XP
            if senior.language_xp:
                best_lang = max(senior.language_xp, key=senior.language_xp.get)
                cur = junior.language_xp.get(best_lang, 0.0)
                senior_xp = senior.language_xp[best_lang]
                if cur < senior_xp * 0.8:
                    junior.language_xp[best_lang] = cur + SENIOR_XP_TRANSFER
                    junior.language_last_used[best_lang] = world.tick

            # Nudge traits toward mentor's strengths
            if senior.resilience > junior.resilience:
                junior.resilience = min(1.0, junior.resilience + SENIOR_TRAIT_BOOST)
            if senior.curiosity > junior.curiosity:
                junior.curiosity = min(1.0, junior.curiosity + SENIOR_TRAIT_BOOST)

            # Small energy transfer
            senior.energy = max(0.0, senior.energy - 0.008)
            junior.energy = min(1.0, junior.energy + 0.01)

            mentored += 1
            senior.students_taught += 1
            if hasattr(world, "total_mentorships"):
                world.total_mentorships += 1
            _track_personality(junior, "mentored")


# ══════════════════════════════════════════════════════════════════════
# 2. BURNOUT RECOVERY — vacation mode
# ══════════════════════════════════════════════════════════════════════

def _process_burnout(world: "World"):
    """Entities near death enter burnout instead of dying.
    
    During burnout they can't CODE or DEPLOY but slowly recover.
    Only triggers once — if energy hits 0 again after recovery, they die.
    """
    for e in world.entities:
        if not e.alive:
            continue

        # Already in burnout — recover
        if getattr(e, 'burnout', False):
            e.burnout_ticks -= 1
            e.energy = min(0.5, e.energy + BURNOUT_REGEN_RATE)
            if e.burnout_ticks <= 0:
                e.burnout = False
                e.burnout_ticks = 0
                _track_personality(e, "recovered_burnout")
                try:
                    world.log_event(
                        f"🌴 #{e.id} finished vacation — back to work! "
                        f"(energy: {e.energy:.0%})")
                except Exception:
                    pass
            continue

        # Check if should enter burnout (first time only)
        if (e.energy < BURNOUT_ENERGY_THRESHOLD
                and e.energy > 0
                and e.entity_type != EntityType.BUG
                and not getattr(e, '_had_burnout', False)):
            e.burnout = True
            e.burnout_ticks = BURNOUT_RECOVERY_TICKS
            e._had_burnout = True  # only one burnout per lifetime
            e.energy = max(0.05, e.energy)  # prevent death
            if hasattr(world, "total_burnouts"):
                world.total_burnouts += 1
            _track_personality(e, "entered_burnout")
            try:
                world.log_event(
                    f"😴 #{e.id} is burned out! Taking a vacation "
                    f"({BURNOUT_RECOVERY_TICKS} ticks)")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════
# 3. REPUTATION SYSTEM
# ══════════════════════════════════════════════════════════════════════

def _process_reputation(world: "World"):
    """Update reputation based on code quality and Judge interactions.
    
    High reputation: chosen as TEAM_LEAD more often, better inheritance.
    Low reputation: harder to find mates, less energy from team.
    """
    snippets = getattr(world, 'code_snippets', {})

    for e in world.entities:
        if not e.alive or e.entity_type == EntityType.BUG:
            continue

        rep = getattr(e, 'reputation', 0.5)

        # Code quality contribution — sample recent output
        authored = [s for s in snippets.values()
                    if s.author_id == e.id
                    and world.tick - getattr(s, 'tick_created', 0) < 300]
        for snip in authored[-5:]:  # last 5 recent snippets
            if snip.quality >= 0.70 and not snip.has_bugs:
                rep += REP_GOOD_CODE
            elif snip.has_bugs or snip.quality < 0.45:
                rep += REP_BAD_CODE

        # Slow drift toward 0.5 (regression to mean)
        rep += (0.5 - rep) * REP_DECAY_RATE

        e.reputation = max(0.0, min(1.0, rep))


def update_reputation_from_judge(entity: "Entity", is_reward: bool):
    """Called from mentoring.py when Judge issues verdict."""
    rep = getattr(entity, 'reputation', 0.5)
    if is_reward:
        rep += REP_JUDGE_REWARD
    else:
        rep += REP_JUDGE_PENALTY
    entity.reputation = max(0.0, min(1.0, rep))


# ══════════════════════════════════════════════════════════════════════
# 4. SKILL DECAY — use it or lose it
# ══════════════════════════════════════════════════════════════════════

def _process_skill_decay(world: "World"):
    """Language XP decays if not used for a long time."""
    for e in world.entities:
        if not e.alive or not e.language_xp:
            continue

        last_used = getattr(e, 'language_last_used', {})
        langs_to_remove = []

        for lang_key, xp in list(e.language_xp.items()):
            last = last_used.get(lang_key, 0)
            idle_ticks = world.tick - last

            if idle_ticks > SKILL_DECAY_UNUSED_AFTER and xp > 0:
                decay = SKILL_DECAY_RATE * (idle_ticks / SKILL_DECAY_UNUSED_AFTER)
                e.language_xp[lang_key] = max(0.0, xp - decay)

                # Forget language entirely if XP drops very low
                if e.language_xp[lang_key] < SKILL_FORGET_THRESHOLD:
                    # Find the CodeLanguage enum and remove
                    for lang in list(e.languages_known):
                        if lang.value == lang_key and len(e.languages_known) > 1:
                            langs_to_remove.append(lang)
                            break

        for lang in langs_to_remove:
            if lang in e.languages_known and len(e.languages_known) > 1:
                e.languages_known.remove(lang)
                if lang.value in e.language_xp:
                    del e.language_xp[lang.value]
                try:
                    world.log_event(
                        f"📉 #{e.id} forgot {lang.value} (unused too long)")
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════
# 5. TEAM MEMORY — institutional knowledge from past projects
# ══════════════════════════════════════════════════════════════════════

def record_team_memory(world: "World", project_entry: dict):
    """Store completed project's metrics as team memory.
    
    Called from shared_project._complete_project().
    """
    memory_list = getattr(world, '_team_memory', None)
    if memory_list is None:
        world._team_memory = []
        memory_list = world._team_memory

    memory_list.append({
        "name": project_entry.get("name", ""),
        "quality": project_entry.get("code_quality", 0.5),
        "tech_stack": project_entry.get("tech_stack", []),
        "files_count": project_entry.get("files_count", 0),
        "bug_count": project_entry.get("bug_count", 0),
        "tick_finished": project_entry.get("tick_finished", 0),
    })

    # Keep bounded
    if len(memory_list) > TEAM_MEMORY_MAX:
        memory_list.pop(0)


def get_team_memory_bonus(world: "World", tech_stack: list) -> float:
    """Quality bonus from past experience with similar tech.
    
    Returns a float [0, 0.15] quality bonus.
    """
    memory_list = getattr(world, '_team_memory', [])
    if not memory_list:
        return 0.0

    tech_values = set()
    for t in tech_stack:
        tech_values.add(t.value if hasattr(t, 'value') else str(t))

    bonus = 0.0
    for mem in memory_list:
        overlap = len(tech_values & set(mem.get("tech_stack", [])))
        if overlap > 0:
            bonus += TEAM_MEMORY_QUALITY_BONUS * min(overlap, 3)

    return min(0.15, bonus)


# ══════════════════════════════════════════════════════════════════════
# 6. PERSONALITY EVOLUTION — traits change with experience
# ══════════════════════════════════════════════════════════════════════

def _track_personality(entity: "Entity", event_type: str):
    """Record a personality-shaping event."""
    pxp = getattr(entity, 'personality_xp', None)
    if pxp is None:
        entity.personality_xp = {}
        pxp = entity.personality_xp

    pxp[event_type] = pxp.get(event_type, 0) + 1


def _process_personality_evolution(world: "World"):
    """Shift traits based on accumulated experience."""
    for e in world.entities:
        if not e.alive:
            continue

        pxp = getattr(e, 'personality_xp', {})
        if not pxp:
            continue

        shift = PERSONALITY_SHIFT_RATE

        # Combat experience → aggression↑
        combat_xp = pxp.get("combat", 0) + pxp.get("bug_fixed", 0)
        if combat_xp > 5:
            e.aggression = min(1.0, e.aggression + shift * min(combat_xp, 20))

        # Meetings / collaboration → sociability↑
        social_xp = pxp.get("meeting", 0) + pxp.get("mentored", 0)
        if social_xp > 5:
            e.sociability = min(1.0, e.sociability + shift * min(social_xp, 20))

        # Learning / exploration → curiosity↑
        learn_xp = pxp.get("learned_language", 0) + pxp.get("knowledge_discovered", 0)
        if learn_xp > 3:
            e.curiosity = min(1.0, e.curiosity + shift * min(learn_xp, 15))

        # Surviving burnout → resilience↑
        survive_xp = pxp.get("recovered_burnout", 0)
        if survive_xp > 0:
            e.resilience = min(1.0, e.resilience + shift * 5 * survive_xp)

        # Decay counters slowly so personality stops shifting eventually
        for k in list(pxp.keys()):
            if pxp[k] > 0:
                pxp[k] = max(0, pxp[k] - 1)


# ══════════════════════════════════════════════════════════════════════
# 7. CASCADE BUGS — critical bugs spread
# ══════════════════════════════════════════════════════════════════════

def _process_cascade_bugs(world: "World"):
    """Very low-quality buggy code can infect neighbouring files."""
    proj = getattr(world, '_active_project', None)
    if proj is None or not proj.codebase:
        return

    # Find critically buggy snippets
    critical = [s for s in proj.codebase
                if getattr(s, 'has_bugs', False)
                and getattr(s, 'quality', 1.0) < CASCADE_BUG_QUALITY_THRESHOLD]

    if not critical:
        return

    for bad_snippet in critical:
        spread_count = 0
        # "Neighbouring" = other files in same project that are clean
        clean = [s for s in proj.codebase
                 if not getattr(s, 'has_bugs', False) and s.id != bad_snippet.id]

        for target in clean:
            if spread_count >= CASCADE_MAX_SPREAD:
                break
            if random.random() < CASCADE_SPREAD_CHANCE:
                target.has_bugs = True
                target.quality = max(0.1, target.quality - 0.15)
                proj.bug_count += 1
                spread_count += 1

        if spread_count > 0:
            try:
                world.log_event(
                    f"🦠 Cascade bug! Critical bug in "
                    f"'{getattr(bad_snippet, 'filename', '?')}' "
                    f"spread to {spread_count} more file(s) "
                    f"in '{proj.project_name}'")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════
# 8. PROJECT MIGRATION — strong devs break away
# ══════════════════════════════════════════════════════════════════════

def _process_migration(world: "World"):
    """High-reputation devs may leave current project to start fresh.
    
    This creates more project diversity instead of everyone on one job.
    """
    proj = getattr(world, '_active_project', None)
    if proj is None:
        return

    # Only during development phase (not architecture/review)
    if getattr(proj, 'phase', '') != 'development':
        return

    members = [e for e in world.entities
               if e.alive and e.settlement_id == proj.id
               and e.entity_type not in (EntityType.BUG, EntityType.TEACHER,
                                          EntityType.JUDGE)]

    # Don't let team get too small
    if len(members) < 15:
        return

    for e in members:
        rep = getattr(e, 'reputation', 0.5)
        if (rep >= MIGRATION_REPUTATION_THRESHOLD
                and e.energy >= MIGRATION_ENERGY_THRESHOLD
                and random.random() < MIGRATION_CHANCE):
            # Leave current project
            e.settlement_id = None
            e.role = Role.NONE
            # Scatter to a new area
            e.x += random.uniform(-300, 300)
            e.y += random.uniform(-200, 200)
            from config import WORLD_WIDTH, WORLD_HEIGHT
            e.x = max(50, min(WORLD_WIDTH - 50, e.x))
            e.y = max(50, min(WORLD_HEIGHT - 50, e.y))

            _track_personality(e, "migrated")
            if hasattr(world, "total_migrations"):
                world.total_migrations += 1
            try:
                world.log_event(
                    f"🚶 #{e.id} ({e.entity_type.value}) left "
                    f"'{proj.project_name}' to explore new opportunities "
                    f"(reputation: {rep:.0%})")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — called from world.step()
# ══════════════════════════════════════════════════════════════════════

def process_advanced_lifecycle(world: "World", tick_mod: int = 0):
    """Run all advanced lifecycle systems.

    *tick_mod* is ``world.tick`` so sub-systems can gate on intervals.
    """
    tick = tick_mod or getattr(world, 'tick', 0)

    # Every tick: burnout check (must be responsive)
    _process_burnout(world)

    # Every 30 ticks: mentorship, reputation, personality
    if tick % 30 == 0:
        _process_mentorship_chain(world)
        _process_reputation(world)

    # Every 60 ticks: personality shifts
    if tick % 60 == 0:
        _process_personality_evolution(world)

    # Every 200 ticks: skill decay
    if tick % SKILL_DECAY_INTERVAL == 0:
        _process_skill_decay(world)

    # Every 100 ticks: cascade bugs, migration
    if tick % 100 == 0:
        _process_cascade_bugs(world)
        _process_migration(world)
