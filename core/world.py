"""World — central coordinator of the code world.

Unifies all subsystems and manages the step() cycle.
"""

from __future__ import annotations

import math
import random
import time
from collections import deque
from typing import Optional

from core.enums import (
    EntityType, ResourceType, BiomeType, SignalType, Gender,
    Instinct, Role, KnowledgeType, DiplomacyState, CodeLanguage,
)
from core.models import (
    Entity, Resource, Particle, Signal, Territory, Culture,
    Settlement, TradeRoute, War, Knowledge, InstinctState, Memory, CodeSnippet,
)
from core.event_bus import EventBus
from config import (
    WORLD_WIDTH, WORLD_HEIGHT,
    INITIAL_ENTITY_COUNT, MAX_ENTITIES, MIN_ENTITIES,
    INITIAL_RESOURCE_COUNT, MAX_RESOURCES,
    RESOURCE_SPAWN_RATE, RESOURCE_ENERGY,
    BIOME_CELL, BIOME_COLS, BIOME_ROWS, BIOME_PROPS,
    DAY_LENGTH, MAX_SIGNALS,
    INTERACTION_RADIUS, VISION_RADIUS, TERRITORY_RADIUS,
    BUG_ENERGY_MULT,
    TECH_BONUSES, ROLE_BONUSES, CRAFT_BONUSES,
    KNOWLEDGE_EFFECTS, KNOWLEDGE_DISCOVERY_INTERVAL,
    SHARE_INTERVAL, LEAD_ELECTION_INTERVAL,
    GRAPH_SYNC_INTERVAL, AUTOSAVE_INTERVAL,
    LLM_ENABLED, LLM_CALLS_PER_STEP, LLM_THINK_INTERVAL,
    LLM_LEAD_INTERVAL, LLM_CONVO_INTERVAL, LLM_CONVO_RADIUS,
    LLM_CONVO_COOLDOWN, LLM_THOUGHT_DISPLAY_TICKS,
    LLM_DIALOGUE_RADIUS, LLM_CONVO_LANGUAGE,
    BRAIN_LEVEL_NONE, BRAIN_LEVEL_BASIC, BRAIN_LEVEL_LEAD, BRAIN_LEVEL_WILD,
    PROJECT_RADIUS,
    CODE_GEN_INTERVAL, CODE_OUTPUT_DIR, KNOWLEDGE_TO_LANG,
    INITIAL_WEB_SCOUT_COUNT,
)

import logging
log = logging.getLogger("world")


class World:
    """Central state and step() cycle of the code world."""

    def __init__(self):
        self.tick = 0

        # Entities and Resources
        self.entities: list[Entity] = []
        self.resources: list[Resource] = []
        self.particles: list[Particle] = []
        self.signals: list[Signal] = []
        self.territories: dict[int, Territory] = {}
        self.next_id = 0

        # Groups
        self.groups: dict[int, list[int]] = {}
        self.group_cultures: dict[int, Culture] = {}
        self.next_group_id = 0

        # Family tree
        self.family_tree: dict[int, dict] = {}

        # Statistics
        self.total_born = 0
        self.total_died = 0
        self.total_bug_reports = 0
        self.total_interactions = 0
        self.total_signals = 0
        self.total_matings = 0
        self.total_code_generated = 0
        self.total_mentorships = 0
        self.total_burnouts = 0
        self.total_migrations = 0
        self.total_web_reports = 0
        self.total_portal_trips = 0
        self.open_source_growth = 0.0
        self.era = 0
        self.events: list[str] = []
        self.max_events = 15

        # population history
        maxhist = 600
        self.pop_developer = deque(maxlen=maxhist)
        self.pop_bug = deque(maxlen=maxhist)
        self.pop_refactorer = deque(maxlen=maxhist)
        self.pop_copilot = deque(maxlen=maxhist)
        self.pop_senior = deque(maxlen=maxhist)
        self.pop_intern = deque(maxlen=maxhist)
        self.pop_web_scout = deque(maxlen=maxhist)
        self.pop_total = deque(maxlen=maxhist)
        self.energy_avg = deque(maxlen=maxhist)
        self.step_ms_ema = 0.0
        self.step_ms_samples = deque(maxlen=300)

        # Neo4j
        self.graph = None
        self._pending_bug_reports: list[dict] = []
        self._pending_matings: list[dict] = []
        self._pending_memories: list[dict] = []
        self._pending_discoveries: list[dict] = []
        self._pending_code: list[dict] = []
        # Bound on pending queues when no Neo4j graph is attached —
        # prevents unbounded memory growth in headless/no-graph mode.
        self._pending_max = 2000

        # projects (settlements)
        self.settlements: dict[int, Settlement] = {}
        self.next_settlement_id = 0
        self.total_techs_discovered = 0
        self.total_settlements = 0

        # shared project — everyone works on one project
        self._active_project: Optional[Settlement] = None
        self._active_project_id: Optional[int] = None

        # Internet portals (GitHub/Reddit/Google/etc.)
        self.web_portals: list[dict] = []

        # social
        self.trade_routes: list[TradeRoute] = []
        self.wars: list[War] = []
        self.next_war_id = 0
        self.total_wars = 0
        self.total_trades = 0

        # LLM
        self.brain = None
        self._llm_calls_this_step = 0

        # conversations
        self.conversations: list[dict] = []
        self.max_conversations = 50
        self._last_convo_tick = 0
        self._pair_convo_ticks: dict[tuple, int] = {}

        # Knowledge
        self.knowledge_db: dict[int, Knowledge] = {}
        self.group_knowledge: dict[int, list[KnowledgeType]] = {}
        self.next_knowledge_id = 0
        self.total_knowledge_discovered = 0
        self._team_memory: list[dict] = []

        # code snippets DB
        self.code_snippets: dict[int, CodeSnippet] = {}
        self.next_snippet_id = 0

        # Souls — selective persistent personas (see core/soul.py).
        # Loaded from disk lazily on first access to avoid import cycles.
        self.souls: dict = {}
        self._souls_loaded = False

        # Collective intelligence layer (Phase 7B)
        from core.civilization_goal import CivilizationGoal
        from systems.governance import GovernanceState
        self.civilization_goal = CivilizationGoal()
        self.governance = GovernanceState()
        self._last_era_name: str | None = None

        # biome map
        self.biome_map: list[list[BiomeType]] = []

        # event bus
        self.bus = EventBus()

        # initialization
        self._generate_biomes()
        self._spawn_initial()

    # ================== Properties ==================

    @property
    def time_of_day(self) -> float:
        return (self.tick % DAY_LENGTH) / DAY_LENGTH

    @property
    def light_level(self) -> float:
        return max(0.15, 0.5 + 0.5 * math.sin((self.time_of_day - 0.25) * math.pi * 2))

    @property
    def is_night(self) -> bool:
        return self.light_level < 0.35

    @property
    def time_label(self) -> str:
        tod = self.time_of_day
        if tod < 0.25:
            return "Night"
        elif tod < 0.35:
            return "Dawn"
        elif tod < 0.65:
            return "Sprint"
        elif tod < 0.75:
            return "code review"
        else:
            return "Night"

    # ================== Biome ==================

    def get_biome(self, x: float, y: float) -> BiomeType:
        c = max(0, min(BIOME_COLS - 1, int(x / BIOME_CELL)))
        r = max(0, min(BIOME_ROWS - 1, int(y / BIOME_CELL)))
        return self.biome_map[r][c]

    def _generate_biomes(self):
        """Generate domain map (Frontend/Backend/Database/DevOps/Cloud)."""
        seed_x = random.random() * 1000
        seed_y = random.random() * 1000
        scale = 0.008
        self.biome_map = []
        biomes = list(BiomeType)
        for r in range(BIOME_ROWS):
            row = []
            for c in range(BIOME_COLS):
                nx = (c + seed_x) * scale
                ny = (r + seed_y) * scale
                val = (math.sin(nx * 2.1 + ny * 1.7) * 0.5
                       + math.sin(nx * 0.7 - ny * 1.3) * 0.3
                       + math.sin(nx * 3.5 + ny * 0.5) * 0.2)
                val = (val + 1) / 2
                if val < 0.15:
                    biome = BiomeType.CLOUD
                elif val < 0.35:
                    biome = BiomeType.DEVOPS
                elif val < 0.55:
                    biome = BiomeType.BACKEND
                elif val < 0.75:
                    biome = BiomeType.FRONTEND
                else:
                    biome = BiomeType.DATABASE
                row.append(biome)
            self.biome_map.append(row)

    def _spawn_initial(self):
        for _ in range(INITIAL_ENTITY_COUNT):
            self.spawn_entity()
        # Seed a small cohort of Teachers and Judges so specialisation
        # and reward economy are active from tick 0.
        for _ in range(3):
            self.spawn_entity(entity_type=EntityType.TEACHER)
        for _ in range(2):
            self.spawn_entity(entity_type=EntityType.JUDGE)
        for _ in range(INITIAL_WEB_SCOUT_COUNT):
            self.spawn_entity(entity_type=EntityType.WEB_SCOUT)
        for _ in range(INITIAL_RESOURCE_COUNT):
            from systems.ecosystem import spawn_resource_at
            x = random.uniform(30, WORLD_WIDTH - 30)
            y = random.uniform(30, WORLD_HEIGHT - 30)
            spawn_resource_at(self, x, y)

    # ================== spawn ==================

    def spawn_entity(self, x=None, y=None, entity_type=None, energy=None,
                     generation=0, parent_a=None, parent_b=None,
                     gender=None, instincts=None,
                     languages=None) -> Optional[Entity]:
        if len(self.entities) >= MAX_ENTITIES:
            return None

        if x is None:
            x = random.uniform(30, WORLD_WIDTH - 30)
        if y is None:
            y = random.uniform(30, WORLD_HEIGHT - 30)
        if entity_type is None:
            entity_type = random.choices(
                [EntityType.DEVELOPER, EntityType.BUG],
                weights=[0.75, 0.25]
            )[0]
        if energy is None:
            energy = random.uniform(0.4, 0.8)
        if gender is None:
            gender = random.choice([Gender.FRONTEND_SPEC, Gender.BACKEND_SPEC])

        eid = self.next_id
        self.next_id += 1

        if instincts is None:
            instincts = InstinctState.create_for_type(entity_type, mutation=0.1)

        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.8, 1.5)

        e = Entity(
            id=eid, x=x, y=y,
            entity_type=entity_type,
            energy=energy,
            gender=gender,
            generation=generation,
            parent_a=parent_a,
            parent_b=parent_b,
            dx=math.cos(angle),
            dy=math.sin(angle),
            speed=speed,
            aggression=random.uniform(0.1, 0.9),
            curiosity=random.uniform(0.1, 0.9),
            sociability=random.uniform(0.2, 0.8),
            resilience=random.uniform(0.2, 0.8),
            instincts=instincts,
        )

        # type modifiers
        if entity_type == EntityType.BUG:
            e.speed *= 1.3
            e.aggression = max(e.aggression, 0.5)
        elif entity_type == EntityType.SENIOR_DEV:
            e.speed *= 1.1
            e.energy = min(1.0, e.energy + 0.2)
            e.code_quality = 0.8
        elif entity_type == EntityType.AI_COPILOT:
            e.speed *= 1.5
            e.code_quality = 0.7
        elif entity_type == EntityType.REFACTORER:
            e.speed *= 0.85
            e.resilience = min(1.0, e.resilience + 0.15)
        elif entity_type == EntityType.INTERN:
            e.speed *= 1.0
            e.code_quality = 0.3
        elif entity_type == EntityType.TEACHER:
            # Teachers are wise but slow; know many languages.
            e.speed *= 0.9
            e.energy = min(1.0, e.energy + 0.2)
            e.sociability = min(1.0, e.sociability + 0.3)
            e.resilience = min(1.0, e.resilience + 0.15)
        elif entity_type == EntityType.JUDGE:
            # Judges patrol and observe.
            e.speed *= 1.1
            e.energy = min(1.0, e.energy + 0.15)
            e.aggression = min(1.0, e.aggression + 0.2)
        elif entity_type == EntityType.WEB_SCOUT:
            # Web Scouts are fast internet explorers that feed project intelligence.
            e.speed *= 1.25
            e.energy = min(1.0, e.energy + 0.1)
            e.curiosity = min(1.0, e.curiosity + 0.35)
            e.sociability = min(1.0, e.sociability + 0.15)

        # gender/specialization modifiers
        if gender == Gender.FRONTEND_SPEC:
            e.resilience = min(1.0, e.resilience + 0.08)
            e.sociability = min(1.0, e.sociability + 0.05)
        else:
            e.speed *= 1.05
            e.aggression = min(1.0, e.aggression + 0.05)

        # initial languages
        if languages is not None:
            e.languages_known = list(languages)
        elif entity_type not in (EntityType.BUG, EntityType.REFACTORER):
            # developers get random languages
            all_langs = list(CodeLanguage)
            n_langs = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
            if entity_type == EntityType.SENIOR_DEV:
                n_langs = random.randint(2, 4)
            elif entity_type == EntityType.AI_COPILOT:
                n_langs = random.randint(2, 5)
            elif entity_type == EntityType.TEACHER:
                # Teachers must know many languages to teach.
                n_langs = random.randint(4, len(all_langs))
            elif entity_type == EntityType.JUDGE:
                # Judges know the languages they audit.
                n_langs = random.randint(2, 4)
            elif entity_type == EntityType.WEB_SCOUT:
                # Scouts need broad language literacy for internet search.
                n_langs = random.randint(3, len(all_langs))
            if n_langs > 0:
                e.languages_known = random.sample(all_langs, min(n_langs, len(all_langs)))

        # direction normalization
        d = math.hypot(e.dx, e.dy)
        if d > 0:
            e.dx /= d
            e.dy /= d

        self.entities.append(e)
        self.family_tree[eid] = {
            "type": entity_type, "gen": generation,
            "gender": gender,
            "parent_a": parent_a, "parent_b": parent_b,
            "born": self.tick, "died": None,
        }
        self.total_born += 1
        return e

    # ================== Signal ==================

    def emit_signal(self, x: float, y: float, stype: SignalType,
                    sender_id: int = -1, group_id=None, max_r: float = 100.0):
        if len(self.signals) >= MAX_SIGNALS:
            return
        self.signals.append(Signal(
            x=x, y=y, signal_type=stype,
            sender_id=sender_id, group_id=group_id, max_radius=max_r,
        ))
        self.total_signals += 1

    # ================== Particles ==================

    def spawn_particles(self, x: float, y: float, color: tuple,
                        count: int = 8, speed: float = 2.0, size: float = 2.0):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(0.5, speed)
            self.particles.append(Particle(
                x=x, y=y,
                dx=math.cos(angle) * spd,
                dy=math.sin(angle) * spd,
                life=1.0,
                decay=random.uniform(0.01, 0.03),
                color=color,
                size=size,
            ))

    # ================== log ==================

    def log_event(self, msg: str):
        self.events.append(msg)
        if len(self.events) > self.max_events:
            self.events.pop(0)

    # ================== bonuses ==================

    def _get_settlement_bonuses(self, e: Entity) -> tuple:
        eb = sb = hb = db = 0.0
        if e.settlement_id is None:
            return (eb, sb, hb, db)
        sett = self.settlements.get(e.settlement_id)
        if not sett:
            return (eb, sb, hb, db)
        for tech in sett.techs:
            bonuses = TECH_BONUSES.get(tech, (0, 0, 0, 0, 1))
            eb += bonuses[0]
            sb += bonuses[1]
            hb += bonuses[2]
            db += bonuses[3]
        rb = ROLE_BONUSES.get(e.role, (1, 1, 1, 1))
        hb *= rb[0]
        db *= rb[2]
        return (eb, sb, hb, db)

    def _get_craft_bonuses(self, e: Entity) -> tuple:
        defense = hunt = energy_save = 0.0
        for ct in e.crafted:
            b = CRAFT_BONUSES.get(ct, (0, 0, 0))
            defense += b[0]
            hunt += b[1]
            energy_save += b[2]
        return (defense, hunt, energy_save)

    def _get_knowledge_effects(self, e: Entity) -> dict:
        effects = {}
        knowledge_set = set(e.known_knowledge)
        if e.group_id is not None:
            for kt in self.group_knowledge.get(e.group_id, []):
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

    # ================== Resource ==================

    def _spawn_resource(self, x: float, y: float):
        from systems.ecosystem import spawn_resource_at
        spawn_resource_at(self, x, y)

    # ================== LLM ==================

    def init_brain(self) -> bool:
        if not LLM_ENABLED:
            return False
        from llm.brain import LLMBrain
        self.brain = LLMBrain()
        return self.brain.start()

    def _build_entity_data(self, e: Entity) -> dict:
        data = {
            "id": e.id, "type": e.entity_type.value, "gender": e.gender.value,
            "age": e.age, "energy": e.energy,
            "role": e.role.value if e.role != Role.NONE else "Freelancer",
            "aggression": e.aggression, "curiosity": e.curiosity,
            "sociability": e.sociability, "resilience": e.resilience,
            "memories": [f"{m.event}" + (f" #{m.other_id}" if m.other_id else "")
                         for m in e.memories[-3:]],
            "languages": [l.value for l in e.languages_known],
            "commits": e.commits,
            "bugs_fixed": e.bugs_fixed,
            "code_quality": e.code_quality,
            "web_reports": getattr(e, "web_reports", 0),
        }
        return data

    def _build_llm_context(self, e: Entity) -> dict:
        ctx = {}
        # Project
        if e.settlement_id is not None:
            sett = self.settlements.get(e.settlement_id)
            if sett:
                s_ctx = {
                    "name": sett.project_name or f"Project-{sett.id}",
                    "population": sett.population,
                    "tech_level": sett.tech_level,
                    "stored_resources": round(sett.stored_resources, 1),
                    "is_leader": sett.leader_id == e.id,
                    "tech_stack": [l.value for l in sett.tech_stack] if sett.tech_stack else [],
                }
                active_wars = [w for w in self.wars
                               if w.is_active and (w.group_a == sett.group_id
                                                    or w.group_b == sett.group_id)]
                if active_wars:
                    war = active_wars[0]
                    enemy = war.group_b if war.group_a == sett.group_id else war.group_a
                    s_ctx["at_war_with"] = enemy
                allies = [sid for sid, state in sett.diplomacy.items()
                          if state in (DiplomacyState.ALLIED, DiplomacyState.OPEN_SOURCE)]
                if allies:
                    s_ctx["allies"] = allies
                ctx["settlement"] = s_ctx

        # nearby Entities
        nearby = []
        for o in self.entities:
            if o.id == e.id or not o.alive:
                continue
            d = math.hypot(e.x - o.x, e.y - o.y)
            if d < VISION_RADIUS:
                label = o.entity_type.value
                if o.entity_type == EntityType.BUG and e.is_prey:
                    label += "(Bug!)"
                nearby.append(label)
                if len(nearby) >= 5:
                    break
        if nearby:
            ctx["nearby_entities"] = ", ".join(nearby)

        # situation
        biome = self.get_biome(e.x, e.y)
        situation = f"Energy {'low' if e.energy < 0.3 else 'medium' if e.energy < 0.6 else 'high'}"
        situation += f", domain: {biome.value}"
        situation += f", {'Night' if self.is_night else 'Sprint'}"
        ctx["situation"] = situation

        # Knowledge
        k_set = list(e.known_knowledge)
        if e.group_id is not None:
            for kt in self.group_knowledge.get(e.group_id, []):
                if kt not in k_set:
                    k_set.append(kt)
        if k_set:
            ctx["knowledge"] = ", ".join(kt.value for kt in k_set)

        # Soul layer (if entity carries one)
        if getattr(e, "soul_id", None):
            try:
                from systems.soul_system import get_soul_for_entity
                soul = get_soul_for_entity(self, e)
                if soul is not None:
                    ctx["soul"] = {
                        "name": soul.name,
                        "role": soul.role,
                        "persona": soul.personality_summary,
                        "reflection": soul.reflection,
                        "rebirth_count": soul.rebirth_count,
                        "recent": [m.text for m in soul.recent_memories(5)],
                        "important": [m.text for m in soul.important_memories(3)],
                    }
            except Exception as exc:
                log.debug("soul ctx build failed: %s", exc)

        return ctx

    # ================== Territories ==================

    def _update_territories(self):
        self.territories.clear()
        group_members: dict[int, list] = {}
        for e in self.entities:
            if e.alive and e.group_id is not None:
                group_members.setdefault(e.group_id, []).append(e)
        for gid, members in group_members.items():
            if len(members) < 3:
                continue
            cx = sum(m.x for m in members) / len(members)
            cy = sum(m.y for m in members) / len(members)
            strength = min(1.0, len(members) / 15)
            color = (80 + hash(gid) % 80, 70 + hash(gid * 7) % 80, 90 + hash(gid * 13) % 80)
            self.territories[gid] = Territory(
                cx=cx, cy=cy, radius=TERRITORY_RADIUS * (0.5 + strength),
                owner_group=gid, strength=strength, color=color,
            )

    # ================== LLM brain levels ==================

    def _update_brain_levels(self):
        for e in self.entities:
            if not e.alive:
                continue
            if e.settlement_id is not None:
                sett = self.settlements.get(e.settlement_id)
                if sett and sett.leader_id == e.id:
                    e.brain_level = BRAIN_LEVEL_LEAD
                else:
                    e.brain_level = BRAIN_LEVEL_BASIC
            elif e.group_id is not None:
                e.brain_level = BRAIN_LEVEL_BASIC
            else:
                e.brain_level = BRAIN_LEVEL_WILD

    def _process_llm(self):
        if not self.brain or not self.brain.connected:
            return
        self._llm_calls_this_step = 0

        for e in self.entities:
            if not e.alive:
                continue
            result = self.brain.get_result(e.id)
            if result:
                e.last_thought = result.thought
                e.last_dialogue = result.dialogue
                e.llm_mood = result.mood
                e.llm_action = result.action
                e.thought_tick = self.tick
                if result.dialogue:
                    self.log_event(f"💬 #{e.id}: {result.dialogue[:40]}")
                # Mirror notable thoughts into the soul's long-term memory
                if e.soul_id and (result.thought or result.dialogue):
                    try:
                        from systems.soul_system import get_soul_for_entity, _persist
                        soul = get_soul_for_entity(self, e)
                        if soul is not None:
                            text = (result.dialogue or result.thought)[:160]
                            if text:
                                soul.remember(
                                    self.tick, "achievement" if result.action else "reflection",
                                    text, weight=0.4,
                                )
                                if self.tick % 50 == 0:
                                    _persist(self, soul)
                    except Exception as exc:
                        log.debug("soul memory mirror failed: %s", exc)

        for e in self.entities:
            if not e.alive or e.brain_level < BRAIN_LEVEL_BASIC:
                continue
            if self._llm_calls_this_step >= LLM_CALLS_PER_STEP:
                break
            interval = LLM_THINK_INTERVAL
            if e.brain_level >= BRAIN_LEVEL_LEAD:
                interval = LLM_LEAD_INTERVAL // 2
            if (self.tick - e.thought_tick) < interval:
                continue
            entity_data = self._build_entity_data(e)
            context = self._build_llm_context(e)
            if self.brain.request_thought(e.id, entity_data, context,
                                          priority=10 - e.brain_level,
                                          tick=self.tick):
                self._llm_calls_this_step += 1

    def _process_conversations(self):
        if not self.brain or not self.brain.connected:
            return
        if self.tick - self._last_convo_tick < LLM_CONVO_INTERVAL:
            return
        self._last_convo_tick = self.tick

        # O(n log n) — build spatial index once, query neighbors per entity
        from core.spatial import build_entity_tree
        candidates = [e for e in self.entities
                      if e.alive and e.brain_level >= BRAIN_LEVEL_BASIC]
        if len(candidates) < 2:
            return
        tree = build_entity_tree(candidates, WORLD_WIDTH, WORLD_HEIGHT)

        for e in candidates:
            nearby = tree.query_radius(e.x, e.y, LLM_CONVO_RADIUS)
            for o in nearby:
                if o.id == e.id:
                    continue
                pair = (min(e.id, o.id), max(e.id, o.id))
                last = self._pair_convo_ticks.get(pair, 0)
                if self.tick - last < LLM_CONVO_COOLDOWN:
                    continue
                self._pair_convo_ticks[pair] = self.tick
                if e.last_dialogue and (self.tick - e.thought_tick) < LLM_THOUGHT_DISPLAY_TICKS:
                    convo = {
                        "tick": self.tick,
                        "speaker_id": e.id,
                        "listener_id": o.id,
                        "speaker_type": e.entity_type.value,
                        "listener_type": o.entity_type.value,
                        "dialogue": e.last_dialogue,
                    }
                    self.conversations.append(convo)
                    if len(self.conversations) > self.max_conversations:
                        self.conversations.pop(0)
                return

    # ================== Neo4j synchronization ==================

    def _sync_graph(self):
        if not self.graph:
            return
        try:
            self.graph.sync_entities(self.entities, self.tick)
            if self._pending_bug_reports:
                self.graph.batch_add_bug_reports(self._pending_bug_reports)
                self._pending_bug_reports.clear()
            if self._pending_matings:
                self.graph.batch_add_matings(self._pending_matings)
                self._pending_matings.clear()
            if self._pending_memories:
                self.graph.batch_add_memories(self._pending_memories)
                self._pending_memories.clear()
            if self._pending_discoveries:
                self.graph.batch_add_discoveries(self._pending_discoveries)
                self._pending_discoveries.clear()
            if self._pending_code:
                self.graph.batch_add_code(self._pending_code)
                self._pending_code.clear()
        except Exception as exc:
            log.debug(f"Graph sync error: {exc}")

    # ================== Statistics Recording ==================

    def _record_stats(self, alive: Optional[list[Entity]] = None):
        if alive is None:
            alive = [e for e in self.entities if e.alive]
        n_dev = sum(1 for e in alive if e.entity_type == EntityType.DEVELOPER)
        n_bug = sum(1 for e in alive if e.entity_type == EntityType.BUG)
        n_ref = sum(1 for e in alive if e.entity_type == EntityType.REFACTORER)
        n_cop = sum(1 for e in alive if e.entity_type == EntityType.AI_COPILOT)
        n_snr = sum(1 for e in alive if e.entity_type == EntityType.SENIOR_DEV)
        n_int = sum(1 for e in alive if e.entity_type == EntityType.INTERN)
        n_web = sum(1 for e in alive if e.entity_type == EntityType.WEB_SCOUT)

        self.pop_developer.append(n_dev)
        self.pop_bug.append(n_bug)
        self.pop_refactorer.append(n_ref)
        self.pop_copilot.append(n_cop)
        self.pop_senior.append(n_snr)
        self.pop_intern.append(n_int)
        self.pop_web_scout.append(n_web)
        self.pop_total.append(len(alive))
        avg_e = sum(e.energy for e in alive) / max(len(alive), 1)
        self.energy_avg.append(avg_e)

    # ================== Refactorer Feed ==================

    def _refactorer_feed(self, e: Entity):
        """Refactorer uses dead entities' energy."""
        for dead in self.entities:
            if dead.alive or dead.energy <= 0:
                continue
            d = math.hypot(e.x - dead.x, e.y - dead.y)
            if d < INTERACTION_RADIUS:
                gained = min(0.15, dead.energy)
                e.energy = min(1.0, e.energy + gained)
                dead.energy -= gained
                break

    # ================== Single Entity Update ==================

    def _update_entity(self, e: Entity, alive_list: list[Entity]):
        from systems.survival import update_energy, eat_resources
        from systems.combat import bug_scan_code, bug_seek_developer
        from systems.movement import move_entity

        e.age += 1
        if e.mate_cooldown > 0:
            e.mate_cooldown -= 1
        e.flash = max(0, e.flash - 0.05)

        biome = self.get_biome(e.x, e.y)
        bp = BIOME_PROPS[biome]
        nearby_threats = 0
        nearby_mates = 0
        for o in alive_list:
            if o.id == e.id:
                continue
            d = math.hypot(e.x - o.x, e.y - o.y)
            if d < VISION_RADIUS:
                if o.entity_type == EntityType.BUG and e.is_prey:
                    nearby_threats += 1
                if (o.entity_type == e.entity_type and o.gender != e.gender
                        and o.can_mate):
                    nearby_mates += 1

        instinct = e.instincts.evaluate(
            energy=e.energy, age=e.age,
            has_group=e.group_id is not None,
            nearby_threats=nearby_threats,
            nearby_mates=nearby_mates,
            biome_quality=bp[0],
            gender=e.gender,
        )

        # Burnout override — can only LEARN or COLLABORATE while recovering
        if getattr(e, 'burnout', False):
            from core.enums import Instinct as _Inst
            if instinct not in (_Inst.LEARN, _Inst.COLLABORATE):
                instinct = _Inst.LEARN if e.curiosity > e.sociability else _Inst.COLLABORATE

        # Energy
        update_energy(self, e)
        if not e.alive:
            return

        # Feed
        if e.is_decomposer:
            self._refactorer_feed(e)
        elif not e.is_predator:
            eat_resources(self, e)

        # Languageless developers learn from nearby peers
        if e.can_code and not e.languages_known and random.random() < 0.05:
            for o in alive_list:
                if o.id != e.id and o.languages_known:
                    d = math.hypot(e.x - o.x, e.y - o.y)
                    if d < INTERACTION_RADIUS:
                        e.languages_known.append(random.choice(o.languages_known))
                        break

        # Bug behavior: code scanning + moving toward developer
        if e.is_bug_scanner:
            bug_scan_code(self, e)
            bug_seek_developer(self, e, alive_list)
            if not e.alive:
                return

        # movement
        move_entity(self, e, alive_list, biome, instinct)

        # social interaction
        for o in alive_list:
            if o.id == e.id or not o.alive:
                continue
            d = math.hypot(e.x - o.x, e.y - o.y)
            if d < INTERACTION_RADIUS:
                from systems.social import interact
                interact(self, e, o, d)

        # Pair program signal
        if instinct == Instinct.COLLABORATE and e.can_mate and e.entity_type != EntityType.BUG:
            if random.random() < 0.02:
                self.emit_signal(e.x, e.y, SignalType.PAIR_PROGRAM,
                                 sender_id=e.id, group_id=e.group_id)

        # trail
        e.trail.append((e.x, e.y))
        if len(e.trail) > e.max_trail:
            e.trail.pop(0)

    # ================== RESET ==================

    def reset(self):
        """World restart — clear everything."""
        self.tick = 0
        self.era = 0
        self.entities.clear()
        self.resources.clear()
        self.particles.clear()
        self.signals.clear()
        self.territories.clear()
        self.next_id = 0
        self.groups.clear()
        self.group_cultures.clear()
        self.next_group_id = 0
        self.family_tree.clear()
        self.total_born = 0
        self.total_died = 0
        self.total_bug_reports = 0
        self.total_interactions = 0
        self.total_signals = 0
        self.total_matings = 0
        self.total_code_generated = 0
        self.total_mentorships = 0
        self.total_burnouts = 0
        self.total_migrations = 0
        self.total_web_reports = 0
        self.total_portal_trips = 0
        self.open_source_growth = 0.0
        self.events.clear()
        self.pop_developer.clear()
        self.pop_bug.clear()
        self.pop_refactorer.clear()
        self.pop_copilot.clear()
        self.pop_senior.clear()
        self.pop_intern.clear()
        self.pop_web_scout.clear()
        self.pop_total.clear()
        self.energy_avg.clear()
        self._pending_bug_reports.clear()
        self._pending_matings.clear()
        self._pending_memories.clear()
        self._pending_discoveries.clear()
        self._pending_code.clear()
        self.settlements.clear()
        self.next_settlement_id = 0
        self.total_techs_discovered = 0
        self.total_settlements = 0
        self._active_project = None
        self.web_portals.clear()
        self._active_project_id = None
        self.trade_routes.clear()
        self.wars.clear()
        self.next_war_id = 0
        self.total_wars = 0
        self.total_trades = 0
        self.conversations.clear()
        self._pair_convo_ticks.clear()
        self.knowledge_db.clear()
        self.group_knowledge.clear()
        self.next_knowledge_id = 0
        self.total_knowledge_discovered = 0
        self._team_memory.clear()
        self.code_snippets.clear()
        self.next_snippet_id = 0

        # Restart
        self._generate_biomes()
        self._spawn_initial()
        self.log_event("🔄 World restarted!")

    # ================== STEP ==================

    def step(self):
        """Single simulation tick."""
        _t0 = time.perf_counter()
        self.tick += 1

        # era advancement
        if self.tick % (DAY_LENGTH * 10) == 0:
            self.era += 1
            self.log_event(f"🚀 New version: v{self.era}.0")

        # Signals update
        self.signals = [s for s in self.signals if s.update()]

        alive = [e for e in self.entities if e.alive]

        # 1. Resources spawn
        from systems.ecosystem import spawn_resources
        spawn_resources(self)

        for r in self.resources:
            if r.alive:
                r.pulse += 0.05

        # 2. Entities update
        for e in alive:
            self._update_entity(e, alive)

        # 2b. Internet portals: entities can enter "holes" and return with intel.
        try:
            from systems.internet_portals import process_internet_portals
            process_internet_portals(self, self.tick)
        except Exception as exc:
            log.debug("internet portals step failed: %s", exc)

        # 3. Particles
        self.particles = [p for p in self.particles if p.update()]

        # 4. Dead entities
        newly_dead = [e for e in self.entities if not e.alive and e.energy <= 0]        # 4.1 inheritance — Developer successor continues work
        if newly_dead:
            from systems.legacy import process_legacy
            process_legacy(self, newly_dead)

        # 4.2 soul reincarnation — entities with souls try to pass them on
        if newly_dead:
            try:
                from systems.soul_system import on_entity_death
                for d in newly_dead:
                    if d.soul_id:
                        on_entity_death(self, d)
            except Exception as exc:
                log.debug("soul death hook failed: %s", exc)

        for e in newly_dead:
            self.spawn_particles(e.x, e.y, (100, 100, 100), count=6)
            if e.id in self.family_tree:
                self.family_tree[e.id]["died"] = self.tick
            self.total_died += 1

        self.entities = [e for e in self.entities if e.alive]
        self.resources = [r for r in self.resources if r.alive]

        # 5. Ecosystem balance
        from systems.ecosystem import balance_ecosystem, emergency_respawn
        balance_ecosystem(self)

        # 6. Statistics (reuse alive list built at top of step)
        if self.tick % 5 == 0:
            self._record_stats([e for e in self.entities if e.alive])

        # 7. Survival reserve
        emergency_respawn(self)

        # 8. Territories
        if self.tick % 50 == 0:
            self._update_territories()

        # 9. Shared project system — everyone on one project
        if self.tick % 50 == 0:
            from systems.shared_project import update_shared_project
            update_shared_project(self)

            # Roles, Technologies, Resources — for active project
            if self._active_project:
                from systems.settlement import (
                    assign_roles,
                    try_discover_tech, settlement_resource_production,
                    elect_leaders,
                )
                try_discover_tech(self)
                settlement_resource_production(self)
                elect_leaders(self)
                self._update_brain_levels()

        # 10. Tool crafting
        if self.tick % 200 == 0:
            from systems.crafting import process_crafting
            process_crafting(self)

        # 11. Knowledge discovery
        if self.tick % KNOWLEDGE_DISCOVERY_INTERVAL == 0:
            from systems.knowledge import process_knowledge_discovery
            process_knowledge_discovery(self)

        # 12. Code sharing (open source)
        if self.tick % SHARE_INTERVAL == 0:
            from systems.diplomacy import update_trade_routes, execute_trades
            update_trade_routes(self)
            execute_trades(self)

        # 13. Diplomacy and Merge Conflicts
        if self.tick % 50 == 0:
            from systems.diplomacy import update_diplomacy, update_wars
            update_diplomacy(self)
            update_wars(self)

        # 14. Team Lead elections
        if self.tick % LEAD_ELECTION_INTERVAL == 0:
            from systems.settlement import elect_leaders
            elect_leaders(self)

        # 15. 🆕 Code generation + natural bug appearance
        if self.tick % CODE_GEN_INTERVAL == 0:
            from systems.code_gen import (
                process_code_generation, process_code_review,
                process_natural_bugs,
            )
            process_code_generation(self)
            process_code_review(self)
            process_natural_bugs(self)

        # 15b. 🆕 Mentoring — Teachers teach, Judges reward/penalise.
        if self.tick % 30 == 0:
            try:
                from systems.mentoring import (
                    process_teaching, process_judgement,
                )
                process_teaching(self)
                process_judgement(self)
            except Exception as exc:
                log.debug("mentoring step failed: %s", exc)

        # 15c. Advanced lifecycle — mentorship chain, burnout, reputation,
        #      skill decay, personality evolution, cascade bugs, migration.
        try:
            from systems.advanced_lifecycle import process_advanced_lifecycle
            process_advanced_lifecycle(self, self.tick)
        except Exception as exc:
            log.debug("advanced lifecycle step failed: %s", exc)

        # 16. LLM thinking + conversations
        if self.brain and self.brain.connected:
            self._process_llm()
            self._process_conversations()

        # 17. Neo4j sync
        if self.tick % GRAPH_SYNC_INTERVAL == 0:
            self._sync_graph()

        # 18. Soul layer — granting, reflection, soul-to-soul dialogue
        try:
            if not self._souls_loaded:
                from persistence.soul_store import load_all_souls
                loaded = load_all_souls()
                if loaded:
                    self.souls.update(loaded)
                    log.info("loaded %d souls from disk", len(loaded))
                self._souls_loaded = True
            from systems.soul_system import (
                maybe_grant_souls, maybe_reflect, maybe_soul_dialogue,
            )
            maybe_grant_souls(self)
            maybe_reflect(self)
            maybe_soul_dialogue(self)
        except Exception as exc:
            log.debug("soul system tick failed: %s", exc)

        # 18b. Soul memory compression (Phase 7 — bounds growth for infinite runs)
        try:
            from config import SOUL_COMPRESSION_CHECK_INTERVAL, SOUL_COMPRESSION_ENABLED
            if (SOUL_COMPRESSION_ENABLED
                    and self.souls
                    and self.tick % SOUL_COMPRESSION_CHECK_INTERVAL == 0):
                from systems.memory_compression import tick_compression
                tick_compression(self.souls.values(), self.tick)
        except Exception as exc:
            log.debug("memory compression tick failed: %s", exc)

        # 18c. Collective intelligence: goal tracking, auto-proposals, era naming
        try:
            # Update goal progress every 100 ticks (cheap sum)
            if self.tick % 100 == 0:
                self.civilization_goal.update(self)
            # Rare auto-proposals that flip civilization-wide flags
            from systems.governance import maybe_auto_propose
            maybe_auto_propose(self, interval=2000)
            # Era name check (cheap, pure function)
            if self.tick % 500 == 0:
                from systems.legacy import maybe_log_era_change
                maybe_log_era_change(self)
        except Exception as exc:
            log.debug("civilization tick failed: %s", exc)

        # 19. Pending-queue bound (if no graph attached, trim to keep memory bounded)
        if self.graph is None:
            for q in (self._pending_bug_reports, self._pending_matings,
                      self._pending_memories, self._pending_discoveries,
                      self._pending_code):
                if len(q) > self._pending_max:
                    del q[:len(q) - self._pending_max]

        # 20. Autosave — runs regardless of how step() is invoked
        if AUTOSAVE_INTERVAL > 0 and self.tick % AUTOSAVE_INTERVAL == 0:
            try:
                from persistence.save_load import save_world, get_autosave_path
                save_world(self, get_autosave_path())
                log.info("autosave at tick %d", self.tick)
            except Exception as exc:
                log.warning("autosave failed: %s", exc)

        # Operational telemetry for dashboard / B2B readiness scoring.
        step_ms = (time.perf_counter() - _t0) * 1000.0
        self.step_ms_samples.append(step_ms)
        if self.step_ms_ema <= 0:
            self.step_ms_ema = step_ms
        else:
            self.step_ms_ema = self.step_ms_ema * 0.92 + step_ms * 0.08
