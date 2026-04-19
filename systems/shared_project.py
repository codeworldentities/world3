"""Shared Project — all developers work on one project.

Flow:
1. ARCHITECTURE Phase — Architect creates file structure, team gathers
2. DEVELOPMENT Phase — devs write code following the structure
3. REVIEW Phase — team meeting, bug analysis and fixing
4. PUSH — upload to GitHub
"""

from __future__ import annotations
import math
import random
import logging
from typing import TYPE_CHECKING, Optional

from core.enums import CodeLanguage, Role, EntityType, ProjectPhase
from core.models import Settlement
from config import CODE_MAX_PER_PROJECT, PROJECT_RADIUS, WORLD_WIDTH, WORLD_HEIGHT

if TYPE_CHECKING:
    from core.world import World

log = logging.getLogger("shared_project")

# project names — more diverse
_PROJECT_NAMES = [
    "CodeForge", "ByteFlow", "PixelStack", "DataPulse", "CloudNest",
    "NodeHive", "GitStream", "DevPulse", "BitForge", "LogicHub",
    "StackBridge", "HexGrid", "FlowEngine", "NeuralKit", "PipeWorks",
    "RustBlade", "PyForge", "GoRunner", "ReactPulse", "SqlVault",
    "MeshOps", "LintMaster", "TestPilot", "DocuGen", "APICraft",
    "CipherNet", "QuantumRun", "VectorDB", "StreamLine", "CacheFlow",
    "LazyLoad", "DeepSync", "FastRoute", "CoreDump", "AlgoSmith",
    "ByteCraft", "NexusAPI", "TerminalX", "ShellForge", "ProtoGen",
]

# which project names we already used
_used_names: set[str] = set()

# completed projects history: [{name, github_url, tick_started, tick_finished, files_count}]
completed_projects: list[dict] = []

# user-requested projects queue
# [{name, description, tech_stack: [str], max_files: int}]
_requested_projects: list[dict] = []


def queue_project(name: str, description: str = "",
                  tech_stack: list[str] = None, max_files: int = 0) -> dict:
    """Add user-requested project to queue."""
    proj = {
        "name": name,
        "description": description or "",
        "tech_stack": tech_stack or [],
        "max_files": max_files or random.randint(15, 50),
    }
    _requested_projects.append(proj)
    return proj


def get_project_queue() -> list[dict]:
    """Queue of requested projects."""
    return list(_requested_projects)


def get_active_project(world: World) -> Optional[Settlement]:
    """Get active project."""
    return getattr(world, '_active_project', None)


def get_completed_projects() -> list[dict]:
    """List of completed projects."""
    return completed_projects


def ensure_active_project(world: World):
    """Ensure active project exists, or create a new one."""
    if getattr(world, '_active_project', None) is not None:
        proj = world._active_project
        phase = proj.phase

        if phase == "architecture":
            _architecture_phase(world, proj)
            return

        elif phase == "development":
            target = proj.max_files or CODE_MAX_PER_PROJECT
            if len(proj.codebase) >= target:
                # transition to Review Phase
                proj.phase = "review"
                proj.phase_tick = world.tick
                proj.review_rounds = 0
                world.log_event(
                    f"📋 '{proj.project_name}' — REVIEW Phase started! "
                    f"Team gathers for project analysis...")
                world.spawn_particles(proj.x, proj.y, (255, 200, 50), count=20, speed=3.0, size=2.5)
            return

        elif phase == "review":
            _review_phase(world, proj)
            return

        elif phase == "push":
            _complete_project(world)
            # new project is created below
        else:
            return

    _start_new_project(world)


def _pick_project_name(sid: int) -> str:
    """Pick a unique project name."""
    available = [n for n in _PROJECT_NAMES if n not in _used_names]
    if not available:
        _used_names.clear()
        available = list(_PROJECT_NAMES)
    name = random.choice(available)
    _used_names.add(name)
    return f"{name}-{sid}"


def _start_new_project(world: World):
    """Start a new shared project."""

    # team center calculation — average position of all alive devs
    devs = [e for e in world.entities
            if e.alive and e.can_code and e.entity_type != EntityType.BUG]
    if not devs:
        return

    # Place project at a spread-out position, not the exact centroid —
    # this prevents all projects from collapsing to the same center
    cx = sum(e.x for e in devs) / len(devs)
    cy = sum(e.y for e in devs) / len(devs)
    # Add significant offset so successive projects don't overlap
    cx += random.uniform(-400, 400)
    cy += random.uniform(-300, 300)
    cx = max(100, min(WORLD_WIDTH - 100, cx))
    cy = max(100, min(WORLD_HEIGHT - 100, cy))

    sid = world.next_settlement_id
    world.next_settlement_id += 1

    # check for requested project (from queue)
    requested = None
    if _requested_projects:
        requested = _requested_projects.pop(0)

    if requested:
        project_name = requested["name"]
        _used_names.add(project_name.split("-")[0] if "-" in project_name else project_name)
    else:
        project_name = _pick_project_name(sid)

    # Tech stack — aggregated from all devs' languages
    lang_counts: dict[CodeLanguage, int] = {}
    for e in devs:
        for lang in e.languages_known:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    if requested and requested.get("tech_stack"):
        # user-specified tech stack
        lang_map = {l.value: l for l in CodeLanguage}
        tech_stack = [lang_map[t] for t in requested["tech_stack"] if t in lang_map]
        if not tech_stack:
            tech_stack = sorted(lang_counts, key=lang_counts.get, reverse=True)[:4]
    else:
        tech_stack = sorted(lang_counts, key=lang_counts.get, reverse=True)[:4]

    sett = Settlement(
        id=sid, group_id=-1, x=cx, y=cy,
        radius=PROJECT_RADIUS,
        founded_tick=world.tick,
        population=len(devs),
        project_name=project_name,
        tech_stack=tech_stack,
    )

    # Project size
    sett.max_files = (requested["max_files"] if requested else random.randint(15, 50))
    # Description (for user request)
    sett.description = requested["description"] if requested else ""
    # Architecture phase — file structure planning
    sett.phase = "architecture"
    sett.phase_tick = world.tick
    sett.file_structure = _plan_file_structure(tech_stack, sett.max_files)

    world.settlements[sid] = sett
    world.total_settlements += 1
    world._active_project = sett
    world._active_project_id = sid

    # Assign all devs to this project and scatter them around the center
    spread = max(PROJECT_RADIUS * 2, 200)
    for e in devs:
        e.settlement_id = sid
        # Scatter entities around the project center instead of clustering
        angle = random.uniform(0, 2 * 3.14159)
        dist = random.uniform(30, spread)
        e.x = max(20, min(WORLD_WIDTH - 20, cx + dist * math.cos(angle)))
        e.y = max(20, min(WORLD_HEIGHT - 20, cy + dist * math.sin(angle)))

    # Distribute roles
    _assign_work_division(world, sett, devs)

    project_num = len(completed_projects) + 1
    custom_tag = " (requested)" if requested else ""
    world.log_event(
        f"🚀 New Project #{project_num}: '{project_name}'{custom_tag} — Architecture Phase! "
        f"({len(devs)} Developer, {sett.max_files} files planned, "
        f"tech: {', '.join(l.value for l in tech_stack[:3])})"
    )
    world.spawn_particles(cx, cy, (80, 200, 255), count=30, speed=4.0, size=3.0)

    log.info(f"New shared project: {project_name} with {len(devs)} devs, phase=architecture")


def _assign_work_division(world: World, sett: Settlement, devs: list):
    """Distribute work by roles.
    
    - ARCHITECT: system architecture, structure
    - REVIEWER: code quality, tests
    - TESTER: unit tests, bug finding
    - DEVOPS_ENG: CI/CD, configuration
    - TEAM_LEAD: coordination
    - All others: features
    """
    random.shuffle(devs)
    n = len(devs)
    
    # required roles count
    n_reviewers = max(1, n // 6)
    n_architects = max(1, n // 8)
    n_testers = max(1, n // 6)
    n_devops = max(1, n // 10)
    n_leads = max(1, n // 12)
    
    assigned = 0
    for e in devs:
        e.settlement_id = sett.id
        if e.entity_type == EntityType.SENIOR_DEV:
            e.role = Role.TEAM_LEAD
            continue
        if e.entity_type == EntityType.AI_COPILOT:
            e.role = Role.ARCHITECT
            continue
        if e.entity_type == EntityType.INTERN:
            e.role = Role.TESTER
            continue
            
        # for the rest — rotation
        if assigned < n_leads:
            e.role = Role.TEAM_LEAD
        elif assigned < n_leads + n_architects:
            e.role = Role.ARCHITECT
        elif assigned < n_leads + n_architects + n_reviewers:
            e.role = Role.REVIEWER
        elif assigned < n_leads + n_architects + n_reviewers + n_testers:
            e.role = Role.TESTER
        elif assigned < n_leads + n_architects + n_reviewers + n_testers + n_devops:
            e.role = Role.DEVOPS_ENG
        else:
            e.role = Role.NONE  # freelancer — feature developer
        assigned += 1


# ─── File Structure Generation ────────────────────────────────────

# Typical folders/files for each language
_STRUCTURE_TEMPLATES = {
    CodeLanguage.PYTHON: [
        "src/python/main.py", "src/python/models.py", "src/python/utils.py",
        "src/python/config.py", "src/python/api.py", "src/python/db.py",
        "src/python/auth.py", "src/python/tasks.py", "src/python/schemas.py",
        "src/python/middleware.py", "src/python/tests/test_main.py",
        "src/python/services/", "src/python/handlers/",
    ],
    CodeLanguage.JAVASCRIPT: [
        "src/javascript/index.js", "src/javascript/app.js",
        "src/javascript/components/App.jsx", "src/javascript/components/Header.jsx",
        "src/javascript/utils/helpers.js", "src/javascript/api/client.js",
        "src/javascript/hooks/", "src/javascript/services/",
        "src/javascript/state/store.js", "src/javascript/tests/",
    ],
    CodeLanguage.RUST: [
        "src/rust/main.rs", "src/rust/lib.rs", "src/rust/config.rs",
        "src/rust/error.rs", "src/rust/handlers/mod.rs",
        "src/rust/models/", "src/rust/utils/",
    ],
    CodeLanguage.GO: [
        "src/go/main.go", "src/go/handler.go", "src/go/config.go",
        "src/go/middleware.go", "src/go/repository.go",
        "src/go/models/", "src/go/services/",
    ],
    CodeLanguage.HTML_CSS: [
        "src/web/index.html", "src/web/styles.css",
        "src/web/components/", "src/web/assets/",
    ],
    CodeLanguage.SQL: [
        "src/sql/schema.sql", "src/sql/migrations/",
        "src/sql/queries/", "src/sql/seeds/",
    ],
}

# Extra files to diversify structure during development
_EXTRA_FILES = {
    CodeLanguage.PYTHON: [
        "src/python/celery_app.py", "src/python/websocket.py",
        "src/python/cache.py", "src/python/logger.py",
        "src/python/decorators.py", "src/python/validators.py",
        "src/python/exceptions.py", "src/python/cli.py",
    ],
    CodeLanguage.JAVASCRIPT: [
        "src/javascript/components/Dashboard.jsx", "src/javascript/components/Modal.jsx",
        "src/javascript/utils/validators.js", "src/javascript/api/websocket.js",
        "src/javascript/components/Settings.jsx", "src/javascript/hooks/useAuth.js",
    ],
    CodeLanguage.RUST: [
        "src/rust/cli.rs", "src/rust/server.rs", "src/rust/cache.rs",
    ],
    CodeLanguage.GO: [
        "src/go/worker.go", "src/go/grpc.go", "src/go/cache.go",
    ],
    CodeLanguage.HTML_CSS: [
        "src/web/dashboard.html", "src/web/responsive.css",
    ],
    CodeLanguage.SQL: [
        "src/sql/views.sql", "src/sql/procedures.sql",
    ],
}


def _plan_file_structure(tech_stack: list, max_files: int) -> list:
    """Plan file structure during architecture phase."""
    structure = ["README.md", ".gitignore"]

    files_per_lang = max(5, max_files // max(len(tech_stack), 1))

    for lang in tech_stack:
        # Gather only real files (not directories ending with /)
        templates = [f for f in _STRUCTURE_TEMPLATES.get(lang, [])
                     if not f.endswith("/")]
        extras = [f for f in _EXTRA_FILES.get(lang, [])
                  if not f.endswith("/")]
        # Take all templates first, then fill with extras
        pool = list(templates)
        for ex in extras:
            if ex not in pool:
                pool.append(ex)
        count = min(len(pool), files_per_lang)
        # Templates first, then random extras
        chosen = templates[:] if len(templates) <= count else random.sample(templates, count)
        remaining = count - len(chosen)
        if remaining > 0 and extras:
            available = [e for e in extras if e not in chosen]
            chosen.extend(random.sample(available, min(remaining, len(available))))
        structure.extend(chosen)

    return structure


def _evolve_file_structure(proj: Settlement, lang: CodeLanguage):
    """Diversify structure during development — new files are added."""
    extras = _EXTRA_FILES.get(lang, [])
    if not extras:
        return
    # 15% chance to add new files to structure
    if random.random() < 0.15:
        new_file = random.choice(extras)
        if new_file not in proj.file_structure:
            proj.file_structure.append(new_file)


# ─── Architecture Phase ──────────────────────────────────────────────

# architecture phase duration (in ticks)
_ARCH_PHASE_DURATION = 80

def _architecture_phase(world: World, proj: Settlement):
    """Architecture phase — file structure creation, team meetings."""
    elapsed = world.tick - proj.phase_tick
    members = [e for e in world.entities
               if e.alive and e.settlement_id == proj.id]

    if elapsed <= 1:
        # first tick: Architect announces structure
        architects = [e for e in members if e.role == Role.ARCHITECT]
        if architects:
            arch = architects[0]
            dirs = set()
            for f in proj.file_structure:
                parts = f.rsplit("/", 1)
                if len(parts) > 1 and parts[0]:
                    dirs.add(parts[0] + "/")
            dir_list = ", ".join(sorted(dirs)[:5])
            world.log_event(
                f"📐 Architect #{arch.id} creates structure: "
                f"{len(proj.file_structure)} files planned ({dir_list}...)")

    # frequent meetings — every arch tick (function runs every 50 world ticks)
    if len(members) >= 2:
        # 2-4 pairs meet each other
        num_pairs = min(len(members) // 2, 4)
        shuffled = list(members)
        random.shuffle(shuffled)
        spread = max(150, getattr(proj, 'radius', 100) * 2.5)
        for i in range(num_pairs):
            if i * 2 + 1 < len(shuffled):
                a, b = shuffled[i * 2], shuffled[i * 2 + 1]
                proj.team_meetings += 1
                # gentle nudge toward each other — wide spread around project
                angle = random.uniform(0, math.pi * 2)
                offset = random.uniform(spread * 0.3, spread * 0.8)
                mid_x = proj.x + math.cos(angle) * offset
                mid_y = proj.y + math.sin(angle) * offset
                a.x += (mid_x - a.x) * 0.05
                a.y += (mid_y - a.y) * 0.05
                b.x += (mid_x - b.x) * 0.05
                b.y += (mid_y - b.y) * 0.05
                _exchange_knowledge(world, a, b, proj)

    # Phase ends — minimum 1 meeting!
    if elapsed >= _ARCH_PHASE_DURATION and proj.team_meetings >= 1:
        proj.phase = "development"
        proj.phase_tick = world.tick
        world.log_event(
            f"🏗 '{proj.project_name}' — Architecture ready! "
            f"DEVELOPMENT Phase starts ({proj.team_meetings} meetings held)")
        world.spawn_particles(proj.x, proj.y, (100, 255, 150), count=25, speed=3.5, size=2.0)


def _exchange_knowledge(world: World, a, b, proj: Settlement):
    """Two entities meet each other and exchange knowledge."""
    # Track meeting for personality evolution
    try:
        from systems.advanced_lifecycle import _track_personality
        _track_personality(a, "meeting")
        _track_personality(b, "meeting")
    except Exception:
        pass

    # a can teach b a language and vice versa
    exchanged = False

    for lang in a.languages_known:
        if lang not in b.languages_known and random.random() < 0.20:
            b.languages_known.append(lang)
            # Track language learning for personality
            try:
                from systems.advanced_lifecycle import _track_personality
                _track_personality(b, "learned_language")
            except Exception:
                pass
            world.log_event(
                f"🤝 #{a.id} ({a.role.value}) taught #{b.id} {lang.value} "
                f"('{proj.project_name}' meeting)")
            exchanged = True
            break

    if not exchanged:
        for lang in b.languages_known:
            if lang not in a.languages_known and random.random() < 0.20:
                a.languages_known.append(lang)
                try:
                    from systems.advanced_lifecycle import _track_personality
                    _track_personality(a, "learned_language")
                except Exception:
                    pass
                world.log_event(
                    f"🤝 #{b.id} ({b.role.value}) taught #{a.id} {lang.value} "
                    f"('{proj.project_name}' meeting)")
                break


# ─── Review Phase ─────────────────────────────────────────────────────

# update_shared_project is called every 50 world ticks, so a meeting every
# other call is roughly once per 100 ticks of wall time.
_REVIEW_MEETING_EVERY_NTH_CALL = 2
_MAX_REVIEW_ROUNDS = 5         # maximum 5 rounds for bug-fixing

def _review_phase(world: World, proj: Settlement):
    """Review Phase — team meeting, project analysis, bug-fixing."""
    elapsed = world.tick - proj.phase_tick
    members = [e for e in world.entities
               if e.alive and e.settlement_id == proj.id]

    # team meeting — physical gather + information exchange.
    # Function only runs every 50 world ticks, so use the call index
    # derived from phase_tick alignment rather than raw-tick modulo.
    call_index = elapsed // 50
    if call_index % _REVIEW_MEETING_EVERY_NTH_CALL == 0 and len(members) >= 2:
        proj.team_meetings += 1
        # gentle pull toward project area — keep entities spread out
        for m in members:
            dx = proj.x - m.x
            dy = proj.y - m.y
            dist = (dx * dx + dy * dy) ** 0.5
            # only pull if far from project (> 2x radius)
            if dist > proj.radius * 2:
                m.x += dx * 0.08 + random.uniform(-40, 40)
                m.y += dy * 0.08 + random.uniform(-40, 40)
            else:
                # inside area — just add wander
                m.x += random.uniform(-50, 50)
                m.y += random.uniform(-50, 50)

        pairs = min(4, len(members) // 2)
        random.shuffle(members)
        for i in range(pairs):
            if i * 2 + 1 < len(members):
                _exchange_knowledge(world, members[i * 2], members[i * 2 + 1], proj)

        world.log_event(
            f"👥 '{proj.project_name}' — team meeting #{proj.team_meetings} "
            f"({len(members)} members, analyzing project...)")

    # bug fixing
    buggy = [s for s in proj.codebase if s.has_bugs]
    if buggy:
        _fix_bugs_phase(world, proj, buggy)
        proj.review_rounds += 1

        # if too many rounds and bugs can't be fixed — force push
        if proj.review_rounds >= _MAX_REVIEW_ROUNDS * 3:
            remaining = sum(1 for s in proj.codebase if s.has_bugs)
            world.log_event(
                f"⚠ '{proj.project_name}' — {remaining} bugs could not be fixed, "
                f"force push!")
            # remove buggy files from codebase
            proj.codebase = [s for s in proj.codebase if not s.has_bugs]
            proj.phase = "push"
            proj.phase_tick = world.tick
        return

    # no more bugs — successful review!
    # at least one meeting must be held
    if proj.team_meetings < 1:
        return

    proj.phase = "push"
    proj.phase_tick = world.tick
    total_quality = proj.code_quality
    world.log_event(
        f"✅ '{proj.project_name}' — Review successful! "
        f"0 Bugs, quality: {total_quality:.0%}, {proj.team_meetings} meetings. "
        f"PUSH Phase!")
    world.spawn_particles(proj.x, proj.y, (50, 255, 100), count=30, speed=4.0, size=3.0)


def _fix_bugs_phase(world: World, proj: Settlement, buggy: list):
    """Bug investigation and handoff to devs.
    
    TESTERs discover bugs, REVIEWERs verify,
    and devs fix them. 1-3 bugs fixed per tick.
    """
    members = [e for e in world.entities
               if e.alive and e.settlement_id == proj.id]
    
    # bug investigation chance by role
    fixers = []
    for e in members:
        if e.role == Role.TESTER:
            fixers.append((e, 0.60))      # testers find them well
        elif e.role == Role.REVIEWER:
            fixers.append((e, 0.45))      # reviewers too
        elif e.role == Role.ARCHITECT:
            fixers.append((e, 0.30))      # Architect
        elif e.role == Role.TEAM_LEAD:
            fixers.append((e, 0.20))      # lead less likely
        elif e.can_code:
            fixers.append((e, 0.10))      # regular dev
    
    fixed_count = 0
    for snippet in list(buggy):
        if not snippet.has_bugs:
            continue
        for fixer, chance in fixers:
            if random.random() < chance:
                snippet.has_bugs = False
                snippet.reviewed = True
                snippet.quality = min(1.0, snippet.quality + 0.15)
                proj.bug_count = max(0, proj.bug_count - 1)
                fixed_count += 1
                
                world.log_event(
                    f"🔧 #{fixer.id} ({fixer.role.value}) fixed bug in "
                    f"'{snippet.filename}' (quality: {snippet.quality:.0%})")
                break  # one fixer per bug
    
    remaining = sum(1 for s in proj.codebase if s.has_bugs)
    if fixed_count > 0:
        log.info(f"Bug-fix phase: {fixed_count} fixed, {remaining} remaining")
    if remaining > 0:
        world.log_event(
            f"🐛 '{proj.project_name}' — {remaining} bugs remain, "
            f"push blocked until all are fixed!")


def _complete_project(world: World):
    """Project completion — GitHub push and save to history."""
    proj = world._active_project
    if proj is None:
        return

    project_name = proj.project_name
    github_url = None

    # GitHub push
    try:
        from systems.github_integration import push_completed_project, is_enabled, get_user
        if is_enabled() and project_name:
            push_completed_project(proj, list(proj.codebase), "complete")
            user = get_user()
            # repo name: strip trailing -ID
            repo = project_name.rsplit("-", 1)[0] if project_name.rsplit("-", 1)[-1].isdigit() else project_name
            if user:
                github_url = f"https://github.com/{user}/{repo}"
    except Exception as e:
        log.error(f"GitHub push failed: {e}")

    # save to history
    entry = {
        "name": project_name,
        "github_url": github_url,
        "tick_started": proj.founded_tick,
        "tick_finished": world.tick,
        "files_count": len(proj.codebase),
        "total_commits": proj.total_commits,
        "bug_count": proj.bug_count,
        "tech_stack": [l.value if hasattr(l, 'value') else str(l) for l in proj.tech_stack],
        "population": proj.population,
        "code_quality": proj.code_quality,
    }
    completed_projects.append(entry)

    # Store in team memory for future project quality bonuses
    try:
        from systems.advanced_lifecycle import record_team_memory
        record_team_memory(world, entry)
    except Exception:
        pass

    project_num = len(completed_projects)

    world.log_event(
        f"✅ Project '{project_name}' completed! "
        f"({len(proj.codebase)} files, {proj.total_commits} commits)"
        + (f" → GitHub: {github_url}" if github_url else "")
    )
    world.spawn_particles(proj.x, proj.y, (50, 255, 100), count=40, speed=5.0, size=4.0)

    # cleanup — reset devs for new project
    for e in world.entities:
        if e.settlement_id == proj.id:
            e.settlement_id = None
            e.role = Role.NONE

    # Remove the completed project from the live settlements map so
    # downstream systems (diplomacy, movement, combat, …) stop iterating
    # over it every tick. History is preserved in `completed_projects`.
    world.settlements.pop(proj.id, None)

    world._active_project = None
    world._active_project_id = None

    log.info(f"Project #{project_num} '{project_name}' completed → {github_url}")


def update_shared_project(world: World):
    """Main update — called in step()."""
    ensure_active_project(world)

    proj = getattr(world, '_active_project', None)
    if proj is None:
        return

    # assign new devs (who aren't in a project yet)
    for e in world.entities:
        if (e.alive and e.can_code 
            and e.entity_type != EntityType.BUG 
            and e.settlement_id is None):
            e.settlement_id = proj.id

    # population update
    members = [e for e in world.entities 
               if e.alive and e.settlement_id == proj.id]
    proj.population = len(members)
