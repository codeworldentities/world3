"""Enums — all types for the code world."""

from enum import Enum


class EntityType(Enum):
    """Entity types."""
    DEVELOPER = "Developer"
    BUG = "Bug"
    REFACTORER = "Refactorer"
    AI_COPILOT = "AI Copilot"
    SENIOR_DEV = "Senior"
    INTERN = "Intern"
    # New roles (Phase 7C — mentoring/judgement)
    TEACHER = "Teacher"   # teaches languages, boosts XP of nearby devs
    JUDGE = "Judge"       # rewards good commits, penalises buggy ones
    WEB_SCOUT = "Web Scout"  # internet researcher / portal explorer


class ResourceType(Enum):
    """Resource types."""
    DOCUMENTATION = "Documentation"
    LIBRARY = "Library"
    BOILERPLATE = "Boilerplate"
    FRAMEWORK = "Framework"
    COFFEE = "Coffee"


class BiomeType(Enum):
    """Code domains (biomes)."""
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    DATABASE = "Database"
    DEVOPS = "DevOps"
    CLOUD = "Cloud"


class SignalType(Enum):
    """Signals."""
    BUG_ALERT = "Bug_Found"
    CODE_REVIEW = "Code_Review"
    HELP_NEEDED = "Help_Needed"
    COFFEE_FOUND = "Coffee_Found"
    PAIR_PROGRAM = "Pair_Program"
    DEPLOY_READY = "Deploy_Ready"


class Gender(Enum):
    """Specialization."""
    FRONTEND_SPEC = "Frontend_Spec"
    BACKEND_SPEC = "Backend_Spec"


class Instinct(Enum):
    """Instincts / motivations."""
    CODE = "Coding"
    DEBUG = "Debug"
    REFACTOR = "Refactoring"
    LEARN = "Learn"
    COLLABORATE = "Collaboration"
    DEPLOY = "Deploy"


class Role(Enum):
    """Roles in the project."""
    NONE = "Freelancer"
    TEAM_LEAD = "Team Lead"
    REVIEWER = "Reviewer"
    ARCHITECT = "Architect"
    TESTER = "Tester"
    DEVOPS_ENG = "DevOps Engineer"


class TechType(Enum):
    """Project technologies."""
    GIT = "Git"
    DOCKER = "Docker"
    CI_CD = "CI/CD"
    KUBERNETES = "Kubernetes"
    MONITORING = "Monitoring"
    MICROSERVICES = "Microservices"


class CraftableType(Enum):
    """Craftable tools."""
    UNIT_TEST = "Unit_Test"
    INTEGRATION_TEST = "Integration_Test"
    CI_PIPELINE = "CI_Pipeline"
    LINTER = "Linter"


class KnowledgeType(Enum):
    """Programming knowledge."""
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    RUST = "Rust"
    GO = "Go"
    SQL = "SQL"
    REACT = "React"
    NODEJS = "Node.js"
    MACHINE_LEARNING = "ML"
    SECURITY = "Security"
    TESTING = "Testing"
    TYPESCRIPT = "TypeScript"
    ALGORITHMS = "Algorithms"


class DiplomacyState(Enum):
    """Inter-project relationship."""
    NEUTRAL = "Neutral"
    ALLIED = "Allied"
    HOSTILE = "Hostile"
    FORKED = "Forked"
    MERGED = "Merged"
    OPEN_SOURCE = "Open_Source"


class CodeLanguage(Enum):
    """Languages that entities write code in."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    RUST = "rust"
    GO = "go"
    HTML_CSS = "html_css"
    SQL = "sql"


class ProjectPhase(Enum):
    """Project phases."""
    ARCHITECTURE = "architecture"      # Planning file structure
    DEVELOPMENT = "development"       # Writing code
    REVIEW = "review"                   # Team meeting, analysis, bug-fix
    PUSH = "push"                      # Upload to GitHub
