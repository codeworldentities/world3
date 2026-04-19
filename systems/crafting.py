"""Tool Crafting — tests, CI/CD Pipeline, Linter."""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from core.enums import CraftableType
from core.models import TYPE_COLORS
from config import CRAFT_RECIPES, CRAFT_BONUSES

if TYPE_CHECKING:
    from core.world import World


def process_crafting(world: World):
    """Entities craft tools (Unit Test, CI Pipeline, Linter)."""
    for e in world.entities:
        if not e.alive or e.age < 300:
            continue
        if len(e.crafted) >= 3:
            continue
        for ctype, recipe in CRAFT_RECIPES.items():
            if ctype in e.crafted:
                continue
            can_craft = True
            for rtype, needed in recipe.items():
                if e.inventory.get(rtype.name, 0) < needed:
                    can_craft = False
                    break
            if can_craft and random.random() < 0.1:
                for rtype, needed in recipe.items():
                    e.inventory[rtype.name] = e.inventory.get(rtype.name, 0) - needed
                e.crafted.append(ctype)
                e.flash = 1.0
                world.spawn_particles(e.x, e.y, TYPE_COLORS[e.entity_type],
                                      count=8, speed=2.0)
                world.log_event(f"🔨 #{e.id} Created: {ctype.value}")
                break


def get_craft_bonuses(e) -> tuple:
    """(defense, bug_detect, energy_save)"""
    d_total = h_total = e_total = 0.0
    for ct in e.crafted:
        bonuses = CRAFT_BONUSES.get(ct, (0, 0, 0))
        d_total += bonuses[0]
        h_total += bonuses[1]
        e_total += bonuses[2]
    return (d_total, h_total, e_total)
