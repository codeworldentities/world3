"""Code Generation — Entities write real code via LLM.

This is world3's main new feature:
- Developers generate code snippets via LLM
- Code is saved to the project's codebase
- Low quality code naturally has bugs
- Reviewers verify code quality
- Generated code is saved to the output/ folder
"""

from __future__ import annotations
import logging
import os
import random
from typing import TYPE_CHECKING

from core.enums import EntityType, CodeLanguage, Role, KnowledgeType
from core.models import CodeSnippet
from config import (
    CODE_GEN_INTERVAL, CODE_GEN_MIN_ENERGY, CODE_GEN_MIN_KNOWLEDGE,
    CODE_QUALITY_BASE, CODE_BUG_CORRUPT_CHANCE, CODE_REVIEW_QUALITY_BOOST,
    CODE_MAX_PER_PROJECT, CODE_OUTPUT_DIR, LANG_EXTENSIONS,
    KNOWLEDGE_TO_LANG, KNOWLEDGE_EFFECTS,
)

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity

log = logging.getLogger("systems.code_gen")

# code topics for each language
_CODE_TOPICS = {
    CodeLanguage.PYTHON: [
        "data processing pipeline", "REST API endpoint", "database model",
        "unit test", "async task handler", "configuration parser",
        "logging utility", "authentication middleware", "caching decorator",
        "data validation schema", "CLI tool", "file processor",
    ],
    CodeLanguage.JAVASCRIPT: [
        "React component", "Express middleware", "event handler",
        "utility function", "API client", "state management",
        "form validation", "animation hook", "WebSocket handler",
        "service worker", "DOM manipulation utility",
    ],
    CodeLanguage.RUST: [
        "error handling enum", "trait implementation", "struct with methods",
        "iterator adapter", "concurrent data structure", "CLI parser",
        "file I/O utility", "memory-safe buffer",
    ],
    CodeLanguage.GO: [
        "HTTP handler", "goroutine worker pool", "interface implementation",
        "middleware chain", "database repository", "gRPC service",
        "configuration loader", "health check endpoint",
    ],
    CodeLanguage.HTML_CSS: [
        "responsive layout", "form component", "navigation bar",
        "dashboard widget", "card component", "modal dialog",
    ],
    CodeLanguage.SQL: [
        "table creation", "complex query", "stored procedure",
        "index optimization", "migration script", "view creation",
    ],
}

_next_snippet_id = 0

# filter topics by role
_ROLE_TOPIC_HINTS = {
    Role.ARCHITECT: ["pipeline", "API", "struct", "interface", "handler", "component", "layout", "table", "model"],
    Role.REVIEWER: ["validation", "test", "check", "verify", "schema"],
    Role.TESTER: ["test", "check", "validation", "mock", "assert"],
    Role.DEVOPS_ENG: ["configuration", "CLI", "worker", "loader", "health", "migration", "CI"],
    Role.TEAM_LEAD: ["middleware", "service", "handler", "endpoint", "API"],
}


def _pick_topic_for_role(role: Role, lang: CodeLanguage) -> str:
    """Pick topic by role — work distribution."""
    topics = _CODE_TOPICS.get(lang, ["utility function"])
    hints = _ROLE_TOPIC_HINTS.get(role)
    if hints:
        matching = [t for t in topics if any(h.lower() in t.lower() for h in hints)]
        if matching:
            return random.choice(matching)
    return random.choice(topics)


# ─── File-structure-aware naming ─────────────────────────────────────

# Map file extensions to CodeLanguage for claiming structure files
_EXT_TO_LANG = {
    ".py": CodeLanguage.PYTHON,
    ".js": CodeLanguage.JAVASCRIPT,
    ".jsx": CodeLanguage.JAVASCRIPT,
    ".rs": CodeLanguage.RUST,
    ".go": CodeLanguage.GO,
    ".html": CodeLanguage.HTML_CSS,
    ".css": CodeLanguage.HTML_CSS,
    ".sql": CodeLanguage.SQL,
}


def _claim_structure_file(proj, lang: CodeLanguage) -> str | None:
    """Claim an unclaimed file from the project's planned file_structure.

    Returns the structure path (e.g. 'src/python/models.py') or None if
    no matching unclaimed file exists.
    """
    if not proj or not getattr(proj, 'file_structure', None):
        return None

    # Track which basenames are already claimed by existing snippets
    claimed = set()
    for snippet in proj.codebase:
        claimed.add(snippet.filename)

    # Find unclaimed files matching this language
    candidates = []
    for path in proj.file_structure:
        if os.path.basename(path) in claimed:
            continue
        # Skip directories (end with /) and non-code files
        if path.endswith("/") or path in ("README.md", ".gitignore"):
            continue
        # Match by extension
        ext = os.path.splitext(path)[1].lower()
        if _EXT_TO_LANG.get(ext) == lang:
            candidates.append(path)

    if not candidates:
        return None
    return random.choice(candidates)


def _topic_from_filename(filepath: str) -> str:
    """Derive a meaningful code topic from a structured filepath.

    'src/python/models.py' → 'models — data models and schemas'
    'src/go/middleware.go'  → 'middleware — request processing chain'
    """
    basename = os.path.splitext(os.path.basename(filepath))[0]

    _TOPIC_HINTS = {
        "main": "application entry point and initialization",
        "models": "data models and schemas",
        "utils": "utility helper functions",
        "config": "application configuration and settings",
        "api": "API route handlers",
        "db": "database connection and queries",
        "auth": "authentication and authorization",
        "tasks": "background task processing",
        "schemas": "data validation schemas",
        "middleware": "request processing middleware",
        "index": "main module entry point",
        "app": "application setup and routing",
        "helpers": "shared helper utilities",
        "client": "API client for external services",
        "store": "state management store",
        "lib": "core library functions",
        "error": "error types and handling",
        "handlers": "request handlers",
        "handler": "request handler functions",
        "repository": "data access layer",
        "server": "server setup and configuration",
        "worker": "background worker processes",
        "cache": "caching layer",
        "logger": "logging configuration",
        "cli": "command-line interface",
        "grpc": "gRPC service definitions",
        "schema": "database schema definition",
        "test_main": "unit tests for main module",
        "validators": "input validation functions",
        "websocket": "WebSocket connection handler",
        "styles": "stylesheet definitions",
    }

    hint = _TOPIC_HINTS.get(basename, basename.replace("_", " "))
    return f"{basename} — {hint}"


def get_next_snippet_id() -> int:
    global _next_snippet_id
    _next_snippet_id += 1
    return _next_snippet_id


def process_code_generation(world: World):
    """Main loop — all developers write code on the shared project."""
    # active project
    active = getattr(world, '_active_project', None)

    # writing code only during development phase!
    if active and getattr(active, 'phase', 'development') != 'development':
        return

    for e in world.entities:
        if not e.alive or not e.can_code:
            continue
        if e.energy < CODE_GEN_MIN_ENERGY:
            continue
        if len(e.languages_known) < CODE_GEN_MIN_KNOWLEDGE:
            continue
        if random.random() > 0.40:
            continue

        # project is full? — skip (shared_project will transition to new one)
        target = (active.max_files if active and active.max_files else CODE_MAX_PER_PROJECT)
        if active and len(active.codebase) >= target:
            continue

        # language selection — priority by project tech_stack
        lang = None
        if active and active.tech_stack:
            matching = [l for l in e.languages_known if l in active.tech_stack]
            if matching:
                # Prefer the language the dev has most XP in.
                matching.sort(
                    key=lambda l: e.language_xp.get(l.value, 0.0),
                    reverse=True,
                )
                # 70% of the time pick the top specialist language,
                # 30% pick a random one (so breadth still grows).
                if random.random() < 0.70:
                    lang = matching[0]
                else:
                    lang = random.choice(matching)
        if lang is None:
            lang = random.choice(e.languages_known)

        # topic selection by role — work distribution
        # First try to claim a file from the planned file_structure
        structure_path = None
        if active:
            structure_path = _claim_structure_file(active, lang)

        if structure_path:
            topic = _topic_from_filename(structure_path)
            filename = os.path.basename(structure_path)
        else:
            topic = _pick_topic_for_role(e.role, lang)
            _safe_topic = topic.replace(' ', '_')
            for _ch in '/\\:*?"<>|':
                _safe_topic = _safe_topic.replace(_ch, '_')
            ext = LANG_EXTENSIONS.get(lang, ".txt")
            filename = f"{_safe_topic[:30]}{ext}"

        # code quality — depends on mood and experience
        quality = CODE_QUALITY_BASE
        quality += e.resilience * 0.15
        quality += min(0.2, e.age / 5000)  # Experience
        quality += min(0.1, e.commits * 0.01)

        # knowledge bonus
        k_effects = world._get_knowledge_effects(e)
        if "code_quality_mult" in k_effects:
            quality *= k_effects["code_quality_mult"]

        # Senior Dev bonus
        if e.entity_type == EntityType.SENIOR_DEV:
            quality += 0.15
        elif e.entity_type == EntityType.INTERN:
            quality -= 0.1

        # Reviewers write better code
        if e.role == Role.REVIEWER:
            quality += 0.05
        elif e.role == Role.ARCHITECT:
            quality += 0.08

        # Team memory bonus — past project experience with same tech
        try:
            from systems.advanced_lifecycle import get_team_memory_bonus
            quality += get_team_memory_bonus(world, active.tech_stack if active else [])
        except Exception:
            pass

        # Specialisation bonus — XP in this language boosts quality.
        # Caps at +0.15 so a seasoned specialist beats a generalist
        # without breaking the 0-1 range.
        lang_xp = e.language_xp.get(lang.value, 0.0)
        if lang_xp > 0:
            quality += min(0.15, lang_xp / 200.0)

        quality = max(0.1, min(1.0, quality + random.uniform(-0.1, 0.1)))

        # code generation via LLM
        code_content = ""
        project_name = active.project_name if active else ""
        # Collect sibling files for context
        sibling_files = []
        if active:
            for s in active.codebase[-10:]:
                sibling_files.append(s.filename)
        if world.brain and world.brain.connected:
            code_content = world.brain.request_code(
                language=lang.value,
                topic=topic,
                quality_hint=quality,
                entity_type=e.entity_type.value,
                project_name=project_name,
                filepath=filename,
                sibling_files=sibling_files,
            )

        if not code_content:
            code_content = _generate_placeholder_code(lang, topic)

        lines = len(code_content.strip().split("\n"))

        snippet = CodeSnippet(
            id=get_next_snippet_id(),
            author_id=e.id,
            language=lang,
            content=code_content,
            description=topic,
            quality=quality,
            tick_created=world.tick,
            lines=lines,
            filename=filename,
            has_bugs=quality < 0.45 or random.random() < 0.25,
        )

        e.code_output.append(snippet.id)
        e.commits += 1
        e.code_quality = (e.code_quality * 0.9 + quality * 0.1)
        e.energy -= 0.08

        # Track language usage for skill decay system
        if hasattr(e, 'language_last_used'):
            e.language_last_used[lang.value] = world.tick

        # Specialisation XP — reward the author in the language they used.
        try:
            from systems.mentoring import grant_commit_xp
            grant_commit_xp(e, lang, quality)
        except Exception as exc:  # pragma: no cover — defensive
            log.debug("grant_commit_xp skipped: %s", exc)

        world.code_snippets[snippet.id] = snippet
        world.total_code_generated += 1

        # add to active project
        target = (active.max_files if active and active.max_files else CODE_MAX_PER_PROJECT)
        if active and len(active.codebase) < target:
            active.codebase.append(snippet)
            active.total_commits += 1
            # diversify file structure
            try:
                from systems.shared_project import _evolve_file_structure
                _evolve_file_structure(active, lang)
            except (ImportError, AttributeError) as exc:
                log.debug("_evolve_file_structure skipped: %s", exc)

        # save files to output/ folder
        _save_code_to_file(world, snippet, e)

        world.spawn_particles(e.x, e.y, (100, 200, 255), count=6, speed=2.0, size=1.5)

        # Hermes skill loop — if this entity has a soul and the code is
        # notable (good quality), record the demonstrated skill.
        try:
            if quality >= 0.6:
                soul = getattr(world, "souls", {}) and next(
                    (s for s in world.souls.values() if s.entity_id == e.id),
                    None,
                )
                if soul is not None:
                    from systems.memory_compression import grant_skill
                    grant_skill(
                        soul,
                        name=f"{lang.value}:{topic}",
                        description=f"Produced {topic} ({lang.value}) at q={quality:.2f}",
                        tick=world.tick,
                    )
        except (AttributeError, ImportError) as exc:
            log.debug("skill grant skipped: %s", exc)

        # log
        if e.commits % 5 == 0:
            world.log_event(
                f"💻 #{e.id} ({e.role.value}) wrote {topic} ({lang.value}, quality: {quality:.2f})")

        # code.generated event
        world._pending_code.append({
            "entity_id": e.id,
            "snippet_id": snippet.id,
            "language": lang.value,
            "topic": topic,
            "quality": quality,
            "tick": world.tick,
        })


def process_code_review(world: World):
    """Reviewers check code quality."""
    for e in world.entities:
        if not e.alive or e.role != Role.REVIEWER:
            continue
        if e.settlement_id is None:
            continue
        sett = world.settlements.get(e.settlement_id)
        if not sett or not sett.codebase:
            continue

        # search for unreviewed code
        unreviewed = [s for s in sett.codebase
                      if not s.reviewed and s.author_id != e.id]
        if not unreviewed:
            continue
        if random.random() > 0.03:
            continue

        snippet = random.choice(unreviewed)
        snippet.reviewed = True
        snippet.reviewer_id = e.id
        snippet.quality = min(1.0, snippet.quality + CODE_REVIEW_QUALITY_BOOST)
        e.reviews_done += 1

        world.log_event(
            f"📝 #{e.id} reviewed #{snippet.author_id}'s {snippet.description}")


def process_natural_bugs(world: World):
    """Bugs naturally appear in code — just like in real projects.

    Unreviewed code may over time introduce
    latent bugs (based on quality, missing updates, etc.).
    """
    # in projects' codebase
    for sett in world.settlements.values():
        if not sett.codebase:
            continue
        clean_code = [s for s in sett.codebase
                      if not s.has_bugs and not s.reviewed]
        for s in clean_code:
            bug_chance = max(0.02, 0.12 * (1.0 - s.quality))
            if random.random() < bug_chance:
                s.has_bugs = True
                sett.bug_count += 1

    # in global snippets too
    for s in world.code_snippets.values():
        if not s.has_bugs and not s.reviewed:
            bug_chance = max(0.02, 0.10 * (1.0 - s.quality))
            if random.random() < bug_chance:
                s.has_bugs = True


def _safe_path_component(name: str, fallback: str = "unnamed") -> str:
    """Strip any path separators / traversal parts from a user/LLM-derived name.

    Only allow [A-Za-z0-9._-]; anything else becomes '_'. Never returns
    a value that would escape the parent directory.
    """
    import re
    # Take only the basename to defeat "../../etc/passwd"
    name = os.path.basename(str(name))
    # Drop leading dots (no hidden files / no ".." slipping through)
    name = name.lstrip(".")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not cleaned or set(cleaned) == {"_"}:
        cleaned = fallback
    return cleaned[:120]


def _save_code_to_file(world: World, snippet: CodeSnippet, entity):
    """Save generated code to file."""
    try:
        output_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)), CODE_OUTPUT_DIR))
        os.makedirs(output_dir, exist_ok=True)

        safe_filename = _safe_path_component(snippet.filename, "snippet.txt")

        # project name sub-folder
        if entity.settlement_id is not None:
            sett = world.settlements.get(entity.settlement_id)
            if sett and sett.project_name:
                safe_project = _safe_path_component(sett.project_name, "project")
                project_dir = os.path.join(output_dir, safe_project)
                os.makedirs(project_dir, exist_ok=True)
                filepath = os.path.join(project_dir, safe_filename)
            else:
                filepath = os.path.join(output_dir, safe_filename)
        else:
            filepath = os.path.join(output_dir, safe_filename)

        # Final guard: resolved path must still be inside output_dir.
        # Use pathlib.is_relative_to() for cross-platform correctness —
        # avoids Windows/POSIX separator pitfalls and resolves symlinks.
        from pathlib import Path
        output_root = Path(output_dir).resolve()
        try:
            resolved_path = Path(filepath).resolve()
            resolved_path.relative_to(output_root)
        except (ValueError, OSError) as exc:
            log.warning("Refusing to write outside output dir: %s (%s)",
                        filepath, exc)
            return
        resolved = str(resolved_path)

        header = (
            f"# Generated by Developer #{entity.id} "
            f"({entity.entity_type.value})\n"
            f"# Language: {snippet.language.value}\n"
            f"# Quality: {snippet.quality:.2f}\n"
            f"# Topic: {snippet.description}\n"
            f"# Tick: {snippet.tick_created}\n\n"
        )

        with open(resolved, "w", encoding="utf-8") as f:
            f.write(header + snippet.content)

    except OSError as exc:
        log.warning("Failed to save snippet %s: %s", snippet.id, exc)


def _generate_placeholder_code(lang: CodeLanguage, topic: str) -> str:
    """Placeholder code — without LLM, unique each time."""
    uid = random.randint(100, 9999)
    n = random.randint(2, 20)
    vnames = random.choice(["data", "result", "output", "cache", "store", "buffer", "items", "payload"])
    ret = random.choice(["processed", "transformed", "compiled", "validated", "resolved"])

    if lang == CodeLanguage.PYTHON:
        imports = random.choice([
            "import os\nimport json\n",
            "import sys\nimport hashlib\n",
            "from typing import Dict, List, Optional\nimport logging\n",
            "import asyncio\nfrom pathlib import Path\n",
            "from collections import defaultdict\nimport re\n",
            "import datetime\nimport functools\n",
        ])
        body_variants = [
            f'''    {vnames} = {{}}\n    for i in range({n}):\n        {vnames}[f"key_{{i}}"] = i * {random.randint(2,9)}\n    return {vnames}''',
            f'''    {vnames} = []\n    for item in range({n}):\n        if item % {random.randint(2,5)} == 0:\n            {vnames}.append(item ** {random.randint(2,3)})\n    return sorted({vnames})''',
            f'''    {vnames} = defaultdict(list)\n    threshold = {random.uniform(0.1, 0.9):.2f}\n    for idx in range({n}):\n        val = idx / {n}\n        if val > threshold:\n            {vnames}["high"].append(val)\n        else:\n            {vnames}["low"].append(val)\n    return dict({vnames})''',
            f'''    logger = logging.getLogger(__name__)\n    {vnames} = {{}}\n    try:\n        for i in range({n}):\n            {vnames}[i] = hash(str(i) + "{uid}")\n        logger.info(f"Processed {{{n}}} items")\n    except Exception as e:\n        logger.error(f"Error: {{e}}")\n    return {vnames}''',
            f'''    stack = []\n    visited = set()\n    for node in range({n}):\n        if node not in visited:\n            stack.append(node)\n            visited.add(node * {random.randint(2,7)})\n    return list(visited)[::{random.choice([-1, 1])}]''',
        ]
        body = random.choice(body_variants)
        return f'''{imports}
def {topic.replace(" ", "_")}_{uid}():
    """{topic} — auto-generated v{uid}."""
{body}


class {topic.replace(" ", "_").title()}Handler_{uid}:
    def __init__(self):
        self._{vnames} = None
        self._initialized = False

    def execute(self):
        if not self._initialized:
            self._{vnames} = {topic.replace(" ", "_")}_{uid}()
            self._initialized = True
        return self._{vnames}


if __name__ == "__main__":
    handler = {topic.replace(" ", "_").title()}Handler_{uid}()
    print(f"Result: {{handler.execute()}}")
'''

    elif lang == CodeLanguage.JAVASCRIPT:
        func_name = "".join(w.capitalize() if i > 0 else w for i, w in enumerate(topic.split()))
        imports = random.choice([
            "", "// @ts-check\n", "/* eslint-disable no-unused-vars */\n",
            "'use strict';\n",
        ])
        body_variants = [
            f'''  const {vnames} = new Map();\n  for (let i = 0; i < {n}; i++) {{\n    {vnames}.set(`key_${{i}}`, i * {random.randint(2,9)});\n  }}\n  return Object.fromEntries({vnames});''',
            f'''  const {vnames} = Array.from({{ length: {n} }}, (_, i) => i * {random.randint(2,7)});\n  return {vnames}.filter(x => x % {random.randint(2,5)} === 0).reduce((a, b) => a + b, 0);''',
            f'''  const {vnames} = {{}};\n  const keys = {list(random.sample(["alpha","beta","gamma","delta","epsilon","zeta","theta"], min(n, 7)))};\n  keys.forEach((k, i) => {{ {vnames}[k] = Math.pow(i, {random.randint(2,3)}); }});\n  return {{ ...{vnames}, _meta: {{ generated: Date.now(), id: {uid} }} }};''',
            f'''  return new Promise((resolve) => {{\n    const {vnames} = [];\n    for (let i = 0; i < {n}; i++) {{\n      {vnames}.push({{ id: i, value: Math.random() * {random.randint(10,100)} }});\n    }}\n    resolve({vnames}.sort((a, b) => a.value - b.value));\n  }});''',
        ]
        body = random.choice(body_variants)
        return f'''{imports}/**
 * {topic} — auto-generated v{uid}
 * @param {{Object}} options
 * @returns {{*}}
 */
export function {func_name}_{uid}(options = {{}}) {{
  const config = {{ maxRetries: {random.randint(1,5)}, timeout: {random.randint(1000,10000)}, ...options }};
{body}
}}

export const {func_name}Defaults_{uid} = {{
  enabled: {random.choice(["true", "false"])},
  maxRetries: {random.randint(1,10)},
  version: "{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,20)}",
}};
'''

    elif lang == CodeLanguage.RUST:
        fields = random.sample(["data", "buffer", "count", "state", "cache", "index"], random.randint(2,4))
        struct_name = topic.replace(" ", "").title() + f"V{uid}"
        return f'''/// {topic} — auto-generated v{uid}
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct {struct_name} {{
    {fields[0]}: Vec<u8>,
    {fields[1]}: {'usize' if random.random() > 0.5 else 'i64'},
    initialized: bool,
}}

impl {struct_name} {{
    pub fn new() -> Self {{
        Self {{
            {fields[0]}: Vec::with_capacity({random.randint(16, 256)}),
            {fields[1]}: {random.randint(0, 100)},
            initialized: false,
        }}
    }}

    pub fn process(&mut self) -> Result<{random.choice(["usize", "String", "Vec<u8>", "()", "bool"])}, Box<dyn std::error::Error>> {{
        let mut map: HashMap<&str, i32> = HashMap::new();
        for i in 0..{n} {{
            map.insert("{ret}", i * {random.randint(2,7)});
        }}
        self.initialized = true;
        self.{fields[1]} {'=' if random.random() > 0.5 else '+='} {random.randint(1, 50)}{' as i64' if random.random() > 0.5 else ''};
        Ok({random.choice([f'self.{fields[0]}.len()', f'format!("{struct_name} ready")', f'self.{fields[0]}.clone()', '()', 'true'])})
    }}

    pub fn is_ready(&self) -> bool {{
        self.initialized && self.{fields[0]}.len() > {random.randint(0, 10)}
    }}
}}

#[cfg(test)]
mod tests {{
    use super::*;

    #[test]
    fn test_{topic.replace(" ", "_")}() {{
        let mut instance = {struct_name}::new();
        assert!(!instance.is_ready());
        let _ = instance.process();
        assert!(instance.initialized);
    }}
}}
'''

    elif lang == CodeLanguage.GO:
        struct_name = topic.replace(" ", "").title() + f"V{uid}"
        return f'''package main

import (
\t"fmt"
\t"sync"
\t{random.choice(['"time"', '"strings"', '"sort"', '"math"'])}
)

// {struct_name} — {topic} (auto-generated v{uid})
type {struct_name} struct {{
\tData   []byte
\tReady  bool
\tCount  int
\tmu     sync.Mutex
}}

func New{struct_name}() *{struct_name} {{
\treturn &{struct_name}{{
\t\tData:  make([]byte, 0, {random.randint(32, 512)}),
\t\tReady: false,
\t\tCount: {random.randint(0, 10)},
\t}}
}}

func (s *{struct_name}) Process() error {{
\ts.mu.Lock()
\tdefer s.mu.Unlock()

\tfor i := 0; i < {n}; i++ {{
\t\ts.Data = append(s.Data, byte(i%{random.randint(128, 256)}))
\t\ts.Count++
\t}}
\ts.Ready = true
\tfmt.Printf("{struct_name}: processed %d items\\n", s.Count)
\treturn nil
}}

func (s *{struct_name}) Stats() map[string]int {{
\treturn map[string]int{{
\t\t"data_len": len(s.Data),
\t\t"count":    s.Count,
\t\t"ready":    func() int {{ if s.Ready {{ return 1 }}; return 0 }}(),
\t}}
}}
'''

    elif lang == CodeLanguage.SQL:
        table_name = topic.replace(" ", "_").lower() + f"_{uid}"
        cols = random.sample([
            ("email", "VARCHAR(255)"), ("status", "VARCHAR(50) DEFAULT 'active'"),
            ("score", "DECIMAL(10,2)"), ("counter", "INTEGER DEFAULT 0"),
            ("description", "TEXT"), ("metadata", "JSONB"),
            ("is_active", "BOOLEAN DEFAULT TRUE"), ("priority", "SMALLINT DEFAULT 0"),
        ], random.randint(3, 5))
        col_defs = ",\n    ".join(f"{c[0]} {c[1]}" for c in cols)
        return f'''-- Auto-generated: {topic} v{uid}
-- Created for project optimization

CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    {col_defs},
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_{table_name}_name
    ON {table_name}(name);

CREATE INDEX IF NOT EXISTS idx_{table_name}_created
    ON {table_name}(created_at DESC);

-- Seed data
INSERT INTO {table_name} (name{", " + cols[0][0] if cols else ""})
VALUES
{chr(10).join(f"    ('item_{i}'{', ' + repr(f'val_{i}_{uid}') if cols else ''}){',' if i < n-1 else ';'}" for i in range(min(n, 8)))}

-- View
CREATE OR REPLACE VIEW v_{table_name}_summary AS
SELECT name, COUNT(*) as total, MAX(created_at) as last_update
FROM {table_name}
GROUP BY name
ORDER BY total DESC;
'''
    else:
        classes = random.sample(["container", "wrapper", "card", "panel", "grid", "flex-row", "header", "section"], random.randint(2,4))
        colors = [f"#{random.randint(0,255):02x}{random.randint(0,255):02x}{random.randint(0,255):02x}" for _ in range(3)]
        return f'''<!-- Auto-generated: {topic} v{uid} -->
<div class="{topic.replace(" ", "-")}-{uid}">
  <header class="{classes[0]}">
    <h2>{topic}</h2>
    <nav class="nav-{uid}">
      <a href="#section-1">Overview</a>
      <a href="#section-2">Details</a>
    </nav>
  </header>
  <main class="{classes[1]}">
    <div class="{classes[2] if len(classes) > 2 else 'content'}">
      <p>Generated component for {topic}</p>
      <span class="badge badge-{uid}">v{uid}</span>
    </div>
  </main>
</div>

<style>
.{topic.replace(" ", "-")}-{uid} {{
  display: {random.choice(["flex", "grid"])};
  {random.choice(["flex-direction: column", "grid-template-columns: 1fr 2fr"])};
  gap: {random.randint(8, 24)}px;
  padding: {random.randint(8, 32)}px;
  background: {colors[0]};
  border-radius: {random.randint(4, 16)}px;
  border: 1px solid {colors[1]};
}}
.{topic.replace(" ", "-")}-{uid} .{classes[0]} {{
  color: {colors[2]};
  font-size: {random.randint(14, 24)}px;
  font-weight: {random.choice([400, 500, 600, 700])};
}}
.badge-{uid} {{
  background: {colors[1]};
  color: white;
  padding: 2px 8px;
  border-radius: {random.randint(2, 12)}px;
  font-size: {random.randint(10, 14)}px;
}}
</style>
'''
