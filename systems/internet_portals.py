"""Internet portal system.

Entities can enter world "holes" (portals) to fetch external intelligence
from GitHub / Reddit / Google / Docs and bring actionable insights back.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from core.enums import CodeLanguage, EntityType
from config import (
    WORLD_WIDTH,
    WORLD_HEIGHT,
    INTERNET_PORTAL_COUNT,
    INTERNET_PORTAL_RADIUS,
    INTERNET_MISSION_MIN_TICKS,
    INTERNET_MISSION_MAX_TICKS,
    INTERNET_REPORT_COOLDOWN,
    INTERNET_BOOST_QUALITY,
    INTERNET_BUGFIX_CHANCE,
    INTERNET_KNOWLEDGE_SHARE_CHANCE,
    INTERNET_OPEN_SOURCE_BOOST,
)

if TYPE_CHECKING:
    from core.world import World

_PORTAL_SOURCES = [
    ("github", "GitHub"),
    ("reddit", "Reddit"),
    ("google", "Google"),
    ("docs", "Docs"),
    ("stackoverflow", "StackOverflow"),
]


def _new_portal(pid: int) -> dict:
    source, label = random.choice(_PORTAL_SOURCES)
    return {
        "id": pid,
        "source": source,
        "label": label,
        "x": random.uniform(120, WORLD_WIDTH - 120),
        "y": random.uniform(120, WORLD_HEIGHT - 120),
        "radius": INTERNET_PORTAL_RADIUS,
    }


def ensure_portals(world: World):
    if getattr(world, "web_portals", None):
        return
    world.web_portals = [_new_portal(i) for i in range(INTERNET_PORTAL_COUNT)]
    world.log_event(f"🕳 {len(world.web_portals)} internet portals appeared in the world")


def _start_mission(world: World, e, portal: dict, tick: int):
    prev = e.entity_type
    if prev != EntityType.WEB_SCOUT:
        e.entity_type = EntityType.WEB_SCOUT
        e.remember(tick, f"portal:converted:{prev.name}", None, 0.2)

    e.web_source = portal["source"]
    e.web_mission_until = tick + random.randint(INTERNET_MISSION_MIN_TICKS, INTERNET_MISSION_MAX_TICKS)
    e.web_last_report_tick = tick
    world.total_portal_trips += 1
    world.log_event(f"🕳 #{e.id} entered {portal['label']} portal and is researching...")
    world.spawn_particles(portal["x"], portal["y"], (120, 240, 255), count=14, speed=2.2, size=2.2)


def _report_back(world: World, e, tick: int):
    source = (e.web_source or "").lower()
    if not source:
        return

    proj = getattr(world, "_active_project", None)
    summary = "new insights"

    if proj is not None:
        # Boost a few snippets with internet-found patterns.
        snippets = [s for s in proj.codebase if hasattr(s, "quality")]
        if snippets:
            for s in random.sample(snippets, min(3, len(snippets))):
                s.quality = min(1.0, s.quality + INTERNET_BOOST_QUALITY)

        # Fix one bug occasionally from internet research.
        buggy = [s for s in proj.codebase if getattr(s, "has_bugs", False)]
        if buggy and random.random() < INTERNET_BUGFIX_CHANCE:
            fixed = random.choice(buggy)
            fixed.has_bugs = False
            fixed.reviewed = True
            fixed.quality = min(1.0, fixed.quality + INTERNET_BOOST_QUALITY)
            proj.bug_count = max(0, proj.bug_count - 1)
            summary = f"fixed issue in {fixed.filename}"

        # Share language knowledge with project members.
        members = [x for x in world.entities if x.alive and x.settlement_id == proj.id]
        if members and random.random() < INTERNET_KNOWLEDGE_SHARE_CHANCE:
            learner = random.choice(members)
            missing = [l for l in CodeLanguage if l not in learner.languages_known]
            if missing:
                new_lang = random.choice(missing)
                learner.languages_known.append(new_lang)
                summary = f"shared {new_lang.value} workflow"

        # Open-source growth indicator.
        world.open_source_growth = min(100.0, world.open_source_growth + INTERNET_OPEN_SOURCE_BOOST)

    e.web_reports += 1
    e.web_source = ""
    e.web_mission_until = 0
    e.web_last_report_tick = tick
    world.total_web_reports += 1

    source_title = source.capitalize() if source else "Web"
    world.log_event(f"🌐 #{e.id} returned from {source_title} with {summary} for the active project")
    world.spawn_particles(e.x, e.y, (80, 255, 180), count=10, speed=2.0, size=2.0)


def process_internet_portals(world: World, tick: int):
    ensure_portals(world)

    # Slight drift keeps portals dynamic while staying on map.
    if tick % 250 == 0:
        for p in world.web_portals:
            p["x"] = min(WORLD_WIDTH - 80, max(80, p["x"] + random.uniform(-70, 70)))
            p["y"] = min(WORLD_HEIGHT - 80, max(80, p["y"] + random.uniform(-70, 70)))

    for e in world.entities:
        if not e.alive or e.entity_type == EntityType.BUG:
            continue

        # If mission completed, deliver report once.
        if e.web_mission_until and tick >= e.web_mission_until:
            _report_back(world, e, tick)
            continue

        # If currently in mission, keep entity roaming lightly.
        if e.web_mission_until and tick < e.web_mission_until:
            e.dx += random.uniform(-0.1, 0.1)
            e.dy += random.uniform(-0.1, 0.1)
            continue

        if (tick - e.web_last_report_tick) < INTERNET_REPORT_COOLDOWN:
            continue

        for portal in world.web_portals:
            d = math.hypot(e.x - portal["x"], e.y - portal["y"])
            if d <= portal["radius"] and random.random() < 0.35:
                _start_mission(world, e, portal, tick)
                break
