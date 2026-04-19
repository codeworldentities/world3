"""Survival — burnout, coffee consumption, learning, aging."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, ResourceType, SignalType, Role
from config import (
    BIOME_PROPS, BUG_ENERGY_MULT, CONFLICT_ENERGY_DRAIN,
    LEAD_ENERGY_BONUS,
    RETIREMENT_AGE_START, RETIREMENT_AGE_PEAK,
    RETIREMENT_BASE_CHANCE, BUG_MAX_AGE_START,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity


def update_energy(world: World, e: Entity):
    """Energy cost (burnout) and regeneration."""
    biome = world.get_biome(e.x, e.y)
    bp = BIOME_PROPS[biome]

    tech_eb, _, _, _ = world._get_settlement_bonuses(e)
    _, _, craft_energy = world._get_craft_bonuses(e)

    cost = (0.0004 + 0.00015 * e.speed) * bp[1]
    if e.is_bug_scanner or e.is_predator:
        cost *= BUG_ENERGY_MULT
    cost *= max(0.5, 1.0 - tech_eb)
    cost *= max(0.7, 1.0 - craft_energy)

    k_effects = world._get_knowledge_effects(e)
    if "energy_cost_mult" in k_effects:
        cost *= k_effects["energy_cost_mult"]

    # Leader bonus (team lead reduces burnout)
    if e.settlement_id is not None:
        sett = world.settlements.get(e.settlement_id)
        if sett and sett.leader_id is not None and sett.leader_id != e.id:
            cost *= max(0.85, 1.0 - LEAD_ENERGY_BONUS)

    e.energy -= cost

    # merge conflict drains energy
    if e.group_id is not None:
        for w in world.wars:
            if w.is_active and (w.group_a == e.group_id or w.group_b == e.group_id):
                e.energy -= CONFLICT_ENERGY_DRAIN
                break

    # age burnout (old coder) — stronger than before, starts earlier.
    if e.age > 2500:
        max_age_bonus = k_effects.get("max_age_bonus", 0)
        age_over = e.age - 2500
        extra_den = 900000 + max(0, max_age_bonus) * 200
        age_burn = 0.00012 + (age_over / max(1, extra_den))
        e.energy -= min(0.004, age_burn)
    e.energy += 0.0003 * e.resilience

    if "energy_regen" in k_effects:
        e.energy += k_effects["energy_regen"]

    # Natural lifecycle turnover: eventually retire old workers and expire old
    # bugs so the population keeps changing instead of becoming static.
    if e.entity_type == EntityType.BUG and e.age > BUG_MAX_AGE_START:
        age_ratio = min(1.0, (e.age - BUG_MAX_AGE_START) / 1500)
        death_chance = 0.0008 + age_ratio * 0.012
        if random.random() < death_chance:
            e.alive = False
            e.energy = 0
            return
    elif e.entity_type != EntityType.BUG and e.age > RETIREMENT_AGE_START:
        span = max(1, RETIREMENT_AGE_PEAK - RETIREMENT_AGE_START)
        age_ratio = min(1.0, (e.age - RETIREMENT_AGE_START) / span)
        retirement_chance = RETIREMENT_BASE_CHANCE + age_ratio * 0.022
        if e.energy < 0.3:
            retirement_chance *= 1.6
        if random.random() < min(0.06, retirement_chance):
            e.alive = False
            e.energy = 0
            return

    if e.energy <= 0.01:
        e.alive = False
        e.energy = 0


def eat_resources(world: World, e: Entity):
    """Developer learns/reads resources (docs, libs, coffee)."""
    food_pref = 0.5
    if e.group_id is not None and e.group_id in world.group_cultures:
        food_pref = world.group_cultures[e.group_id].food_pref

    best_res = None
    best_score = float("inf")
    for r in world.resources:
        if not r.alive:
            continue
        d = math.hypot(e.x - r.x, e.y - r.y)
        if d < 15:
            # coffee — energy restoration
            if r.resource_type == ResourceType.COFFEE:
                e.energy = min(1.0, e.energy + 0.04)
                r.energy -= 0.02
                e.flash = 0.4
                continue
            # boilerplate and framework — to inventory
            if r.resource_type in (ResourceType.BOILERPLATE, ResourceType.FRAMEWORK):
                key = r.resource_type.name
                cur = e.inventory.get(key, 0)
                if cur < 10:
                    e.inventory[key] = cur + 1
                    r.energy -= 0.05
                    if r.energy <= 0.01:
                        r.energy = 0
                    e.flash = 0.3
                continue

            pref_bonus = 0
            if r.resource_type == ResourceType.LIBRARY and food_pref > 0.6:
                pref_bonus = -5
            elif r.resource_type == ResourceType.DOCUMENTATION and food_pref < 0.4:
                pref_bonus = -5
            score = d + pref_bonus
            if score < best_score:
                best_score = score
                best_res = r

    if best_res:
        eat = min(best_res.energy, 0.08)
        if best_res.resource_type == ResourceType.LIBRARY:
            eat *= 1.5  # library gives more knowledge
        k_eff = world._get_knowledge_effects(e)
        if "resource_gather_mult" in k_eff:
            eat *= k_eff["resource_gather_mult"]
        if "code_speed_mult" in k_eff:
            eat *= k_eff["code_speed_mult"]
        e.energy = min(1.0, e.energy + eat)
        best_res.energy -= eat
        e.flash = 0.5
        world.spawn_particles(best_res.x, best_res.y,
                              best_res.color,
                              count=3, speed=1.0, size=1.5)
        if random.random() < 0.04 and e.sociability > 0.4:
            world.emit_signal(best_res.x, best_res.y, SignalType.COFFEE_FOUND,
                              sender_id=e.id, group_id=e.group_id, max_r=80)
