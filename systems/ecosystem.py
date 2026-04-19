"""Ecosystem balance — Developer/Bug ratio, Resources."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, ResourceType, BiomeType, CodeLanguage
from config import (
    MAX_BUG_RATIO, BUG_OVERPOP_DRAIN,
    BIOME_PROPS, BIOME_CELL, BIOME_COLS, BIOME_ROWS,
    MAX_RESOURCES, RESOURCE_ENERGY, RESOURCE_SPAWN_RATE,
    WORLD_WIDTH, WORLD_HEIGHT, MIN_ENTITIES,
)

if TYPE_CHECKING:
    from core.world import World


def balance_ecosystem(world: World):
    """Protect species min/max ratios."""
    total = len(world.entities)
    if total == 0:
        return

    counts = {t: 0 for t in EntityType}
    for e in world.entities:
        counts[e.entity_type] += 1

    dev_count = counts[EntityType.DEVELOPER] + counts[EntityType.INTERN]
    bug_count = counts[EntityType.BUG]
    bug_ratio = bug_count / total if total > 0 else 0

    # developers minimum
    if dev_count < max(20, total * 0.3):
        for _ in range(random.randint(1, 3)):
            e = world.spawn_entity(entity_type=EntityType.DEVELOPER)
            if e and not e.languages_known:
                e.languages_known.append(random.choice(list(CodeLanguage)))

    # bugs minimum
    if bug_count < max(5, total * 0.08):
        if random.random() < 0.3:
            world.spawn_entity(entity_type=EntityType.BUG)

    # bugs overpopulation
    if bug_ratio > MAX_BUG_RATIO:
        for e in world.entities:
            if e.entity_type == EntityType.BUG and e.alive:
                e.energy -= BUG_OVERPOP_DRAIN

    # refactorers minimum
    if counts[EntityType.REFACTORER] < max(2, total * 0.02):
        if random.random() < 0.1:
            world.spawn_entity(entity_type=EntityType.REFACTORER)

    # Teachers — keep a few around so language transfer / XP always active.
    if counts[EntityType.TEACHER] < 3:
        if random.random() < 0.15:
            world.spawn_entity(entity_type=EntityType.TEACHER)

    # Judges — keep a small cohort so reward/penalty economy runs.
    if counts[EntityType.JUDGE] < 2:
        if random.random() < 0.15:
            world.spawn_entity(entity_type=EntityType.JUDGE)


def emergency_respawn(world: World):
    """Emergency respawn if population is too low."""
    if len(world.entities) < MIN_ENTITIES:
        for _ in range(15):
            e = world.spawn_entity(entity_type=EntityType.DEVELOPER)
            if e and not e.languages_known:
                e.languages_known.append(random.choice(list(CodeLanguage)))


def spawn_resources(world: World):
    """Spawn resources based on biome."""
    if len(world.resources) >= MAX_RESOURCES:
        return
    if random.random() > RESOURCE_SPAWN_RATE:
        return

    x = random.uniform(30, WORLD_WIDTH - 30)
    y = random.uniform(30, WORLD_HEIGHT - 30)
    biome = world.get_biome(x, y)
    bp = BIOME_PROPS[biome]

    if random.random() > bp[0]:
        return

    _spawn_resource_at(world, x, y, biome)


def spawn_resource_at(world: World, x: float, y: float):
    """Spawn resource at chosen coordinates."""
    if len(world.resources) >= MAX_RESOURCES:
        return
    biome = world.get_biome(x, y)
    _spawn_resource_at(world, x, y, biome)


def _spawn_resource_at(world: World, x: float, y: float, biome: BiomeType):
    """Internal resource spawn logic — code world resources."""
    from core.models import Resource

    bp = BIOME_PROPS[biome]
    # bp[3]=doc_ratio, bp[4]=lib_ratio, bp[5]=boilerplate_ratio, bp[6]=framework_ratio
    doc_r, lib_r, boiler_r, frame_r = bp[3], bp[4], bp[5], bp[6]
    total_r = doc_r + lib_r + boiler_r + frame_r
    if total_r <= 0:
        return

    roll = random.random() * total_r
    cumulative = 0.0
    rtype = ResourceType.DOCUMENTATION
    for rt, ratio in [(ResourceType.DOCUMENTATION, doc_r),
                      (ResourceType.LIBRARY, lib_r),
                      (ResourceType.BOILERPLATE, boiler_r),
                      (ResourceType.FRAMEWORK, frame_r)]:
        cumulative += ratio
        if roll < cumulative:
            rtype = rt
            break
    else:
        rtype = ResourceType.COFFEE

    energy_mult = {
        ResourceType.DOCUMENTATION: 1.0,
        ResourceType.LIBRARY: 2.0,
        ResourceType.COFFEE: 0.8,
        ResourceType.BOILERPLATE: 0.3,
        ResourceType.FRAMEWORK: 0.2,
    }
    energy = RESOURCE_ENERGY * energy_mult.get(rtype, 1.0)

    world.resources.append(Resource(
        x=x, y=y, resource_type=rtype, energy=energy,
        pulse=random.uniform(0, 6.28),
    ))
