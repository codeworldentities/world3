"""Mentoring — Teacher & Judge entity behaviour (phase 7C).

Teachers seek out low-XP developers nearby and transfer language knowledge /
boost XP. Judges observe recent commits and either reward good work with
energy or penalise buggy work by draining energy. They do not themselves
generate code.

Both systems run every few dozen ticks from `world.step()`.
"""

from __future__ import annotations

import logging
import math
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, CodeLanguage

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity

log = logging.getLogger("systems.mentoring")

# How close an entity must be to a Teacher/Judge to be affected.
MENTOR_RADIUS = 80.0

# Each Teacher tick affects at most this many nearby students.
MAX_STUDENTS_PER_TEACHER = 4

# XP granted to a student when touched by a Teacher.
TEACH_XP_GAIN = 1.5

# Chance that a Teacher transfers an unknown language to a nearby dev.
TEACH_LANGUAGE_CHANCE = 0.35

# Judge thresholds.
JUDGE_REWARD_QUALITY = 0.70      # quality above this → reward
JUDGE_REWARD_ENERGY = 0.12       # energy bonus for good code
JUDGE_PENALTY_ENERGY = 0.08      # energy drained for buggy code

# Per-call limits to keep the loop bounded.
MAX_REWARDS_PER_CALL = 8
MAX_PENALTIES_PER_CALL = 8


def _log_event(world: "World", msg: str) -> None:
    try:
        world.log_event(msg)
    except AttributeError:
        pass


# ──────────────────────────────────────────────────────────────────
# Teacher behaviour
# ──────────────────────────────────────────────────────────────────

def process_teaching(world: "World") -> int:
    """Teachers mentor nearby devs. Returns number of students mentored."""
    teachers = [e for e in world.entities
                if e.alive and e.entity_type == EntityType.TEACHER]
    if not teachers:
        return 0

    # candidate students — anything that can code
    students = [e for e in world.entities
                if e.alive and e.can_code]
    if not students:
        return 0

    total_mentored = 0
    for teacher in teachers:
        # find nearby students sorted by distance
        nearby: list[tuple[float, "Entity"]] = []
        for s in students:
            if s.id == teacher.id:
                continue
            d = math.hypot(teacher.x - s.x, teacher.y - s.y)
            if d <= MENTOR_RADIUS:
                nearby.append((d, s))
        if not nearby:
            continue

        nearby.sort(key=lambda p: p[0])
        for _, student in nearby[:MAX_STUDENTS_PER_TEACHER]:
            _teach(world, teacher, student)
            total_mentored += 1

    return total_mentored


def _teach(world: "World", teacher: "Entity", student: "Entity") -> None:
    """Apply one teacher→student interaction."""
    # pick a language the teacher knows to focus on
    if not teacher.languages_known:
        return

    lang = random.choice(teacher.languages_known)
    key = lang.value

    # Language transfer — if student doesn't know it yet.
    if lang not in student.languages_known:
        if random.random() < TEACH_LANGUAGE_CHANCE:
            student.languages_known.append(lang)
            _log_event(
                world,
                f"👨‍🏫 Teacher #{teacher.id} taught #{student.id} "
                f"a new language: {lang.value}",
            )
            teacher.students_taught += 1
            # small energy cost / reward
            teacher.energy = max(0.0, teacher.energy - 0.02)
            student.energy = min(1.0, student.energy + 0.04)
            return

    # Otherwise — boost XP in a language both already know.
    student.language_xp[key] = student.language_xp.get(key, 0.0) + TEACH_XP_GAIN
    # Tiny quality nudge — practice improves average.
    student.code_quality = min(1.0, student.code_quality + 0.01)
    teacher.students_taught += 1


# ──────────────────────────────────────────────────────────────────
# Judge behaviour
# ──────────────────────────────────────────────────────────────────

def process_judgement(world: "World") -> tuple[int, int]:
    """Judges reward/penalise entities based on their recent code commits.

    Returns (rewards_granted, penalties_applied).
    """
    judges = [e for e in world.entities
              if e.alive and e.entity_type == EntityType.JUDGE]
    if not judges:
        return (0, 0)

    # Snippets table lives on world; consult only un-judged ones.
    snippets = getattr(world, "code_snippets", None)
    if not snippets:
        return (0, 0)

    # Collect snippets that have not been judged yet.
    unjudged: list = []
    for sid, snip in snippets.items():
        if getattr(snip, "_judged", False):
            continue
        unjudged.append(snip)

    if not unjudged:
        return (0, 0)

    # Sort by tick_created descending (most recent first).
    unjudged.sort(key=lambda s: getattr(s, "tick_created", 0), reverse=True)

    rewards = 0
    penalties = 0
    entities_by_id = {e.id: e for e in world.entities}

    for snip in unjudged:
        if rewards >= MAX_REWARDS_PER_CALL and penalties >= MAX_PENALTIES_PER_CALL:
            break
        author = entities_by_id.get(snip.author_id)
        if author is None or not author.alive:
            snip._judged = True
            continue

        # Need at least one Judge within range to pass verdict.
        j = _nearest_judge(judges, author.x, author.y)
        if j is None:
            continue  # leave unjudged for next tick when a judge roams close

        if snip.has_bugs or snip.quality < 0.45:
            if penalties >= MAX_PENALTIES_PER_CALL:
                continue
            drain = JUDGE_PENALTY_ENERGY
            author.energy = max(0.0, author.energy - drain)
            author.judge_penalties += drain
            j.energy = min(1.0, j.energy + drain * 0.25)  # judge rewarded
            snip._judged = True
            penalties += 1
            # Reputation update
            try:
                from systems.advanced_lifecycle import update_reputation_from_judge
                update_reputation_from_judge(author, False)
            except Exception:
                pass
            _log_event(
                world,
                f"⚖️ Judge #{j.id} fined #{author.id} for buggy "
                f"{snip.language.value} ({snip.description})",
            )
        elif snip.quality >= JUDGE_REWARD_QUALITY and not snip.has_bugs:
            if rewards >= MAX_REWARDS_PER_CALL:
                continue
            bonus = JUDGE_REWARD_ENERGY
            author.energy = min(1.0, author.energy + bonus)
            author.judge_rewards += bonus
            # Specialisation XP award for excellent work.
            key = snip.language.value
            author.language_xp[key] = author.language_xp.get(key, 0.0) + 2.0
            j.energy = max(0.0, j.energy - bonus * 0.15)
            snip._judged = True
            rewards += 1
            # Reputation update
            try:
                from systems.advanced_lifecycle import update_reputation_from_judge
                update_reputation_from_judge(author, True)
            except Exception:
                pass
            _log_event(
                world,
                f"🏅 Judge #{j.id} rewarded #{author.id} "
                f"({snip.language.value} q={snip.quality:.2f})",
            )
        else:
            # Mediocre — mark as judged with no effect.
            snip._judged = True

    return (rewards, penalties)


def _nearest_judge(judges: list, x: float, y: float):
    """Return nearest Judge within MENTOR_RADIUS, or None."""
    best = None
    best_d = MENTOR_RADIUS
    for j in judges:
        d = math.hypot(j.x - x, j.y - y)
        if d < best_d:
            best_d = d
            best = j
    return best


# ──────────────────────────────────────────────────────────────────
# Commit-time helper — called from systems/code_gen.py after a snippet
# is appended to a project. Awards baseline XP to the author.
# ──────────────────────────────────────────────────────────────────

def grant_commit_xp(entity: "Entity", language: CodeLanguage,
                    quality: float) -> None:
    """Award baseline specialisation XP for a commit."""
    key = language.value
    gain = 1.0 + max(0.0, quality - 0.5) * 2.0
    entity.language_xp[key] = entity.language_xp.get(key, 0.0) + gain
