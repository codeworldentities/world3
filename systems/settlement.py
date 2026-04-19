"""Projects — formation, role distribution, technologies, leader."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, Role, TechType, CodeLanguage
from core.models import Settlement
from config import (
    PROJECT_MIN_TEAM_SIZE, PROJECT_MIN_TICKS_TOGETHER,
    PROJECT_RADIUS, PROJECT_MAX_TEAM,
    TECH_TREE, TECH_BONUSES, ROLE_BONUSES,
    LEAD_MIN_AGE,
    WORLD_WIDTH, WORLD_HEIGHT,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity

# project names
_PROJECT_NAMES = [
    "CodeForge", "ByteFlow", "PixelStack", "DataPulse", "CloudNest",
    "NodeHive", "GitStream", "DevPulse", "BitForge", "LogicHub",
    "StackBridge", "HexGrid", "FlowEngine", "NeuralKit", "PipeWorks",
    "RustBlade", "PyForge", "GoRunner", "ReactPulse", "SqlVault",
    "MeshOps", "LintMaster", "TestPilot", "DocuGen", "APICraft",
]


def update_settlements(world: World):
    """Organize teams into projects and update projects."""
    group_members: dict[int, list] = {}
    for e in world.entities:
        if e.group_id is not None:
            group_members.setdefault(e.group_id, []).append(e)

    dead_settlements = []
    for sid, sett in world.settlements.items():
        members = group_members.get(sett.group_id, [])
        nearby = [m for m in members
                  if math.hypot(m.x - sett.x, m.y - sett.y) < sett.radius * 1.5]
        sett.population = len(nearby)
        if sett.population == 0:
            dead_settlements.append(sid)
        else:
            sett.x = sett.x * 0.95 + sum(m.x for m in nearby) / len(nearby) * 0.05
            sett.y = sett.y * 0.95 + sum(m.y for m in nearby) / len(nearby) * 0.05
            for m in nearby:
                m.settlement_id = sid

    for sid in dead_settlements:
        sett = world.settlements[sid]
        # on GitHub push archiving
        if sett.codebase:
            try:
                from systems.github_integration import push_completed_project, is_enabled
                if is_enabled() and sett.project_name:
                    push_completed_project(sett, list(sett.codebase), "archived")
            except Exception:
                pass
        del world.settlements[sid]
        name = sett.project_name or f"#{sid}"
        world.log_event(f"📁 Project {name} archived")

    settled_groups = {s.group_id for s in world.settlements.values()}
    for gid, members in group_members.items():
        if gid in settled_groups or len(members) < PROJECT_MIN_TEAM_SIZE:
            continue
        cx = sum(m.x for m in members) / len(members)
        cy = sum(m.y for m in members) / len(members)
        max_d = max(math.hypot(m.x - cx, m.y - cy) for m in members)
        if max_d > PROJECT_RADIUS * 2:
            continue
        old_members = [m for m in members if m.age > PROJECT_MIN_TICKS_TOGETHER]
        if len(old_members) < 1:
            continue

        sid = world.next_settlement_id
        world.next_settlement_id += 1

        project_name = random.choice(_PROJECT_NAMES) + f"-{sid}"

        # project tech stack — most common languages in team
        lang_counts: dict[CodeLanguage, int] = {}
        for m in members:
            for lang in m.languages_known:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        tech_stack = sorted(lang_counts, key=lang_counts.get, reverse=True)[:3]

        sett = Settlement(
            id=sid, group_id=gid, x=cx, y=cy,
            founded_tick=world.tick, population=len(members),
            project_name=project_name,
            tech_stack=tech_stack,
        )
        world.settlements[sid] = sett
        world.total_settlements += 1
        for m in members:
            m.settlement_id = sid
            m.home_x = cx + random.uniform(-30, 30)
            m.home_y = cy + random.uniform(-30, 30)
        world.log_event(
            f"📂 Project '{project_name}' founded! "
            f"(team #{gid}, {len(members)} devs)")

        world.spawn_particles(cx, cy, (100, 180, 255), count=20, speed=3.0, size=3.0)


def assign_roles(world: World):
    """Distribute roles in the project team."""
    for sid, sett in world.settlements.items():
        members = [e for e in world.entities if e.settlement_id == sid and e.alive]
        if not members:
            continue
        for e in members:
            # Team Lead — experienced
            if e.age > 1000 and e.role == Role.NONE:
                leads = sum(1 for m in members if m.role == Role.TEAM_LEAD)
                if leads < max(1, len(members) // 8):
                    e.role = Role.TEAM_LEAD
                    continue
            if e.role != Role.NONE:
                continue
            # Reviewer — high attention
            if e.sociability > 0.6 and e.resilience > 0.4:
                reviewers = sum(1 for m in members if m.role == Role.REVIEWER)
                if reviewers < max(1, len(members) // 4):
                    e.role = Role.REVIEWER
                    continue
            # Architect — high curiosity
            if e.curiosity > 0.6:
                archs = sum(1 for m in members if m.role == Role.ARCHITECT)
                if archs < max(1, len(members) // 5):
                    e.role = Role.ARCHITECT
                    continue
            # Tester — agressiveness + attention
            if e.aggression > 0.5 and e.resilience > 0.3:
                testers = sum(1 for m in members if m.role == Role.TESTER)
                if testers < max(1, len(members) // 5):
                    e.role = Role.TESTER
                    continue
            # DevOps
            if e.curiosity > 0.4 and e.resilience > 0.5:
                devops = sum(1 for m in members if m.role == Role.DEVOPS_ENG)
                if devops < max(1, len(members) // 6):
                    e.role = Role.DEVOPS_ENG
                    continue


def try_discover_tech(world: World):
    """Technology discovery in projects (Docker, CI/CD, K8s, etc.)."""
    for sid, sett in world.settlements.items():
        members = [e for e in world.entities if e.settlement_id == sid and e.alive]
        pop = len(members)
        if pop == 0:
            continue
        oldest_age = max(m.age for m in members)
        leads = [m for m in members if m.role == Role.TEAM_LEAD]
        devops = [m for m in members if m.role == Role.DEVOPS_ENG]
        for tech, (min_pop, min_age, prereq, chance) in TECH_TREE.items():
            if sett.has_tech(tech):
                continue
            if pop < min_pop or oldest_age < min_age:
                continue
            if prereq is not None and not sett.has_tech(prereq):
                continue
            eff_chance = chance * (1.0 + 0.5 * len(leads) + 0.8 * len(devops))
            culture = world.group_cultures.get(sett.group_id)
            if culture:
                eff_chance *= (0.5 + culture.cooperation)
            if random.random() < eff_chance:
                sett.techs.append(tech)
                world.total_techs_discovered += 1
                name = sett.project_name or f"#{sid}"
                world.log_event(
                    f"🔧 {name}: {tech.value} deployed! (level {sett.tech_level})")
                world.spawn_particles(sett.x, sett.y, (100, 255, 200),
                                      count=25, speed=4.0, size=3.5)
                for lead in leads:
                    lead.remember(world.tick, f"deployed:{tech.value}", None, 1.0)


def settlement_resource_production(world: World):
    """Projects produce resources (documentation, coffee fund)."""
    for sid, sett in world.settlements.items():
        if sett.population == 0:
            continue
        production = 0.01 * sett.population
        resource_mult = 1.0
        for tech in sett.techs:
            resource_mult *= TECH_BONUSES[tech][4]
        devops_count = sum(1 for e in world.entities
                          if e.settlement_id == sid and e.role == Role.DEVOPS_ENG)
        production *= (1.0 + 0.15 * devops_count) * resource_mult
        sett.stored_resources += production

        if sett.stored_resources > 1.0:
            sett.stored_resources -= 1.0
            rx = max(0, min(WORLD_WIDTH, sett.x + random.uniform(-sett.radius * 0.6, sett.radius * 0.6)))
            ry = max(0, min(WORLD_HEIGHT, sett.y + random.uniform(-sett.radius * 0.6, sett.radius * 0.6)))
            world._spawn_resource(rx, ry)

        # CI/CD technology adds automatic docs
        if sett.has_tech(TechType.CI_CD) and random.random() < 0.02:
            rx = max(0, min(WORLD_WIDTH, sett.x + random.uniform(-sett.radius * 0.4, sett.radius * 0.4)))
            ry = max(0, min(WORLD_HEIGHT, sett.y + random.uniform(-sett.radius * 0.4, sett.radius * 0.4)))
            world._spawn_resource(rx, ry)

        # commits counter
        architects = sum(1 for e in world.entities
                        if e.settlement_id == sid and e.role == Role.ARCHITECT)
        if architects > 0 and random.random() < 0.003 * architects:
            sett.total_commits += 1
            sett.buildings += 1
            if sett.total_commits % 10 == 0:
                name = sett.project_name or f"#{sid}"
                world.log_event(f"📊 {name}: {sett.total_commits} commits!")


def elect_leaders(world: World):
    """Elect Team Lead in each project."""
    for sid, sett in world.settlements.items():
        members = [e for e in world.entities if e.settlement_id == sid and e.alive]
        if not members:
            sett.leader_id = None
            continue
        if sett.leader_id is not None:
            leader_alive = any(e.id == sett.leader_id and e.alive for e in members)
            if leader_alive:
                continue

        best_e, best_score = None, -1
        for e in members:
            if e.age < LEAD_MIN_AGE:
                continue
            score = (e.age * 0.3 + e.energy * 200 + len(e.relationships) * 10
                     + len(e.memories) * 5 + e.sociability * 100 + e.resilience * 80
                     + e.commits * 20 + e.reviews_done * 15 + e.bugs_fixed * 25
                     + getattr(e, 'reputation', 0.5) * 150)
            if e.role == Role.TEAM_LEAD:
                score *= 1.5
            if e.entity_type == EntityType.SENIOR_DEV:
                score *= 1.3
            if score > best_score:
                best_score = score
                best_e = e

        old_leader = sett.leader_id
        if best_e:
            sett.leader_id = best_e.id
            if old_leader != best_e.id:
                name = sett.project_name or f"#{sid}"
                world.log_event(f"👑 {name}: Team Lead #{best_e.id}!")
                world.spawn_particles(best_e.x, best_e.y, (255, 215, 0),
                                      count=15, speed=3.0, size=2.5)
        else:
            sett.leader_id = None


def get_settlement_bonuses(world: World, e) -> tuple:
    """(energy_bonus, speed_bonus, debug_bonus, defense_bonus)"""
    if e.settlement_id is None:
        return (0.0, 0.0, 0.0, 0.0)
    sett = world.settlements.get(e.settlement_id)
    if not sett:
        return (0.0, 0.0, 0.0, 0.0)
    eb, sb, hb, db = 0.0, 0.0, 0.0, 0.0
    for tech in sett.techs:
        bonuses = TECH_BONUSES[tech]
        eb += bonuses[0]; sb += bonuses[1]; hb += bonuses[2]; db += bonuses[3]
    role_b = ROLE_BONUSES[e.role]
    hb *= role_b[0]; db *= role_b[2]
    return (eb, sb, hb, db)
