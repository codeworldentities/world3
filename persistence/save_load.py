"""Save/Load — code world state save and restoration."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from core.enums import (
    EntityType, ResourceType, BiomeType, Gender, Instinct,
    Role, TechType, DiplomacyState, CraftableType, KnowledgeType, CodeLanguage,
)
from core.models import (
    Entity, Resource, Memory, Culture, InstinctState,
    Settlement, TradeRoute, War, Knowledge, CodeSnippet,
)

log = logging.getLogger("persistence.save_load")

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")


def save_world(world, filepath: Optional[str] = None) -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)

    if filepath is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(SAVE_DIR, f"world_{timestamp}.json")

    data = {
        "version": 3,
        "timestamp": datetime.now().isoformat(),
        "tick": world.tick,
        "era": world.era,
        "next_id": world.next_id,
        "next_group_id": world.next_group_id,
        "stats": {
            "total_born": world.total_born,
            "total_died": world.total_died,
            "total_hunts": world.total_bug_reports,
            "total_interactions": world.total_interactions,
            "total_signals": world.total_signals,
            "total_matings": world.total_matings,
            "total_code_generated": world.total_code_generated,
            "total_web_reports": getattr(world, "total_web_reports", 0),
            "total_portal_trips": getattr(world, "total_portal_trips", 0),
        },
        "biome_map": [[b.value for b in row] for row in world.biome_map],
        "entities": [_entity_to_dict(e) for e in world.entities],
        "resources": [_resource_to_dict(r) for r in world.resources],
        "groups": {str(k): v for k, v in world.groups.items()},
        "group_cultures": {str(k): _culture_to_dict(v)
                           for k, v in world.group_cultures.items()},
        "family_tree": {str(k): _family_to_dict(v)
                        for k, v in world.family_tree.items()},
        "settlements": {str(k): _settlement_to_dict(s)
                        for k, s in world.settlements.items()},
        "next_settlement_id": world.next_settlement_id,
        "active_project_id": world._active_project_id,
        "total_techs_discovered": world.total_techs_discovered,
        "total_settlements": world.total_settlements,
        "trade_routes": [_trade_route_to_dict(tr) for tr in world.trade_routes if tr.active],
        "wars": [_war_to_dict(w) for w in world.wars],
        "next_war_id": world.next_war_id,
        "total_wars": world.total_wars,
        "total_trades": world.total_trades,
        "events": world.events[-20:],
        "knowledge_db": {str(k): _knowledge_to_dict(kn)
                         for k, kn in world.knowledge_db.items()},
        "group_knowledge": {str(gid): [kt.name for kt in kts]
                            for gid, kts in world.group_knowledge.items()},
        "next_knowledge_id": world.next_knowledge_id,
        "total_knowledge_discovered": world.total_knowledge_discovered,
        "code_snippets": {str(k): _snippet_to_dict(s)
                          for k, s in world.code_snippets.items()},
        "next_snippet_id": world.next_snippet_id,
        "pop_history": {
            "developer": list(world.pop_developer),
            "bug": list(world.pop_bug),
            "refactorer": list(world.pop_refactorer),
            "copilot": list(world.pop_copilot),
            "senior": list(world.pop_senior),
            "intern": list(world.pop_intern),
            "web_scout": list(getattr(world, "pop_web_scout", [])),
            "total": list(world.pop_total),
            "energy_avg": list(world.energy_avg),
        },
        # Phase 8: team memory
        "team_memory": getattr(world, '_team_memory', []),
        "web_portals": getattr(world, "web_portals", []),
        "open_source_growth": getattr(world, "open_source_growth", 0.0),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_world(world, filepath: str) -> bool:
    if not os.path.exists(filepath):
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    world.tick = data["tick"]
    world.era = data["era"]
    world.next_id = data["next_id"]
    world.next_group_id = data["next_group_id"]

    stats = data["stats"]
    world.total_born = stats["total_born"]
    world.total_died = stats["total_died"]
    world.total_bug_reports = stats.get("total_hunts", 0)
    world.total_interactions = stats["total_interactions"]
    world.total_signals = stats["total_signals"]
    world.total_matings = stats["total_matings"]
    world.total_code_generated = stats.get("total_code_generated", 0)
    world.total_web_reports = stats.get("total_web_reports", 0)
    world.total_portal_trips = stats.get("total_portal_trips", 0)

    # biomes
    biome_lookup = {b.value: b for b in BiomeType}
    world.biome_map = [[biome_lookup[cell] for cell in row]
                       for row in data["biome_map"]]

    # Entities
    world.entities = [_dict_to_entity(d) for d in data["entities"]]

    # Resources
    world.resources = [_dict_to_resource(d) for d in data["resources"]]

    # Groups
    world.groups = {int(k): v for k, v in data["groups"].items()}
    world.group_cultures = {int(k): _dict_to_culture(v)
                            for k, v in data["group_cultures"].items()}

    # Family tree
    world.family_tree = {}
    for k, v in data["family_tree"].items():
        world.family_tree[int(k)] = _dict_to_family(v)

    # Events
    world.events = data.get("events", [])

    # population history
    pop = data.get("pop_history", {})
    for name in ("developer", "bug", "refactorer", "copilot", "senior", "intern", "web_scout", "total"):
        deq = getattr(world, f"pop_{name}", None)
        if deq is not None:
            deq.clear()
            for v in pop.get(name, []):
                deq.append(v)
    world.energy_avg.clear()
    for v in pop.get("energy_avg", []):
        world.energy_avg.append(v)

    # projects
    world.settlements = {}
    for k, v in data.get("settlements", {}).items():
        world.settlements[int(k)] = _dict_to_settlement(v)
    world.next_settlement_id = data.get("next_settlement_id", 1)
    world.total_techs_discovered = data.get("total_techs_discovered", 0)
    world.total_settlements = data.get("total_settlements", 0)

    # Restore active project pointer; drop any stale/orphan settlements
    # (completed projects from older save formats that never got cleaned
    # up when `_complete_project` forgot to delete them).
    active_id = data.get("active_project_id")
    if active_id is not None and active_id in world.settlements:
        world._active_project_id = active_id
        world._active_project = world.settlements[active_id]
        # Drop everything else — past projects should live only in
        # completed_projects history, not in the live settlements map.
        for sid in list(world.settlements.keys()):
            if sid != active_id:
                world.settlements.pop(sid, None)
    else:
        world._active_project_id = None
        world._active_project = None
        # No known active project — wipe stale residue from old saves.
        world.settlements.clear()

    # Clear dangling settlement_id references on entities.
    live_sids = set(world.settlements.keys())
    for e in world.entities:
        if e.settlement_id is not None and e.settlement_id not in live_sids:
            e.settlement_id = None

    # social
    world.trade_routes = [_dict_to_trade_route(tr) for tr in data.get("trade_routes", [])]
    world.wars = [_dict_to_war(w) for w in data.get("wars", [])]
    world.next_war_id = data.get("next_war_id", 0)
    world.total_wars = data.get("total_wars", 0)
    world.total_trades = data.get("total_trades", 0)

    # clear runtime state
    world.signals = []
    world.particles = []
    world._pending_bug_reports = []
    world._pending_matings = []
    world._pending_memories = []
    world._pending_discoveries = []
    world._pending_code = []

    # Knowledge
    world.knowledge_db = {}
    for k, v in data.get("knowledge_db", {}).items():
        world.knowledge_db[int(k)] = _dict_to_knowledge(v)
    world.group_knowledge = {}
    for gid, kts in data.get("group_knowledge", {}).items():
        world.group_knowledge[int(gid)] = [
            KnowledgeType[name] for name in kts
            if name in KnowledgeType.__members__
        ]
    world.next_knowledge_id = data.get("next_knowledge_id", 0)
    world.total_knowledge_discovered = data.get("total_knowledge_discovered", 0)

    # code snippets
    world.code_snippets = {}
    for k, v in data.get("code_snippets", {}).items():
        world.code_snippets[int(k)] = _dict_to_snippet(v)
    world.next_snippet_id = data.get("next_snippet_id", 0)

    # Phase 8: team memory
    world._team_memory = data.get("team_memory", [])
    world.web_portals = data.get("web_portals", [])
    world.open_source_growth = data.get("open_source_growth", 0.0)

    # Rehydrate settlement codebase: ID list → CodeSnippet objects
    for sett in world.settlements.values():
        rehydrated = []
        for ref in sett.codebase:
            if isinstance(ref, int):
                snip = world.code_snippets.get(ref)
                if snip is not None:
                    rehydrated.append(snip)
            elif hasattr(ref, "id"):
                rehydrated.append(ref)
        sett.codebase = rehydrated

    return True


def get_latest_save() -> Optional[str]:
    if not os.path.exists(SAVE_DIR):
        return None
    saves = [f for f in os.listdir(SAVE_DIR)
             if f.endswith(".json") and f != "autosave.json"]
    if not saves:
        return None
    saves.sort(reverse=True)
    return os.path.join(SAVE_DIR, saves[0])


def get_autosave_path() -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return os.path.join(SAVE_DIR, "autosave.json")


def list_saves() -> list[dict]:
    if not os.path.exists(SAVE_DIR):
        return []
    result = []
    for f in sorted(os.listdir(SAVE_DIR), reverse=True):
        if not f.endswith(".json"):
            continue
        fpath = os.path.join(SAVE_DIR, f)
        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            result.append({
                "file": f,
                "path": fpath,
                "tick": data.get("tick", 0),
                "era": data.get("era", 0),
                "entities": len(data.get("entities", [])),
                "timestamp": data.get("timestamp", ""),
            })
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Skipping unreadable save %s: %s", f, exc)
    return result


# ================== Serialization ==================

def _entity_to_dict(e: Entity) -> dict:
    return {
        "id": e.id,
        "x": round(e.x, 2),
        "y": round(e.y, 2),
        "entity_type": e.entity_type.name,
        "alive": e.alive,
        "energy": round(e.energy, 4),
        "gender": e.gender.name,
        "age": e.age,
        "generation": e.generation,
        "aggression": round(e.aggression, 4),
        "curiosity": round(e.curiosity, 4),
        "sociability": round(e.sociability, 4),
        "resilience": round(e.resilience, 4),
        "nocturnal": round(e.nocturnal, 4),
        "dx": round(e.dx, 4),
        "dy": round(e.dy, 4),
        "speed": round(e.speed, 4),
        "group_id": e.group_id,
        "home_x": round(e.home_x, 2) if e.home_x is not None else None,
        "home_y": round(e.home_y, 2) if e.home_y is not None else None,
        "mate_cooldown": e.mate_cooldown,
        "parent_a": e.parent_a,
        "parent_b": e.parent_b,
        "relationships": {str(k): round(v, 3) for k, v in e.relationships.items()},
        "memories": [
            {"tick": m.tick, "event": m.event,
             "other_id": m.other_id, "value": round(m.value, 3)}
            for m in e.memories
        ],
        "instincts": {
            "weights": {k.name: round(v, 4) for k, v in e.instincts.weights.items()},
            "active": e.instincts.active.name if e.instincts.active else None,
            "cooldowns": {k.name: v for k, v in e.instincts.cooldowns.items()},
        },
        "role": e.role.name,
        "settlement_id": e.settlement_id,
        "brain_level": e.brain_level,
        "last_thought": e.last_thought,
        "last_dialogue": e.last_dialogue,
        "thought_tick": e.thought_tick,
        "llm_mood": e.llm_mood,
        "llm_action": e.llm_action,
        "inventory": e.inventory,
        "crafted": [ct.name for ct in e.crafted] if e.crafted else [],
        "known_knowledge": [kt.name for kt in e.known_knowledge] if e.known_knowledge else [],
        # code world fields
        "languages_known": [l.name for l in e.languages_known] if e.languages_known else [],
        "code_output": e.code_output,
        "bugs_fixed": e.bugs_fixed,
        "bugs_introduced": e.bugs_introduced,
        "code_quality": round(e.code_quality, 4),
        "commits": e.commits,
        "reviews_done": e.reviews_done,
        "pair_partner_id": e.pair_partner_id,
        "dev_name": e.dev_name,
        "found_bug_in": e.found_bug_in,
        "reported_to_dev": e.reported_to_dev,
        "soul_id": e.soul_id,
        # Phase 8: advanced lifecycle fields
        "reputation": round(getattr(e, 'reputation', 0.5), 4),
        "burnout": getattr(e, 'burnout', False),
        "burnout_ticks": getattr(e, 'burnout_ticks', 0),
        "personality_xp": getattr(e, 'personality_xp', {}),
        "language_last_used": getattr(e, 'language_last_used', {}),
        "language_xp": e.language_xp,
        "web_mission_until": int(getattr(e, 'web_mission_until', 0)),
        "web_source": getattr(e, 'web_source', ''),
        "web_last_report_tick": int(getattr(e, 'web_last_report_tick', 0)),
        "web_reports": int(getattr(e, 'web_reports', 0)),
    }


def _dict_to_entity(d: dict) -> Entity:
    etype = EntityType[d["entity_type"]]
    gender = Gender[d["gender"]]

    weights = {Instinct[k]: v for k, v in d["instincts"]["weights"].items()}
    active = Instinct[d["instincts"]["active"]] if d["instincts"].get("active") else None
    cooldowns = {Instinct[k]: v for k, v in d["instincts"].get("cooldowns", {}).items()}

    e = Entity(
        id=d["id"],
        x=d["x"],
        y=d["y"],
        entity_type=etype,
        alive=d.get("alive", True),
        energy=d["energy"],
        gender=gender,
        age=d["age"],
        generation=d["generation"],
        aggression=d["aggression"],
        curiosity=d["curiosity"],
        sociability=d["sociability"],
        resilience=d["resilience"],
        nocturnal=d.get("nocturnal", 0),
        dx=d["dx"],
        dy=d["dy"],
        speed=d["speed"],
        group_id=d["group_id"],
        home_x=d.get("home_x"),
        home_y=d.get("home_y"),
        mate_cooldown=d["mate_cooldown"],
        parent_a=d.get("parent_a"),
        parent_b=d.get("parent_b"),
        instincts=InstinctState(weights=weights, active=active, cooldowns=cooldowns),
    )

    e.relationships = {int(k): v for k, v in d.get("relationships", {}).items()}
    e.memories = [
        Memory(tick=m["tick"], event=m["event"],
               other_id=m.get("other_id"), value=m.get("value", 0))
        for m in d.get("memories", [])
    ]
    e.role = Role[d["role"]] if d.get("role") else Role.NONE
    e.settlement_id = d.get("settlement_id")
    e.brain_level = d.get("brain_level", 0)
    e.last_thought = d.get("last_thought", "")
    e.last_dialogue = d.get("last_dialogue", "")
    e.thought_tick = d.get("thought_tick", 0)
    e.llm_mood = d.get("llm_mood", "")
    e.llm_action = d.get("llm_action", "")
    e.inventory = d.get("inventory", {})
    e.crafted = [CraftableType[name] for name in d.get("crafted", [])
                 if name in CraftableType.__members__]
    e.known_knowledge = [KnowledgeType[name] for name in d.get("known_knowledge", [])
                         if name in KnowledgeType.__members__]

    # code world fields
    e.languages_known = [CodeLanguage[name] for name in d.get("languages_known", [])
                         if name in CodeLanguage.__members__]
    e.code_output = d.get("code_output", [])
    e.bugs_fixed = d.get("bugs_fixed", 0)
    e.bugs_introduced = d.get("bugs_introduced", 0)
    e.code_quality = d.get("code_quality", 0.5)
    e.commits = d.get("commits", 0)
    e.reviews_done = d.get("reviews_done", 0)
    e.pair_partner_id = d.get("pair_partner_id")
    e.dev_name = d.get("dev_name", "")
    e.found_bug_in = d.get("found_bug_in")
    e.reported_to_dev = d.get("reported_to_dev")
    e.soul_id = d.get("soul_id")

    # Phase 8: advanced lifecycle fields
    e.reputation = d.get("reputation", 0.5)
    e.burnout = d.get("burnout", False)
    e.burnout_ticks = d.get("burnout_ticks", 0)
    e.personality_xp = d.get("personality_xp", {})
    e.language_last_used = d.get("language_last_used", {})
    e.language_xp = d.get("language_xp", {})
    e.web_mission_until = d.get("web_mission_until", 0)
    e.web_source = d.get("web_source", "")
    e.web_last_report_tick = d.get("web_last_report_tick", 0)
    e.web_reports = d.get("web_reports", 0)

    # Backward safety: if an old save marks entity dead but left positive
    # energy, clamp to zero so cleanup logic stays consistent.
    if not e.alive and e.energy > 0:
        e.energy = 0

    return e


def _snippet_to_dict(s: CodeSnippet) -> dict:
    return {
        "id": s.id,
        "author_id": s.author_id,
        "language": s.language.name,
        "content": s.content[:500],  # limited size for storage
        "description": s.description,
        "quality": round(s.quality, 4),
        "tick_created": s.tick_created,
        "reviewed": s.reviewed,
        "reviewer_id": s.reviewer_id,
        "has_bugs": s.has_bugs,
        "lines": s.lines,
        "filename": s.filename,
    }


def _dict_to_snippet(d: dict) -> CodeSnippet:
    return CodeSnippet(
        id=d["id"],
        author_id=d["author_id"],
        language=CodeLanguage[d["language"]],
        content=d.get("content", ""),
        description=d.get("description", ""),
        quality=d.get("quality", 0.5),
        tick_created=d.get("tick_created", 0),
        reviewed=d.get("reviewed", False),
        reviewer_id=d.get("reviewer_id"),
        has_bugs=d.get("has_bugs", False),
        lines=d.get("lines", 0),
        filename=d.get("filename", ""),
    )


def _knowledge_to_dict(k: Knowledge) -> dict:
    return {
        "id": k.id,
        "knowledge_type": k.knowledge_type.name,
        "name": k.name,
        "description": k.description,
        "discovered_at_tick": k.discovered_at_tick,
        "discovered_by_entity": k.discovered_by_entity,
        "discovered_by_group": k.discovered_by_group,
    }


def _dict_to_knowledge(d: dict) -> Knowledge:
    return Knowledge(
        id=d["id"],
        knowledge_type=KnowledgeType[d["knowledge_type"]],
        name=d["name"],
        description=d.get("description", ""),
        discovered_at_tick=d.get("discovered_at_tick", 0),
        discovered_by_entity=d.get("discovered_by_entity"),
        discovered_by_group=d.get("discovered_by_group"),
    )


def _resource_to_dict(r: Resource) -> dict:
    return {
        "x": round(r.x, 2),
        "y": round(r.y, 2),
        "resource_type": r.resource_type.name,
        "energy": round(r.energy, 4),
        "pulse": round(r.pulse, 2),
    }


def _dict_to_resource(d: dict) -> Resource:
    return Resource(
        x=d["x"],
        y=d["y"],
        resource_type=ResourceType[d["resource_type"]],
        energy=d["energy"],
        pulse=d.get("pulse", 0),
    )


def _culture_to_dict(c: Culture) -> dict:
    return {
        "food_pref": round(c.food_pref, 3),
        "aggression_norm": round(c.aggression_norm, 3),
        "nocturnal": round(c.nocturnal, 3),
        "cooperation": round(c.cooperation, 3),
        "wander_range": round(c.wander_range, 3),
    }


def _dict_to_culture(d: dict) -> Culture:
    return Culture(
        food_pref=d["food_pref"],
        aggression_norm=d["aggression_norm"],
        nocturnal=d.get("nocturnal", 0),
        cooperation=d.get("cooperation", 0.5),
        wander_range=d.get("wander_range", 0.5),
    )


def _family_to_dict(f: dict) -> dict:
    return {
        "type": f["type"].name if isinstance(f["type"], EntityType) else f["type"],
        "gen": f["gen"],
        "gender": f["gender"].name if isinstance(f["gender"], Gender) else f["gender"],
        "parent_a": f.get("parent_a"),
        "parent_b": f.get("parent_b"),
        "born": f.get("born"),
        "died": f.get("died"),
    }


def _dict_to_family(d: dict) -> dict:
    return {
        "type": EntityType[d["type"]] if isinstance(d["type"], str) else d["type"],
        "gen": d["gen"],
        "gender": Gender[d["gender"]] if isinstance(d["gender"], str) else d["gender"],
        "parent_a": d.get("parent_a"),
        "parent_b": d.get("parent_b"),
        "born": d.get("born"),
        "died": d.get("died"),
    }


def _settlement_to_dict(s: Settlement) -> dict:
    return {
        "id": s.id,
        "group_id": s.group_id,
        "x": round(s.x, 2),
        "y": round(s.y, 2),
        "radius": s.radius,
        "population": s.population,
        "founded_tick": s.founded_tick,
        "techs": [t.name for t in s.techs],
        "stored_resources": round(s.stored_resources, 3),
        "buildings": s.buildings,
        "leader_id": s.leader_id,
        "diplomacy": {str(k): v.name for k, v in s.diplomacy.items()},
        "peace_cooldowns": {str(k): v for k, v in s.peace_cooldowns.items()},
        "project_name": s.project_name,
        "tech_stack": [l.name for l in s.tech_stack] if s.tech_stack else [],
        "total_commits": s.total_commits,
        "bug_count": s.bug_count,
        # codebase at runtime is list[CodeSnippet]; persist only IDs (capped
        # for size). The snippets themselves are stored under world.code_snippets.
        "codebase": [getattr(c, "id", c) for c in s.codebase[:200]],
    }


def _dict_to_settlement(d: dict) -> Settlement:
    diplo_lookup = {ds.name: ds for ds in DiplomacyState}
    s = Settlement(
        id=d["id"],
        group_id=d["group_id"],
        x=d["x"],
        y=d["y"],
        radius=d.get("radius", 180),
        population=d["population"],
        founded_tick=d["founded_tick"],
        techs=[TechType[t] for t in d.get("techs", [])],
        stored_resources=d.get("stored_resources", 0),
        buildings=d.get("buildings", 0),
        leader_id=d.get("leader_id"),
        diplomacy={int(k): diplo_lookup.get(v, DiplomacyState.NEUTRAL)
                   for k, v in d.get("diplomacy", {}).items()},
        peace_cooldowns={int(k): v for k, v in d.get("peace_cooldowns", {}).items()},
    )
    s.project_name = d.get("project_name", "")
    s.tech_stack = [CodeLanguage[n] for n in d.get("tech_stack", [])
                    if n in CodeLanguage.__members__]
    s.total_commits = d.get("total_commits", 0)
    s.bug_count = d.get("bug_count", 0)
    # Keep as IDs here; rehydration to CodeSnippet objects happens in load_world
    # after code_snippets are loaded.
    s.codebase = list(d.get("codebase", []))
    return s


def _trade_route_to_dict(tr: TradeRoute) -> dict:
    return {
        "settlement_a": tr.settlement_a,
        "settlement_b": tr.settlement_b,
        "established_tick": tr.established_tick,
        "strength": round(tr.strength, 3),
        "total_traded": round(tr.total_traded, 3),
        "active": tr.active,
    }


def _dict_to_trade_route(d: dict) -> TradeRoute:
    return TradeRoute(
        settlement_a=d["settlement_a"],
        settlement_b=d["settlement_b"],
        established_tick=d["established_tick"],
        strength=d.get("strength", 1.0),
        total_traded=d.get("total_traded", 0),
        active=d.get("active", True),
    )


def _war_to_dict(w: War) -> dict:
    return {
        "id": w.id,
        "group_a": w.group_a,
        "group_b": w.group_b,
        "started_tick": w.started_tick,
        "duration": w.duration,
        "casualties_a": w.casualties_a,
        "casualties_b": w.casualties_b,
        "resolved": w.resolved,
        "winner": w.winner,
    }


def _dict_to_war(d: dict) -> War:
    return War(
        id=d["id"],
        group_a=d["group_a"],
        group_b=d["group_b"],
        started_tick=d["started_tick"],
        duration=d.get("duration", 0),
        casualties_a=d.get("casualties_a", 0),
        casualties_b=d.get("casualties_b", 0),
        resolved=d.get("resolved", False),
        winner=d.get("winner"),
    )
