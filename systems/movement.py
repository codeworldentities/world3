"""Movement — instinct-aware navigation in code domains."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import (
    EntityType, ResourceType, BiomeType, SignalType, Instinct, Role,
)
from config import (
    BIOME_PROPS, VISION_RADIUS, TERRITORY_RADIUS,
    WORLD_WIDTH, WORLD_HEIGHT,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity


def move_entity(world: World, e: Entity, all_entities: list,
                biome: BiomeType, instinct: Instinct):
    """Instinct-aware movement in code domains."""
    bp = BIOME_PROPS[biome]

    # LEARN — search for documentation/libraries (and coffee!)
    seek_resource = (not e.is_predator) and e.curiosity > 0.3 and random.random() < 0.06
    if instinct == Instinct.LEARN:
        seek_resource = (not e.is_predator) and random.random() < 0.15

    if seek_resource:
        food_pref = 0.5
        if e.group_id is not None and e.group_id in world.group_cultures:
            food_pref = world.group_cultures[e.group_id].food_pref

        nearest_res = None
        nearest_d = VISION_RADIUS
        for r in world.resources:
            if not r.alive:
                continue
            d = math.hypot(e.x - r.x, e.y - r.y)
            if r.resource_type == ResourceType.LIBRARY and food_pref > 0.6:
                d *= 0.7  # Library preference
            elif r.resource_type == ResourceType.DOCUMENTATION and food_pref < 0.4:
                d *= 0.7  # Documentation preference
            if r.resource_type == ResourceType.COFFEE and e.energy < 0.3:
                d *= 0.5  # Urgently needs coffee
            if d < nearest_d:
                nearest_res = r
                nearest_d = d
        if nearest_res:
            dx = nearest_res.x - e.x
            dy = nearest_res.y - e.y
            d = math.hypot(dx, dy)
            if d > 0:
                e.dx = e.dx * 0.6 + (dx / d) * 0.4
                e.dy = e.dy * 0.6 + (dy / d) * 0.4

    # COLLABORATE — searching for pair partner
    if instinct == Instinct.COLLABORATE and e.can_mate:
        nearest_mate = None
        nearest_md = VISION_RADIUS * 1.3
        for o in all_entities:
            if (o.id != e.id and o.alive and o.entity_type == e.entity_type
                    and o.gender != e.gender and o.can_mate):
                d = math.hypot(e.x - o.x, e.y - o.y)
                if d < nearest_md:
                    nearest_mate = o
                    nearest_md = d
        if nearest_mate:
            dx = nearest_mate.x - e.x
            dy = nearest_mate.y - e.y
            d = math.hypot(dx, dy)
            if d > 0:
                e.dx = e.dx * 0.5 + (dx / d) * 0.5
                e.dy = e.dy * 0.5 + (dy / d) * 0.5

    # CODE — finding a quiet spot to code
    if instinct == Instinct.CODE and e.can_code:
        # Gentle pull toward project area — only if far away
        if e.settlement_id is not None:
            sett = world.settlements.get(e.settlement_id)
            if sett:
                dx = sett.x - e.x
                dy = sett.y - e.y
                d = math.hypot(dx, dy)
                r = getattr(sett, 'radius', 100) * 3
                if d > r:
                    e.dx = e.dx * 0.9 + (dx / d) * 0.08
                    e.dy = e.dy * 0.9 + (dy / d) * 0.08
                elif d < r * 0.5 and d > 5:
                    # too close to center — push outward strongly
                    push = 0.3 * (1.0 - d / (r * 0.5))
                    e.dx -= (dx / d) * push
                    e.dy -= (dy / d) * push

    # LEARN — migrate to new domain
    if instinct == Instinct.LEARN and random.random() < 0.04:
        best_dir_x, best_dir_y = 0.0, 0.0
        for _ in range(5):
            angle = random.uniform(0, 2 * math.pi)
            probe_x = max(0, min(WORLD_WIDTH, e.x + math.cos(angle) * 100))
            probe_y = max(0, min(WORLD_HEIGHT, e.y + math.sin(angle) * 100))
            probe_biome = world.get_biome(probe_x, probe_y)
            q = BIOME_PROPS[probe_biome][0]
            if q > bp[0]:
                best_dir_x += math.cos(angle) * q
                best_dir_y += math.sin(angle) * q
        d = math.hypot(best_dir_x, best_dir_y)
        if d > 0:
            e.dx = e.dx * 0.6 + (best_dir_x / d) * 0.4
            e.dy = e.dy * 0.6 + (best_dir_y / d) * 0.4

    # DEPLOY — toward team center (together for deploy)
    if instinct == Instinct.DEPLOY and e.group_id is not None:
        gm = [o for o in all_entities if o.group_id == e.group_id
              and o.id != e.id and o.alive]
        weak = [m for m in gm if m.energy < 0.3]
        target_list = weak if weak else gm
        if target_list:
            cx = sum(m.x for m in target_list) / len(target_list)
            cy = sum(m.y for m in target_list) / len(target_list)
            dx = cx - e.x
            dy = cy - e.y
            d = math.hypot(dx, dy)
            if d > 80:
                e.dx = e.dx * 0.85 + (dx / d) * 0.15
                e.dy = e.dy * 0.85 + (dy / d) * 0.15

    # Group cohesion — only if far from group
    elif e.sociability > 0.5 and e.group_id is not None:
        gm = [o for o in all_entities if o.group_id == e.group_id
              and o.id != e.id and o.alive]
        if gm:
            cx = sum(m.x for m in gm) / len(gm)
            cy = sum(m.y for m in gm) / len(gm)
            dx = cx - e.x
            dy = cy - e.y
            d = math.hypot(dx, dy)
            if d > 150:
                e.dx = e.dx * 0.92 + (dx / d) * 0.08
                e.dy = e.dy * 0.92 + (dy / d) * 0.08

    # Toward settlements (workspace)
    if e.home_x is not None and e.ticks_at_home > 100 and random.random() < 0.03:
        dx = e.home_x - e.x
        dy = e.home_y - e.y
        d = math.hypot(dx, dy)
        if d > TERRITORY_RADIUS:
            e.dx = e.dx * 0.7 + (dx / d) * 0.3
            e.dy = e.dy * 0.7 + (dy / d) * 0.3

    # Territory repulsion (other project territory)
    for tid, terr in world.territories.items():
        if tid == e.group_id:
            continue
        d = math.hypot(e.x - terr.cx, e.y - terr.cy)
        if d < terr.radius and terr.strength > 0.3:
            dx = e.x - terr.cx
            dy = e.y - terr.cy
            d2 = math.hypot(dx, dy)
            if d2 > 0:
                push = 0.15 * terr.strength
                e.dx += (dx / d2) * push
                e.dy += (dy / d2) * push

    # Signal reaction
    for sig in world.signals:
        if sig.sender_id == e.id:
            continue
        d = math.hypot(e.x - sig.x, e.y - sig.y)
        if d > sig.radius or d < 1:
            continue

        influence = sig.strength * (1.0 - d / sig.radius) * 0.3
        dx = sig.x - e.x
        dy = sig.y - e.y
        nd = math.hypot(dx, dy)
        if nd < 1:
            continue
        ndx, ndy = dx / nd, dy / nd

        if sig.signal_type == SignalType.BUG_ALERT:
            # Bug signal — debuggers head toward bug
            if e.entity_type in (EntityType.SENIOR_DEV, EntityType.AI_COPILOT):
                e.dx += ndx * influence * 0.5
                e.dy += ndy * influence * 0.5

        elif sig.signal_type == SignalType.COFFEE_FOUND:
            if e.energy < 0.5:
                e.dx += ndx * influence
                e.dy += ndy * influence

        elif sig.signal_type == SignalType.HELP_NEEDED:
            if e.group_id == sig.group_id and e.sociability > 0.3:
                e.dx += ndx * influence * 0.6
                e.dy += ndy * influence * 0.6

        elif sig.signal_type == SignalType.PAIR_PROGRAM:
            if e.can_mate and e.entity_type != EntityType.BUG:
                e.dx += ndx * influence * 0.3
                e.dy += ndy * influence * 0.3

        elif sig.signal_type == SignalType.CODE_REVIEW:
            # Reviewers go to code review
            if e.role == Role.REVIEWER:
                e.dx += ndx * influence * 0.5
                e.dy += ndy * influence * 0.5

    # Random wander — chaotic movement
    wander_chance = 0.35 if e.entity_type == EntityType.BUG else 0.20
    if random.random() < wander_chance:
        angle = random.uniform(0, math.pi * 2)
        strength = random.uniform(0.3, 0.8)
        e.dx += math.cos(angle) * strength
        e.dy += math.sin(angle) * strength

    # During meeting phases — loose pull only if very far
    if e.settlement_id is not None:
        sett = world.settlements.get(e.settlement_id)
        if sett and getattr(sett, 'phase', '') in ('architecture', 'review'):
            dx = sett.x - e.x
            dy = sett.y - e.y
            d = math.hypot(dx, dy)
            outer_radius = max(200, (sett.radius if hasattr(sett, 'radius') else 100) * 3.0)
            if d > outer_radius:
                pull = 0.05
                e.dx = e.dx * 0.92 + (dx / d) * pull
                e.dy = e.dy * 0.92 + (dy / d) * pull
            elif d < outer_radius * 0.25 and d > 5:
                # too close to center — push out
                e.dx -= (dx / d) * 0.25
                e.dy -= (dy / d) * 0.25
            else:
                # inside area — wander freely
                angle = random.uniform(0, math.pi * 2)
                e.dx += math.cos(angle) * 1.8
                e.dy += math.sin(angle) * 1.8

    # Entity repulsion — prevent overlapping (sample for perf)
    in_project = e.settlement_id is not None
    repulse_radius = 100 if in_project else 60
    check_list = all_entities if len(all_entities) < 80 else random.sample(all_entities, 60)
    for o in check_list:
        if o.id == e.id or not o.alive:
            continue
        dx2 = e.x - o.x
        dy2 = e.y - o.y
        d_sq = dx2 * dx2 + dy2 * dy2
        if 0 < d_sq < repulse_radius * repulse_radius:
            d = d_sq ** 0.5
            push = (1.0 - d / repulse_radius) * (2.0 if in_project else 1.2)
            e.dx += dx2 / d * push
            e.dy += dy2 / d * push

    # Normalize
    d = math.hypot(e.dx, e.dy)
    if d > 0:
        e.dx /= d
        e.dy /= d

    # Speed
    spd = e.speed * bp[2]
    # Bugs move faster
    if e.entity_type == EntityType.BUG:
        spd *= 1.8
    if world.is_night:
        spd *= (0.7 + 0.6 * e.nocturnal)
    # Minimum speed — do not stop
    spd = max(spd, 0.5)

    e.x = max(5, min(WORLD_WIDTH - 5, e.x + e.dx * spd))
    e.y = max(5, min(WORLD_HEIGHT - 5, e.y + e.dy * spd))

    if e.home_x is not None:
        if math.hypot(e.x - e.home_x, e.y - e.home_y) < TERRITORY_RADIUS:
            e.ticks_at_home += 1
        else:
            e.ticks_at_home = max(0, e.ticks_at_home - 1)
