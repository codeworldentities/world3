"""Knowledge system — programming language and framework discovery."""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from core.enums import KnowledgeType, CodeLanguage
from core.models import Knowledge
from config import (
    KNOWLEDGE_TREE, KNOWLEDGE_EFFECTS,
    KNOWLEDGE_MIN_GROUP_SIZE, KNOWLEDGE_MIN_RESOURCES,
    KNOWLEDGE_LLM_DISCOVERY, KNOWLEDGE_TO_LANG,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity


def get_knowledge_effects(world: World, e) -> dict:
    """Effects based on entity's knowledge."""
    effects = {}
    knowledge_set = set(e.known_knowledge)
    if e.group_id is not None:
        for kt in world.group_knowledge.get(e.group_id, []):
            knowledge_set.add(kt)
    for kt in knowledge_set:
        kt_effects = KNOWLEDGE_EFFECTS.get(kt, {})
        for key, val in kt_effects.items():
            if isinstance(val, bool):
                effects[key] = val
            elif isinstance(val, (int, float)):
                if key in effects:
                    effects[key] = effects[key] * val
                else:
                    effects[key] = val
    return effects


def process_knowledge_discovery(world: World):
    """Programming language and framework discovery."""
    group_members: dict[int, list] = {}
    for e in world.entities:
        if e.alive and e.group_id is not None:
            group_members.setdefault(e.group_id, []).append(e)

    for gid, members in group_members.items():
        if len(members) < KNOWLEDGE_MIN_GROUP_SIZE:
            continue
        total_res = sum(sum(e.inventory.values()) for e in members)
        if total_res < KNOWLEDGE_MIN_RESOURCES:
            continue

        group_k = world.group_knowledge.get(gid, [])

        for k_type, (min_pop, min_age, prereq, base_chance) in KNOWLEDGE_TREE.items():
            if k_type in group_k:
                continue
            if len(members) < min_pop:
                continue
            oldest = max(m.age for m in members)
            if oldest < min_age:
                continue
            if prereq is not None and prereq not in group_k:
                continue

            chance = base_chance
            culture = world.group_cultures.get(gid)
            if culture:
                chance *= (0.5 + culture.cooperation)
            avg_curiosity = sum(m.curiosity for m in members) / len(members)
            chance *= (0.5 + avg_curiosity)

            if random.random() < chance:
                discovery_desc = ""
                discoverer = max(members, key=lambda m: m.curiosity)

                if KNOWLEDGE_LLM_DISCOVERY and world.brain and world.brain.connected:
                    group_info = {
                        "members": [m.entity_type.value for m in members[:5]],
                        "resources": list(set(
                            rtype for m in members
                            for rtype, cnt in m.inventory.items() if cnt > 0
                        )),
                        "known_knowledge": [k.value for k in group_k],
                        "biome": world.get_biome(discoverer.x, discoverer.y).value,
                        "situation": f"team of {len(members)}, tick {world.tick}",
                    }
                    llm_result = world.brain.request_discovery(group_info)
                    if llm_result and llm_result.get("discovered"):
                        discovery_desc = llm_result.get("description", "")

                _register_knowledge(world, k_type, discoverer, gid, discovery_desc)

                # language to CodeLanguage inheritance
                if k_type in KNOWLEDGE_TO_LANG:
                    lang = KNOWLEDGE_TO_LANG[k_type]
                    for m in members:
                        if lang not in m.languages_known:
                            m.languages_known.append(lang)

                break


def _register_knowledge(world: World, k_type: KnowledgeType, discoverer,
                        group_id: int, description: str = ""):
    """Register new knowledge."""
    kid = world.next_knowledge_id
    world.next_knowledge_id += 1
    k = Knowledge(
        id=kid, knowledge_type=k_type, name=k_type.value,
        description=description or k_type.value,
        discovered_at_tick=world.tick,
        discovered_by_entity=discoverer.id,
        discovered_by_group=group_id,
    )
    world.knowledge_db[kid] = k
    world.total_knowledge_discovered += 1

    if group_id not in world.group_knowledge:
        world.group_knowledge[group_id] = []
    world.group_knowledge[group_id].append(k_type)

    for e in world.entities:
        if e.alive and e.group_id == group_id:
            if k_type not in e.known_knowledge:
                e.known_knowledge.append(k_type)

    world.log_event(f"📚 Knowledge: {k_type.value} (team #{group_id}, #{discoverer.id})")
    world.spawn_particles(discoverer.x, discoverer.y, (100, 200, 255),
                          count=15, speed=3.0, size=2.5)

    world._pending_discoveries.append({
        "entity_id": discoverer.id,
        "group_id": group_id,
        "knowledge_type": k_type.value,
        "knowledge_id": kid,
        "tick": world.tick,
    })
