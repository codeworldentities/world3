"""Configuration — all parameters for the code world.

Secrets (Neo4j password, GitHub token, API keys) are read from environment
variables. See .env.example. A .env file in the project root is loaded
automatically if python-dotenv is installed.
"""

import os

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


def _env(name: str, default: str = "") -> str:
    val = os.environ.get(name)
    return val if val is not None else default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


from core.enums import (
    EntityType, Instinct, TechType, KnowledgeType,
    ResourceType, CraftableType, Role, BiomeType, CodeLanguage,
)

# ================== world size ==================

WORLD_WIDTH = 6000
WORLD_HEIGHT = 4000

# ================== Simulation ==================

INITIAL_ENTITY_COUNT = 350
MAX_ENTITIES = 1200
MIN_ENTITIES = 100

ENTITY_RADIUS = 3
INTERACTION_RADIUS = 40
VISION_RADIUS = 90

INITIAL_RESOURCE_COUNT = 250
MAX_RESOURCES = 600
RESOURCE_SPAWN_RATE = 0.04
RESOURCE_ENERGY = 0.25

TERRITORY_RADIUS = 80
DAY_LENGTH = 600  # 1 Sprint
MAX_SIGNALS = 60

BIOME_CELL = 50
BIOME_COLS = WORLD_WIDTH // BIOME_CELL
BIOME_ROWS = WORLD_HEIGHT // BIOME_CELL

# ================== Neo4j ==================

NEO4J_URI = _env("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "")
NEO4J_DB = _env("NEO4J_DB", "neo4j")
GRAPH_SYNC_INTERVAL = 50

# ================== Ecosystem Balance ==================

BUG_ENERGY_MULT = 1.35  # Bugs consume more energy
DEV_COFFEE_ENERGY = 0.25  # coffee energy
DEV_MIN_ENERGY_TO_CODE = 0.25
DEV_MIN_AGE_TO_REPRODUCE = 100
BUG_MIN_AGE_TO_SPREAD = 180
MAX_BUG_RATIO = 0.30
FEATURE_CHANCE = 0.025  # new feature/developer creation probability
BUG_STEAL_ENERGY = 0.18
BUG_DAMAGE_MULT = 1.2
COOLDOWN_AFTER_FEATURE = 80  # frontend spec
COOLDOWN_AFTER_REVIEW = 40   # backend spec
DEV_FLEE_SPEED_BONUS = 1.3  # Intern fleeing from Bug
BUG_OVERPOP_DRAIN = 0.001
AUTOSAVE_INTERVAL = 3000

# Internet portal exploration (Web Scout race)
INITIAL_WEB_SCOUT_COUNT = 4
INTERNET_PORTAL_COUNT = 6
INTERNET_PORTAL_RADIUS = 34
INTERNET_MISSION_MIN_TICKS = 80
INTERNET_MISSION_MAX_TICKS = 220
INTERNET_REPORT_COOLDOWN = 120
INTERNET_BOOST_QUALITY = 0.03
INTERNET_BUGFIX_CHANCE = 0.45
INTERNET_KNOWLEDGE_SHARE_CHANCE = 0.35
INTERNET_OPEN_SOURCE_BOOST = 0.012

# Lifecycle turnover — helps avoid immortal populations in long runs.
RETIREMENT_AGE_START = 2200
RETIREMENT_AGE_PEAK = 5200
RETIREMENT_BASE_CHANCE = 0.0002
BUG_MAX_AGE_START = 1400

# Advanced lifecycle tuning.
SENIOR_MENTOR_RADIUS = 100.0
SENIOR_XP_TRANSFER = 0.8
SENIOR_TRAIT_BOOST = 0.004
SENIOR_MENTOR_CHANCE = 0.25

BURNOUT_ENERGY_THRESHOLD = 0.06
BURNOUT_RECOVERY_TICKS = 150
BURNOUT_REGEN_RATE = 0.003

REP_GOOD_CODE = 0.008
REP_BAD_CODE = -0.012
REP_JUDGE_REWARD = 0.015
REP_JUDGE_PENALTY = -0.020
REP_DECAY_RATE = 0.0001

SKILL_DECAY_INTERVAL = 200
SKILL_DECAY_UNUSED_AFTER = 500
SKILL_DECAY_RATE = 0.15
SKILL_FORGET_THRESHOLD = 0.3

TEAM_MEMORY_QUALITY_BONUS = 0.05
TEAM_MEMORY_MAX = 20

PERSONALITY_SHIFT_RATE = 0.002

CASCADE_BUG_QUALITY_THRESHOLD = 0.20
CASCADE_SPREAD_CHANCE = 0.10
CASCADE_MAX_SPREAD = 3

MIGRATION_REPUTATION_THRESHOLD = 0.75
MIGRATION_ENERGY_THRESHOLD = 0.6
MIGRATION_CHANCE = 0.008

# ================== Soul memory compression (Phase 7) ==================
# DeerFlow + DeepTutor + Hermes patterns, 100% local (Ollama only).
# When a Soul's memory list grows past the threshold, the oldest half is
# summarised into a single "reflection" SoulMemory via the local LLM. Top-K
# by importance weight are kept verbatim. This bounds per-soul memory to
# KEEP_RECENT + KEEP_IMPORTANT + 1 reflection, enabling unbounded simulation
# lifetime without token / RAM growth.
SOUL_MEMORY_COMPRESSION_THRESHOLD = 40    # compress when len(memory) > this
SOUL_MEMORY_KEEP_RECENT = 10              # preserve N most recent verbatim
SOUL_MEMORY_KEEP_IMPORTANT = 5            # preserve top-K by weight verbatim
SOUL_REFLECTION_INTERVAL = 500            # ticks between reflection refresh
SOUL_PROFILE_UPDATE_INTERVAL = 2000       # ticks between profile refresh
SOUL_COMPRESSION_ENABLED = True           # master switch (disable for tests)
SOUL_COMPRESSION_CHECK_INTERVAL = 200     # how often to scan souls for compression
SOUL_SKILLS_MAX = 20                      # cap per soul

# ================== GitHub ==================

GITHUB_TOKEN = _env("GITHUB_TOKEN", "")
GITHUB_PUSH_COOLDOWN = 50  # minimum 50 ticks between pushes

# ================== API / CORS ==================

API_CORS_ORIGINS = _env_list(
    "API_CORS_ORIGINS",
    ["http://localhost:3000", "http://localhost:5173"],
)

# ================== Tier / Quotas ==================
# Used by feature gating when the project is run as a hosted SaaS.
# Defaults are the "free" tier. Set WORLD3_TIER=pro to unlock higher caps.

WORLD3_TIER = _env("WORLD3_TIER", "free").lower()
_TIER_QUOTAS = {
    "free": {"max_souls": 5,  "max_github_pushes_per_day": 3,  "dialog_enabled": True},
    "pro":  {"max_souls": 50, "max_github_pushes_per_day": 50, "dialog_enabled": True},
    "enterprise": {"max_souls": 500, "max_github_pushes_per_day": 10000, "dialog_enabled": True},
}
TIER_QUOTAS = _TIER_QUOTAS.get(WORLD3_TIER, _TIER_QUOTAS["free"])
MAX_SOULS = int(_env("MAX_SOULS", str(TIER_QUOTAS["max_souls"])))
MAX_GITHUB_PUSHES_PER_DAY = int(_env(
    "MAX_GITHUB_PUSHES_PER_DAY",
    str(TIER_QUOTAS["max_github_pushes_per_day"]),
))

# ================== Instinct Weights ==================

INSTINCT_WEIGHTS = {
    EntityType.DEVELOPER: {
        Instinct.CODE: 0.9, Instinct.DEBUG: 0.5, Instinct.LEARN: 0.8,
        Instinct.COLLABORATE: 0.6, Instinct.DEPLOY: 0.4, Instinct.REFACTOR: 0.3,
    },
    EntityType.BUG: {
        Instinct.CODE: 0.0, Instinct.DEBUG: 0.1, Instinct.LEARN: 0.0,
        Instinct.COLLABORATE: 0.1, Instinct.DEPLOY: 0.0, Instinct.REFACTOR: 0.0,
    },
    EntityType.REFACTORER: {
        Instinct.CODE: 0.3, Instinct.DEBUG: 0.4, Instinct.LEARN: 0.5,
        Instinct.COLLABORATE: 0.2, Instinct.DEPLOY: 0.3, Instinct.REFACTOR: 0.9,
    },
    EntityType.AI_COPILOT: {
        Instinct.CODE: 0.85, Instinct.DEBUG: 0.7, Instinct.LEARN: 0.55,
        Instinct.COLLABORATE: 0.5, Instinct.DEPLOY: 0.4, Instinct.REFACTOR: 0.6,
    },
    EntityType.SENIOR_DEV: {
        Instinct.CODE: 0.7, Instinct.DEBUG: 0.8, Instinct.LEARN: 0.5,
        Instinct.COLLABORATE: 0.9, Instinct.DEPLOY: 0.7, Instinct.REFACTOR: 0.6,
    },
    EntityType.INTERN: {
        Instinct.CODE: 0.6, Instinct.DEBUG: 0.2, Instinct.LEARN: 0.95,
        Instinct.COLLABORATE: 0.7, Instinct.DEPLOY: 0.1, Instinct.REFACTOR: 0.1,
    },
    EntityType.TEACHER: {
        Instinct.CODE: 0.2, Instinct.DEBUG: 0.2, Instinct.LEARN: 0.5,
        Instinct.COLLABORATE: 0.95, Instinct.DEPLOY: 0.1, Instinct.REFACTOR: 0.3,
    },
    EntityType.JUDGE: {
        Instinct.CODE: 0.1, Instinct.DEBUG: 0.7, Instinct.LEARN: 0.3,
        Instinct.COLLABORATE: 0.6, Instinct.DEPLOY: 0.2, Instinct.REFACTOR: 0.4,
    },
    EntityType.WEB_SCOUT: {
        Instinct.CODE: 0.75, Instinct.DEBUG: 0.55, Instinct.LEARN: 0.95,
        Instinct.COLLABORATE: 0.65, Instinct.DEPLOY: 0.35, Instinct.REFACTOR: 0.35,
    },
}

# ================== Domain Properties ==================
# (resource_chance, energy_cost_mult, speed_mult, doc_ratio, lib_ratio, boilerplate_ratio, framework_ratio)

BIOME_PROPS = {
    BiomeType.FRONTEND: (1.2, 0.9, 1.0, 0.30, 0.25, 0.25, 0.15),
    BiomeType.BACKEND:  (1.0, 1.0, 0.9, 0.35, 0.30, 0.15, 0.15),
    BiomeType.DATABASE:  (0.8, 1.1, 0.8, 0.40, 0.15, 0.10, 0.25),
    BiomeType.DEVOPS:   (0.6, 1.3, 1.1, 0.25, 0.10, 0.15, 0.40),
    BiomeType.CLOUD:    (0.5, 1.4, 1.2, 0.20, 0.20, 0.10, 0.40),
}

# ================== Technology Tree ==================

TECH_TREE = {
    TechType.GIT:            (3, 300,  None,              0.0003),
    TechType.DOCKER:         (4, 500,  None,              0.0002),
    TechType.CI_CD:          (5, 400,  TechType.GIT,      0.00025),
    TechType.KUBERNETES:     (7, 600,  TechType.DOCKER,   0.00015),
    TechType.MONITORING:     (6, 500,  TechType.CI_CD,    0.0002),
    TechType.MICROSERVICES:  (5, 400,  TechType.DOCKER,   0.00018),
}

TECH_BONUSES = {
    TechType.GIT:            (0.15, 0.0, 0.0,  0.1, 1.0),
    TechType.DOCKER:         (0.0,  0.0, 0.2,  0.0, 1.2),
    TechType.CI_CD:          (0.1,  0.0, 0.0,  0.2, 1.0),
    TechType.KUBERNETES:     (0.2,  0.0, 0.0,  0.0, 1.8),
    TechType.MONITORING:     (0.1,  0.0, 0.0,  0.0, 1.3),
    TechType.MICROSERVICES:  (0.0,  0.1, 0.35, 0.15, 1.0),
}

ROLE_BONUSES = {
    Role.NONE:       (1.0, 1.0, 1.0, 1.0),
    Role.TEAM_LEAD:  (1.3, 0.8, 1.0, 1.2),
    Role.REVIEWER:   (0.7, 1.6, 0.8, 1.0),
    Role.ARCHITECT:  (1.0, 0.8, 1.8, 0.9),
    Role.TESTER:     (0.8, 1.0, 1.0, 1.5),
    Role.DEVOPS_ENG: (0.6, 0.8, 0.9, 1.0),
}

# ================== Knowledge Tree (Languages & Frameworks) ==================

KNOWLEDGE_TREE = {
    KnowledgeType.PYTHON:          (3, 200, None, 0.0008),
    KnowledgeType.JAVASCRIPT:      (3, 200, None, 0.0008),
    KnowledgeType.SQL:             (3, 300, None, 0.0006),
    KnowledgeType.REACT:           (4, 400, KnowledgeType.JAVASCRIPT, 0.0005),
    KnowledgeType.NODEJS:          (4, 400, KnowledgeType.JAVASCRIPT, 0.0005),
    KnowledgeType.TYPESCRIPT:      (4, 350, KnowledgeType.JAVASCRIPT, 0.0006),
    KnowledgeType.RUST:            (5, 600, None, 0.0003),
    KnowledgeType.GO:              (4, 500, None, 0.0004),
    KnowledgeType.MACHINE_LEARNING:(5, 700, KnowledgeType.PYTHON, 0.0002),
    KnowledgeType.SECURITY:        (5, 500, None, 0.0003),
    KnowledgeType.TESTING:         (3, 300, None, 0.0006),
    KnowledgeType.ALGORITHMS:      (4, 400, None, 0.0005),
}

KNOWLEDGE_EFFECTS = {
    KnowledgeType.PYTHON:           {"code_speed_mult": 1.3, "can_code": True},
    KnowledgeType.JAVASCRIPT:       {"code_speed_mult": 1.2, "can_code": True},
    KnowledgeType.SQL:              {"data_access_mult": 1.5},
    KnowledgeType.REACT:            {"frontend_mult": 1.4},
    KnowledgeType.NODEJS:           {"backend_mult": 1.3},
    KnowledgeType.TYPESCRIPT:       {"code_quality_mult": 1.3},
    KnowledgeType.RUST:             {"performance_mult": 1.5, "bug_resist": 0.3},
    KnowledgeType.GO:               {"deploy_speed_mult": 1.4},
    KnowledgeType.MACHINE_LEARNING: {"ai_bonus": 1.5},
    KnowledgeType.SECURITY:         {"bug_resist": 0.4, "defense_mult": 1.5},
    KnowledgeType.TESTING:          {"bug_detect_mult": 1.4, "code_quality_mult": 1.2},
    KnowledgeType.ALGORITHMS:       {"code_speed_mult": 1.2, "performance_mult": 1.3},
}

KNOWLEDGE_DISCOVERY_INTERVAL = 200
KNOWLEDGE_DISCOVERY_CHANCE = 0.001
KNOWLEDGE_MIN_GROUP_SIZE = 3
KNOWLEDGE_MIN_RESOURCES = 2
KNOWLEDGE_LLM_DISCOVERY = True
KNOWLEDGE_INHERIT_CHANCE = 0.4

# ================== Tool Recipes ==================

CRAFT_RECIPES = {
    CraftableType.UNIT_TEST:        {ResourceType.DOCUMENTATION: 2, ResourceType.LIBRARY: 1},
    CraftableType.INTEGRATION_TEST: {ResourceType.DOCUMENTATION: 3, ResourceType.FRAMEWORK: 2},
    CraftableType.CI_PIPELINE:      {ResourceType.BOILERPLATE: 3, ResourceType.FRAMEWORK: 2},
    CraftableType.LINTER:           {ResourceType.DOCUMENTATION: 2, ResourceType.BOILERPLATE: 1},
}

CRAFT_BONUSES = {
    CraftableType.UNIT_TEST:        (0.2, 0.25, 0.0),   # defense, bug_detect, energy_save
    CraftableType.INTEGRATION_TEST: (0.3, 0.20, 0.0),
    CraftableType.CI_PIPELINE:      (0.1, 0.0,  0.2),
    CraftableType.LINTER:           (0.0, 0.15, 0.1),
}

# ================== Project (Settlement) ==================

PROJECT_MIN_TEAM_SIZE = 4
PROJECT_MIN_TICKS_TOGETHER = 200
PROJECT_RADIUS = 180
PROJECT_RESOURCE_BOOST = 1.6
PROJECT_MAX_TEAM = 25

# ================== Code Sharing (Trade) ==================

SHARE_MIN_PROJECT_AGE = 500
SHARE_MAX_DISTANCE = 2000
SHARE_INTERVAL = 150
SHARE_RESOURCE_AMOUNT = 0.3
SHARE_RELATION_BOOST = 0.05
SHARE_TECH_SPREAD_CHANCE = 0.002

# ================== Merge Conflict (War) ==================

CONFLICT_TERRITORY_OVERLAP = 250
CONFLICT_AGGRESSION_THRESHOLD = 0.55
CONFLICT_DURATION_TICKS = 300
CONFLICT_CASUALTY_CHANCE = 0.003
CONFLICT_ENERGY_DRAIN = 0.001
CONFLICT_VICTORY_LOOT = 0.5
CONFLICT_COOLDOWN = 800
DIPLOMACY_DECAY = 0.001

# ================== Team Lead ==================

LEAD_MIN_AGE = 600
LEAD_ELECTION_INTERVAL = 500
LEAD_INFLUENCE_RADIUS = 200
LEAD_ENERGY_BONUS = 0.05
LEAD_MORALE_BONUS = 0.1

# ================== Code Generation (new!) ==================

CODE_GEN_INTERVAL = 50         # tries to write code every 50 ticks
CODE_GEN_MIN_ENERGY = 0.12     # min energy for coding
CODE_GEN_MIN_KNOWLEDGE = 1     # must know at least 1 language
CODE_QUALITY_BASE = 0.5
CODE_BUG_CORRUPT_CHANCE = 0.15 # chance of Bug corrupting code
CODE_REVIEW_QUALITY_BOOST = 0.2
CODE_MAX_PER_PROJECT = 40      # max code files per project
CODE_OUTPUT_DIR = "output"

# language to file extension mapping
LANG_EXTENSIONS = {
    CodeLanguage.PYTHON: ".py",
    CodeLanguage.JAVASCRIPT: ".js",
    CodeLanguage.RUST: ".rs",
    CodeLanguage.GO: ".go",
    CodeLanguage.HTML_CSS: ".html",
    CodeLanguage.SQL: ".sql",
}

# knowledge to language mapping
KNOWLEDGE_TO_LANG = {
    KnowledgeType.PYTHON: CodeLanguage.PYTHON,
    KnowledgeType.JAVASCRIPT: CodeLanguage.JAVASCRIPT,
    KnowledgeType.REACT: CodeLanguage.JAVASCRIPT,
    KnowledgeType.NODEJS: CodeLanguage.JAVASCRIPT,
    KnowledgeType.TYPESCRIPT: CodeLanguage.JAVASCRIPT,
    KnowledgeType.RUST: CodeLanguage.RUST,
    KnowledgeType.GO: CodeLanguage.GO,
    KnowledgeType.SQL: CodeLanguage.SQL,
}

# ================== LLM ==================

LLM_ENABLED = True
LLM_PROVIDER = "ollama"
LLM_MODEL = _env("LLM_MODEL", "llama3.2:3b")
LLM_BASE_URL = _env("LLM_BASE_URL", "http://localhost:11434")
LLM_TIMEOUT = 8
LLM_MAX_QUEUE = 20
LLM_CALLS_PER_STEP = 2
LLM_THINK_INTERVAL = 200
LLM_LEAD_INTERVAL = 400
LLM_CONVO_INTERVAL = 300
LLM_CONVO_RADIUS = 120
LLM_CONVO_COOLDOWN = 1200
LLM_CONVO_LANGUAGE = "english"
LLM_CACHE_SIZE = 128
LLM_MAX_TOKENS = 120
LLM_TEMPERATURE = 0.7
LLM_THOUGHT_DISPLAY_TICKS = 300
LLM_DIALOGUE_RADIUS = 150

BRAIN_LEVEL_NONE = 0
BRAIN_LEVEL_BASIC = 1
BRAIN_LEVEL_LEAD = 2
BRAIN_LEVEL_WILD = 1

# ================== LLM Validator ==================

LLM_VALIDATOR_ENABLED = True
FAKE_GEORGIAN_PATTERNS = [
    "ჰალო", "ჰატ", "ბრო", "ოკეი", "ბაი",
]
CANON_FORBIDDEN_WORDS = [
    "car", "phone", "gun",
    "მანქანა", "ტელეფონი", "იარაღი",
]

# ================== Kimi (disabled) ==================

KIMI_ENABLED = False
KIMI_API_KEY = _env("KIMI_API_KEY", "")
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_MODEL = "kimi-k2.5"
KIMI_MAX_TOKENS = 150
KIMI_TEMPERATURE = 0.6

# ============ Aliases (world2 compatibility) ============

# survival.py and others use these aliases
PREDATOR_ENERGY_MULT = BUG_ENERGY_MULT
WAR_ENERGY_DRAIN = CONFLICT_ENERGY_DRAIN
LEADER_ENERGY_BONUS = LEAD_ENERGY_BONUS
MATE_CHANCE = FEATURE_CHANCE
HUNT_STEAL_ENERGY = BUG_STEAL_ENERGY
HUNT_DAMAGE_MULT = BUG_DAMAGE_MULT
MATE_COOLDOWN_FEMALE = COOLDOWN_AFTER_FEATURE
MATE_COOLDOWN_MALE = COOLDOWN_AFTER_REVIEW
HERBIVORE_FLEE_SPEED_BONUS = DEV_FLEE_SPEED_BONUS
PREDATOR_OVERPOP_DRAIN = BUG_OVERPOP_DRAIN
MAX_PREDATOR_RATIO = MAX_BUG_RATIO
HERBIVORE_MATE_ENERGY = DEV_MIN_ENERGY_TO_CODE
HERBIVORE_MATE_AGE = DEV_MIN_AGE_TO_REPRODUCE
PREDATOR_MATE_ENERGY = 0.4
PREDATOR_MATE_AGE = BUG_MIN_AGE_TO_SPREAD
SETTLEMENT_MIN_GROUP_SIZE = PROJECT_MIN_TEAM_SIZE
SETTLEMENT_MIN_TICKS_TOGETHER = PROJECT_MIN_TICKS_TOGETHER
SETTLEMENT_RADIUS = PROJECT_RADIUS
SETTLEMENT_RESOURCE_BOOST = PROJECT_RESOURCE_BOOST
SETTLEMENT_MAX_POP = PROJECT_MAX_TEAM
TRADE_MIN_SETTLEMENT_AGE = SHARE_MIN_PROJECT_AGE
TRADE_MAX_DISTANCE = SHARE_MAX_DISTANCE
TRADE_INTERVAL = SHARE_INTERVAL
TRADE_RESOURCE_AMOUNT = SHARE_RESOURCE_AMOUNT
TRADE_RELATION_BOOST = SHARE_RELATION_BOOST
TRADE_TECH_SPREAD_CHANCE = SHARE_TECH_SPREAD_CHANCE
WAR_TERRITORY_OVERLAP_RADIUS = CONFLICT_TERRITORY_OVERLAP
WAR_AGGRESSION_THRESHOLD = CONFLICT_AGGRESSION_THRESHOLD
WAR_DURATION_TICKS = CONFLICT_DURATION_TICKS
WAR_CASUALTY_CHANCE = CONFLICT_CASUALTY_CHANCE
WAR_VICTORY_RESOURCE_LOOT = CONFLICT_VICTORY_LOOT
WAR_PEACE_COOLDOWN = CONFLICT_COOLDOWN
DIPLOMACY_RELATION_DECAY = DIPLOMACY_DECAY
LEADER_MIN_AGE = LEAD_MIN_AGE
LEADER_ELECTION_INTERVAL = LEAD_ELECTION_INTERVAL
LEADER_INFLUENCE_RADIUS = LEAD_INFLUENCE_RADIUS
LEADER_MORALE_BONUS = LEAD_MORALE_BONUS
