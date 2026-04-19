"""Bug finding and reporting — Bug searches for bugs in code, developer receives the info.

Logic:
 1. Bug searches for buggy code in the project's codebase
 2. When found — saves found_bug_in (snippet id)
 3. Upon meeting a developer — Bug delivers the report
 4. Bug dies (squashed), Developer fixes the code
 5. Recorded: who met whom, what bug was fixed
"""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, SignalType, Instinct, Role
from config import VISION_RADIUS, INTERACTION_RADIUS

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity


def bug_scan_code(world: World, bug: Entity):
    """Bug scans code — searches for buggy snippets in project's codebase.

    If Bug's found_bug_in is already set, doesn't search again.
    """
    if bug.found_bug_in is not None:
        return  # already found, waiting for developer

    # first — search in project (if in settlement)
    if bug.settlement_id is not None:
        sett = world.settlements.get(bug.settlement_id)
        if sett and sett.codebase:
            buggy = [s for s in sett.codebase if s.has_bugs]
            if buggy:
                snippet = random.choice(buggy)
                bug.found_bug_in = snippet.id
                bug.flash = 0.6
                world.spawn_particles(bug.x, bug.y, (255, 200, 50),
                                      count=4, speed=1.5, size=1.2)
                return

    # second — search in any nearby project (by radius)
    for sett in world.settlements.values():
        d = math.hypot(bug.x - sett.x, bug.y - sett.y)
        if d < sett.radius * 2 and sett.codebase:
            buggy = [s for s in sett.codebase if s.has_bugs]
            if buggy:
                snippet = random.choice(buggy)
                bug.found_bug_in = snippet.id
                bug.flash = 0.6
                world.spawn_particles(bug.x, bug.y, (255, 200, 50),
                                      count=4, speed=1.5, size=1.2)
                return

    # third — search in global code
    if not world.code_snippets:
        return
    buggy_global = [s for s in world.code_snippets.values() if s.has_bugs]
    if buggy_global and random.random() < 0.15:
        snippet = random.choice(buggy_global)
        bug.found_bug_in = snippet.id
        bug.flash = 0.6
        world.spawn_particles(bug.x, bug.y, (255, 200, 50),
                              count=4, speed=1.5, size=1.2)


def bug_seek_developer(world: World, bug: Entity, all_entities: list):
    """Bug seeks nearest developer to deliver the report.

    If bug hasn't found a bug yet (found_bug_in is None),
    simply moves toward a project to search code.
    """
    vision = VISION_RADIUS * (1 + bug.curiosity * 0.5)
    if world.is_night:
        vision *= 1.3 if bug.nocturnal > 0.5 else 0.8

    # if Bug hasn't found one yet — moves toward project
    if bug.found_bug_in is None:
        _move_toward_settlement(world, bug)
        return

    # Bug found — now searching for developer
    nearest_dev = None
    nearest_dist = vision

    for other in all_entities:
        if other.id == bug.id or not other.alive:
            continue
        if other.entity_type not in (EntityType.DEVELOPER, EntityType.SENIOR_DEV,
                                     EntityType.INTERN, EntityType.AI_COPILOT):
            continue
        d = math.hypot(bug.x - other.x, bug.y - other.y)
        if d < nearest_dist:
            nearest_dev = other
            nearest_dist = d

    if nearest_dev:
        bug.target_id = nearest_dev.id

        # nearby — deliver report + Bug death
        if nearest_dist < INTERACTION_RADIUS:
            _bug_report_to_dev(world, bug, nearest_dev)
            return

        # far away — approach
        dx = nearest_dev.x - bug.x
        dy = nearest_dev.y - bug.y
        d = math.hypot(dx, dy)
        if d > 0:
            bug.dx = bug.dx * 0.4 + (dx / d) * 0.6
            bug.dy = bug.dy * 0.4 + (dy / d) * 0.6
    else:
        # no developer nearby — wander
        _move_toward_settlement(world, bug)


def _bug_report_to_dev(world: World, bug: Entity, dev: Entity):
    """Bug delivers report to developer — Bug dies, Developer fixes.

    This is the key moment: Bug met developer, delivered information,
    and got "squashed".
    """
    snippet = world.code_snippets.get(bug.found_bug_in)

    # --- Bug dies (squashed) ---
    bug.alive = False
    bug.energy = 0
    bug.reported_to_dev = dev.id
    bug.flash = 1.0
    world.spawn_particles(bug.x, bug.y, (255, 100, 100),
                          count=10, speed=3.0, size=2.0)

    # --- Developer fixes ---
    dev.bugs_fixed += 1
    dev.flash = 0.8
    world.spawn_particles(dev.x, dev.y, (100, 255, 100),
                          count=8, speed=2.0, size=1.5)

    # Track combat experience for personality evolution
    try:
        from systems.advanced_lifecycle import _track_personality
        _track_personality(dev, "bug_fixed")
        _track_personality(dev, "combat")
    except Exception:
        pass

    if snippet:
        snippet.has_bugs = False
        snippet.quality = min(1.0, snippet.quality + 0.15)
        snippet.reviewed = True
        snippet.reviewer_id = dev.id

        # project bug_count reduction
        if dev.settlement_id is not None:
            sett = world.settlements.get(dev.settlement_id)
            if sett and sett.bug_count > 0:
                sett.bug_count -= 1

    # --- Memory: Bug met developer ---
    bug.remember(world.tick, "reported_to_dev", dev.id, 1.0)
    dev.remember(world.tick, "bug_report_received", bug.id, 1.0)
    dev.update_relationship(bug.id, 0.1)  # Thanks to bug for the information

    # --- Statistics ---
    world.total_bug_reports += 1



    # --- Event: meeting note ---
    desc = snippet.description if snippet else "unknown"
    world._pending_bug_reports.append({
        "bug_id": bug.id,
        "dev_id": dev.id,
        "snippet_id": bug.found_bug_in,
        "snippet_desc": desc,
        "tick": world.tick,
    })

    world.emit_signal(dev.x, dev.y, SignalType.CODE_REVIEW,
                      sender_id=dev.id,
                      group_id=dev.group_id, max_r=100)

    world.log_event(
        f"🐛→🔧 Bug #{bug.id} met dev #{dev.id}, "
        f"fixed: {desc}")


def _move_toward_settlement(world: World, bug: Entity):
    """Bug moves toward nearest project, searching for code."""
    if not world.settlements:
        return
    nearest_sett = None
    nearest_d = float("inf")
    for sett in world.settlements.values():
        if not sett.codebase:
            continue
        d = math.hypot(bug.x - sett.x, bug.y - sett.y)
        if d < nearest_d:
            nearest_sett = sett
            nearest_d = d

    if nearest_sett and nearest_d > INTERACTION_RADIUS:
        dx = nearest_sett.x - bug.x
        dy = nearest_sett.y - bug.y
        d = math.hypot(dx, dy)
        if d > 0:
            bug.dx = bug.dx * 0.6 + (dx / d) * 0.4
            bug.dy = bug.dy * 0.6 + (dy / d) * 0.4
