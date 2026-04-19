"""Models — all dataclasses for the code world."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from core.enums import (
    EntityType, ResourceType, SignalType, BiomeType, Gender, Instinct,
    Role, TechType, DiplomacyState, CraftableType, KnowledgeType, CodeLanguage,
)
from config import (
    ENTITY_RADIUS, INSTINCT_WEIGHTS,
    DEV_MIN_ENERGY_TO_CODE, DEV_MIN_AGE_TO_REPRODUCE,
    PREDATOR_MATE_ENERGY, BUG_MIN_AGE_TO_SPREAD,
    PROJECT_RADIUS,
)


# ================== Colors ==================

TYPE_COLORS = {
    EntityType.DEVELOPER:   (70, 170, 230),   # blue
    EntityType.BUG:         (220, 50, 50),     # red
    EntityType.REFACTORER:  (180, 140, 50),    # yellow
    EntityType.AI_COPILOT:  (150, 100, 220),   # purple
    EntityType.SENIOR_DEV:  (255, 215, 0),     # Golden
    EntityType.INTERN:      (100, 200, 150),   # green
    EntityType.TEACHER:     (80, 220, 220),    # cyan
    EntityType.JUDGE:       (255, 120, 200),   # pink
    EntityType.WEB_SCOUT:   (120, 240, 255),   # ice blue
}

RESOURCE_COLORS = {
    ResourceType.DOCUMENTATION: (60, 140, 200),
    ResourceType.LIBRARY:       (180, 80, 200),
    ResourceType.BOILERPLATE:   (160, 130, 70),
    ResourceType.FRAMEWORK:     (120, 140, 160),
    ResourceType.COFFEE:        (90, 60, 30),
}


# ================== Particle ==================

@dataclass
class Particle:
    x: float
    y: float
    dx: float
    dy: float
    life: float
    decay: float
    color: tuple
    size: float

    def update(self) -> bool:
        self.x += self.dx
        self.y += self.dy
        self.dx *= 0.96
        self.dy *= 0.96
        self.life -= self.decay
        return self.life > 0


# ================== Resource ==================

@dataclass
class Resource:
    x: float
    y: float
    resource_type: ResourceType
    energy: float
    pulse: float = 0.0

    @property
    def alive(self) -> bool:
        return self.energy > 0.01

    @property
    def color(self) -> tuple:
        base = RESOURCE_COLORS[self.resource_type]
        pf = 0.7 + 0.3 * math.sin(self.pulse)
        return (int(base[0] * pf), int(base[1] * pf), int(base[2] * pf))

    @property
    def radius(self) -> int:
        return max(2, int(3 + 3 * self.energy))


# ================== Memory ==================

@dataclass
class Memory:
    tick: int
    event: str
    other_id: Optional[int] = None
    value: float = 0.0


# ================== Territory ==================

@dataclass
class Territory:
    cx: float
    cy: float
    radius: float
    owner_group: int
    strength: float = 0.0
    color: tuple = (80, 80, 120)


# ================== Signal ==================

@dataclass
class Signal:
    x: float
    y: float
    signal_type: SignalType
    radius: float = 5.0
    max_radius: float = 100.0
    strength: float = 1.0
    sender_id: int = -1
    group_id: Optional[int] = None

    def update(self) -> bool:
        self.radius += 2.0
        self.strength *= 0.95
        return self.radius < self.max_radius and self.strength > 0.04


# ================== Culture / Coding Style ==================

@dataclass
class Culture:
    food_pref: float = 0.5         # coffee vs documentation
    aggression_norm: float = 0.5   # aggressive debugging
    nocturnal: float = 0.0         # night coding
    cooperation: float = 0.5       # pair programming frequency
    wander_range: float = 0.5      # wandering across domains


# ================== Code Snippets (new!) ==================

@dataclass
class CodeSnippet:
    id: int
    author_id: int
    language: CodeLanguage
    content: str
    description: str = ""
    quality: float = 0.5
    tick_created: int = 0
    reviewed: bool = False
    reviewer_id: Optional[int] = None
    has_bugs: bool = False
    lines: int = 0
    filename: str = ""

    @property
    def is_good(self) -> bool:
        return self.quality > 0.6 and not self.has_bugs


# ================== Project (Settlement) ==================

@dataclass
class Settlement:
    id: int
    group_id: int
    x: float
    y: float
    radius: float = PROJECT_RADIUS
    population: int = 0
    founded_tick: int = 0
    techs: list = field(default_factory=list)
    stored_resources: float = 0.0
    buildings: int = 0
    leader_id: Optional[int] = None
    diplomacy: dict = field(default_factory=dict)
    peace_cooldowns: dict = field(default_factory=dict)

    # code world new fields
    # At runtime this is list[CodeSnippet] (objects are appended in code_gen
    # and iterated elsewhere). Save/load serialises it via snippet IDs.
    codebase: list = field(default_factory=list)
    tech_stack: list = field(default_factory=list)      # list of CodeLanguages
    project_name: str = ""
    total_commits: int = 0
    bug_count: int = 0
    max_files: int = 0

    # project phases and structure
    phase: str = "architecture"                         # architecture / development / review / push
    phase_tick: int = 0                                 # phase start tick
    file_structure: list = field(default_factory=list)   # planned file structure
    team_meetings: int = 0                              # how many meetings were held
    review_rounds: int = 0                              # how many review rounds

    @property
    def tech_level(self) -> int:
        return len(self.techs)

    def has_tech(self, tech: TechType) -> bool:
        return tech in self.techs

    @property
    def code_quality(self) -> float:
        """Project average code quality (CodeSnippet objects required)."""
        snippets = [c for c in self.codebase if hasattr(c, "quality")]
        if not snippets:
            return 0.0
        return sum(c.quality for c in snippets) / len(snippets)


# ================== Sharing Route (Open Source) ==================

@dataclass
class TradeRoute:
    settlement_a: int
    settlement_b: int
    established_tick: int
    strength: float = 1.0
    total_traded: float = 0.0
    active: bool = True


# ================== Merge Conflict (War) ==================

@dataclass
class War:
    id: int
    group_a: int
    group_b: int
    started_tick: int
    duration: int = 0
    casualties_a: int = 0
    casualties_b: int = 0
    resolved: bool = False
    winner: Optional[int] = None

    @property
    def is_active(self) -> bool:
        return not self.resolved


# ================== instincts ==================

@dataclass
class InstinctState:
    weights: dict = field(default_factory=dict)
    active: Optional[Instinct] = None
    urgency: float = 0.0
    cooldowns: dict = field(default_factory=dict)

    def evaluate(self, energy: float, age: int, has_group: bool,
                 nearby_threats: int, nearby_mates: int,
                 biome_quality: float, gender: Gender) -> Instinct:
        scores: dict[Instinct, float] = {}
        for inst, base_w in self.weights.items():
            cd = self.cooldowns.get(inst, 0)
            if cd > 0:
                self.cooldowns[inst] = cd - 1
                scores[inst] = base_w * 0.1
                continue
            scores[inst] = base_w

        # burnout — energy is low
        if energy < 0.2:
            scores[Instinct.LEARN] *= 0.3
            scores[Instinct.CODE] *= 0.2
            scores[Instinct.COLLABORATE] *= 2.5  # asks for help

        # bugs are nearby
        if nearby_threats > 0:
            scores[Instinct.DEBUG] *= (1.5 + nearby_threats * 0.5)

        # energy is high — coding
        if energy > DEV_MIN_ENERGY_TO_CODE and age > DEV_MIN_AGE_TO_REPRODUCE:
            scores[Instinct.CODE] *= 1.8
            if nearby_mates > 0:
                scores[Instinct.COLLABORATE] *= 1.5
            if gender == Gender.FRONTEND_SPEC:
                scores[Instinct.CODE] *= 0.9  # frontend slightly less feature
        else:
            scores[Instinct.CODE] *= 0.3

        # team
        if has_group:
            scores[Instinct.DEPLOY] *= 1.6
            if nearby_threats > 0:
                scores[Instinct.DEBUG] *= 2.0
        else:
            scores[Instinct.DEPLOY] *= 0.2

        # biome quality
        if biome_quality < 0.4:
            scores[Instinct.LEARN] *= 2.5   # migrate to new domain
        elif biome_quality > 0.8:
            scores[Instinct.LEARN] *= 0.5

        # Refactoring
        if energy > 0.5:
            scores[Instinct.REFACTOR] *= 1.3
        else:
            scores[Instinct.REFACTOR] *= 0.3

        if not scores:
            return Instinct.CODE
        best = max(scores, key=lambda k: scores[k])
        self.active = best
        self.urgency = scores[best]
        return best

    def set_cooldown(self, instinct: Instinct, ticks: int):
        self.cooldowns[instinct] = ticks

    @staticmethod
    def create_for_type(etype: EntityType, mutation: float = 0.0) -> InstinctState:
        base = INSTINCT_WEIGHTS.get(etype, {})
        weights = {}
        for inst, w in base.items():
            weights[inst] = max(0.0, min(1.0, w + random.uniform(-mutation, mutation)))
        return InstinctState(weights=weights)

    @staticmethod
    def inherit(parent_a: InstinctState, parent_b: InstinctState,
                mutation: float = 0.08) -> InstinctState:
        weights = {}
        for inst in Instinct:
            wa = parent_a.weights.get(inst, 0.5)
            wb = parent_b.weights.get(inst, 0.5)
            weights[inst] = max(0.0, min(1.0,
                (wa + wb) / 2 + random.uniform(-mutation, mutation)))
        return InstinctState(weights=weights)


# ================== Knowledge ==================

@dataclass
class Knowledge:
    id: int
    knowledge_type: KnowledgeType
    name: str
    description: str = ""
    discovered_at_tick: int = 0
    discovered_by_entity: Optional[int] = None
    discovered_by_group: Optional[int] = None


# ================== entity (Developer/Bug/...) ==================

@dataclass
class Entity:
    id: int
    x: float
    y: float
    entity_type: EntityType
    energy: float
    gender: Gender

    age: int = 0
    generation: int = 0

    aggression: float = 0.0
    curiosity: float = 0.0
    sociability: float = 0.0
    resilience: float = 0.0
    nocturnal: float = 0.0

    dx: float = 0.0
    dy: float = 0.0
    speed: float = 1.0

    memories: list = field(default_factory=list)
    max_memories: int = 25
    relationships: dict = field(default_factory=dict)

    alive: bool = True
    group_id: Optional[int] = None
    settlement_id: Optional[int] = None
    role: Role = Role.NONE
    home_x: Optional[float] = None
    home_y: Optional[float] = None
    ticks_at_home: int = 0
    mate_cooldown: int = 0

    trail: list = field(default_factory=list)
    max_trail: int = 25
    flash: float = 0.0
    target_id: Optional[int] = None

    parent_a: Optional[int] = None
    parent_b: Optional[int] = None

    instincts: InstinctState = field(default_factory=InstinctState)

    brain_level: int = 0
    last_thought: str = ""
    last_dialogue: str = ""
    thought_tick: int = 0
    llm_mood: str = ""
    llm_action: str = ""

    inventory: dict = field(default_factory=dict)
    crafted: list = field(default_factory=list)

    known_knowledge: list = field(default_factory=list)

    # ===== Code world new fields =====
    languages_known: list = field(default_factory=list)    # list of CodeLanguages
    # Per-language experience points (phase 7C specialisation).
    # Key is CodeLanguage.value (str) to keep serialisation trivial.
    language_xp: dict = field(default_factory=dict)
    # Cumulative reward/penalty energy granted by Judge entities.
    judge_rewards: float = 0.0
    judge_penalties: float = 0.0
    # Mentor tracking — how many devs this Teacher has taught.
    students_taught: int = 0
    code_output: list = field(default_factory=list)        # list of CodeSnippet IDs
    bugs_fixed: int = 0
    bugs_introduced: int = 0
    code_quality: float = 0.5
    commits: int = 0
    reviews_done: int = 0
    pair_partner_id: Optional[int] = None
    dev_name: str = ""      # LLM-generated name
    found_bug_in: Optional[int] = None    # which snippet the Bug found a bug in
    reported_to_dev: Optional[int] = None  # which developer the Bug reported to

    # ===== Phase 8: Advanced lifecycle =====
    reputation: float = 0.5              # 0..1 — Judge rewards raise, penalties lower
    burnout: bool = False                # True = in vacation/recovery mode
    burnout_ticks: int = 0               # ticks remaining in burnout recovery
    personality_xp: dict = field(default_factory=dict)  # combat/meeting/learn counters
    language_last_used: dict = field(default_factory=dict)  # lang.value → last tick used

    # Internet portal mission state.
    web_mission_until: int = 0
    web_source: str = ""
    web_last_report_tick: int = 0
    web_reports: int = 0

    # Persona / long-term memory layer (see core/soul.py).
    # None for ordinary entities; set when a Soul is granted.
    soul_id: Optional[str] = None

    def remember(self, tick: int, event: str, other_id: Optional[int] = None, value: float = 0.0):
        self.memories.append(Memory(tick, event, other_id, value))
        if len(self.memories) > self.max_memories:
            self.memories.pop(0)

    def get_relationship(self, other_id: int) -> float:
        return self.relationships.get(other_id, 0.0)

    def update_relationship(self, other_id: int, delta: float):
        cur = self.relationships.get(other_id, 0.0)
        self.relationships[other_id] = max(-1.0, min(1.0, cur + delta))

    @property
    def color(self) -> tuple:
        base = TYPE_COLORS[self.entity_type]
        f = 0.3 + 0.7 * self.energy
        fa = int(80 * self.flash)
        return (
            min(255, int(base[0] * f) + fa),
            min(255, int(base[1] * f) + fa),
            min(255, int(base[2] * f) + fa),
        )

    @property
    def radius(self) -> int:
        return max(2, int(ENTITY_RADIUS * (0.5 + 0.8 * self.energy)))

    @property
    def is_predator(self) -> bool:
        """AI Copilot — the only 'Predator' (catches bugs)."""
        return self.entity_type == EntityType.AI_COPILOT

    @property
    def is_bug_scanner(self) -> bool:
        """Bug — scans code, finds bugs, reports to developer."""
        return self.entity_type == EntityType.BUG

    @property
    def is_prey(self) -> bool:
        """Bug = AI Copilot's prey (copilot catches bugs)."""
        return self.entity_type == EntityType.BUG

    @property
    def is_decomposer(self) -> bool:
        return self.entity_type == EntityType.REFACTORER

    @property
    def can_mate(self) -> bool:
        """Can create features/new developers."""
        if not self.alive or self.mate_cooldown > 0:
            return False
        if self.entity_type == EntityType.BUG:
            return self.energy > PREDATOR_MATE_ENERGY and self.age > BUG_MIN_AGE_TO_SPREAD
        if self.entity_type == EntityType.WEB_SCOUT:
            return False
        return self.energy > DEV_MIN_ENERGY_TO_CODE and self.age > DEV_MIN_AGE_TO_REPRODUCE

    @property
    def can_code(self) -> bool:
        """Can write code — must know a language."""
        return (self.alive and
                len(self.languages_known) > 0 and
                self.entity_type in (EntityType.DEVELOPER, EntityType.AI_COPILOT,
                                     EntityType.SENIOR_DEV, EntityType.INTERN,
                                     EntityType.WEB_SCOUT))

    @property
    def primary_language(self) -> Optional[CodeLanguage]:
        """Primary programming language."""
        if self.languages_known:
            return self.languages_known[0]
        return None
