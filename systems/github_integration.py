"""GitHub \u10d8\u10dc\u10e2\u10d4\u10d2\u10e0\u10d0\u10ea\u10d8\u10d0 \u2014 \u10de\u10e0\u10dd\u10d4\u10e5\u10e2\u10d8\u10e1 \u10d3\u10d0\u10e1\u10e0\u10e3\u10da\u10d4\u10d1\u10d8\u10e1\u10d0\u10e1 batch push GitHub-\u10d6\u10d4."""

from __future__ import annotations
import base64
import json
import logging
import os
import threading
import time
from typing import TYPE_CHECKING, Optional

import urllib.request
import urllib.error

if TYPE_CHECKING:
    from core.models import CodeSnippet, Settlement

log = logging.getLogger("github")

# ================== \u10d9\u10dd\u10dc\u10e4\u10d8\u10d2\u10e3\u10e0\u10d0\u10ea\u10d8\u10d0 ==================

_GITHUB_TOKEN: Optional[str] = None
_GITHUB_USER: Optional[str] = None
_GITHUB_ENABLED = False

# \u10e3\u10d9\u10d5\u10d4 \u10d3\u10d0\u10de\u10e3\u10e8\u10e3\u10da\u10d8 \u10de\u10e0\u10dd\u10d4\u10e5\u10e2\u10d4\u10d1\u10d8 (\u10d2\u10d0\u10dc\u10db\u10d4\u10dd\u10e0\u10d4\u10d1\u10d8\u10d7 push \u10d7\u10d0\u10d5\u10d8\u10d3\u10d0\u10dc \u10d0\u10ea\u10d8\u10da\u10d4\u10d1\u10d0)
_pushed_projects: set[str] = set()

# Push queue \u2014 async batch push
_push_queue: list[dict] = []
_push_lock = threading.Lock()
_push_thread: Optional[threading.Thread] = None

# \u10e1\u10e2\u10d0\u10e2\u10d8\u10e1\u10e2\u10d8\u10d9\u10d0
_stats = {
    "projects_pushed": 0,
    "total_files_pushed": 0,
    "in_progress": 0,
}

# \u10d4\u10dc\u10d8\u10e1 extension-\u10d4\u10d1\u10d8
_LANG_DIRS = {
    "python": "python",
    "javascript": "javascript",
    "rust": "rust",
    "go": "go",
    "html_css": "web",
    "sql": "sql",
}


def configure(token: str):
    """\u10e2\u10dd\u10d9\u10d4\u10dc\u10d8\u10e1 \u10d9\u10dd\u10dc\u10e4\u10d8\u10d2\u10e3\u10e0\u10d0\u10ea\u10d8\u10d0."""
    global _GITHUB_TOKEN, _GITHUB_USER, _GITHUB_ENABLED
    _GITHUB_TOKEN = token

    try:
        user_data = _api_request("GET", "/user")
        _GITHUB_USER = user_data["login"]
        _GITHUB_ENABLED = True
        log.info(f"GitHub \u25cf \u10d3\u10d0\u10d9\u10d0\u10d5\u10e8\u10d8\u10e0\u10d4\u10d1\u10e3\u10da\u10d8\u10d0: {_GITHUB_USER}")
        # Pre-populate pushed projects from existing repos to avoid duplicates
        _sync_pushed_projects()
        _start_push_thread()
        return True
    except Exception as e:
        log.error(f"GitHub connection failed: {e}")
        _GITHUB_ENABLED = False
        return False


def _sync_pushed_projects():
    """Fetch existing repos and mark them as already pushed."""
    try:
        page = 1
        while True:
            repos = _api_request("GET", f"/users/{_GITHUB_USER}/repos?per_page=100&page={page}")
            if not repos:
                break
            for r in repos:
                _pushed_projects.add(r["name"])
            if len(repos) < 100:
                break
            page += 1
        log.info(f"GitHub \u25cf synced {len(_pushed_projects)} existing repos")
    except Exception as e:
        log.warning(f"GitHub repo sync failed: {e}")


def is_enabled() -> bool:
    return _GITHUB_ENABLED


def get_user() -> Optional[str]:
    return _GITHUB_USER


def is_project_pushed(project_name: str) -> bool:
    """\u10e3\u10d9\u10d5\u10d4 \u10d3\u10d0\u10d8\u10de\u10e3\u10e8\u10d0 \u10d4\u10e1 \u10de\u10e0\u10dd\u10d4\u10e5\u10e2\u10d8?"""
    return _clean_repo_name(project_name) in _pushed_projects


# ================== \u10db\u10d7\u10d0\u10d5\u10d0\u10e0\u10d8 \u10e4\u10e3\u10dc\u10e5\u10ea\u10d8\u10d0: batch push ==================

def push_completed_project(settlement, snippets: list, reason: str = "complete"):
    """\u10d3\u10d0\u10e1\u10e0\u10e3\u10da\u10d4\u10d1\u10e3\u10da\u10d8 \u10de\u10e0\u10dd\u10d4\u10e5\u10e2\u10d8\u10e1 \u10e7\u10d5\u10d4\u10da\u10d0 \u10e4\u10d0\u10d8\u10da\u10d8\u10e1 \u10d4\u10e0\u10d7\u10d8\u10d0\u10dc\u10d0\u10d3 push.

    \u10d2\u10d0\u10db\u10dd\u10eb\u10d0\u10ee\u10d4\u10d1\u10d0:
        settlement  \u2014 Settlement \u10dd\u10d1\u10d8\u10d4\u10e5\u10e2\u10d8
        snippets    \u2014 \u10e7\u10d5\u10d4\u10da\u10d0 CodeSnippet (\u10e1\u10d4\u10e2\u10da\u10db\u10d4\u10dc\u10e2\u10d8\u10e1 codebase)
        reason      \u2014 "complete" \u10d0\u10dc "archived"
    """
    if not _GITHUB_ENABLED:
        return
    if not settlement.project_name:
        return

    repo_name = _clean_repo_name(settlement.project_name)

    if repo_name in _pushed_projects:
        return

    _pushed_projects.add(repo_name)

    with _push_lock:
        _stats["in_progress"] += 1
        _push_queue.append({
            "type": "batch",
            "repo": repo_name,
            "project_name": settlement.project_name,
            "snippets": snippets,
            "tech_stack": settlement.tech_stack if hasattr(settlement, 'tech_stack') else [],
            "total_commits": settlement.total_commits if hasattr(settlement, 'total_commits') else len(snippets),
            "bug_count": settlement.bug_count if hasattr(settlement, 'bug_count') else 0,
            "population": settlement.population,
            "founded_tick": settlement.founded_tick if hasattr(settlement, 'founded_tick') else 0,
            "reason": reason,
        })

    log.info(f"GitHub batch push queued: {repo_name} ({len(snippets)} files, reason={reason})")


# ================== API ==================

def _api_request(method: str, path: str, data: dict = None) -> dict:
    """GitHub API request."""
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {_GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CodeWorld-Sim/3.0",
    }

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {e.code}: {error_body}") from e


# ================== Background Push Thread ==================

def _start_push_thread():
    global _push_thread
    if _push_thread and _push_thread.is_alive():
        return
    _push_thread = threading.Thread(target=_push_worker, daemon=True)
    _push_thread.start()
    log.info("GitHub push worker started")


def _push_worker():
    """Background worker \u2014 queue-\u10d3\u10d0\u10dc batch push-\u10d0\u10d5\u10e1 GitHub-\u10d6\u10d4."""
    while True:
        item = None
        with _push_lock:
            if _push_queue:
                item = _push_queue.pop(0)

        if item is None:
            time.sleep(2)
            continue

        try:
            _do_batch_push(item)
        except Exception as e:
            log.error(f"GitHub batch push failed for {item.get('repo', '?')}: {e}")
            with _push_lock:
                _stats["in_progress"] = max(0, _stats["in_progress"] - 1)

        time.sleep(1)


def _do_batch_push(item: dict):
    """\u10de\u10e0\u10dd\u10d4\u10e5\u10e2\u10d8\u10e1 \u10e7\u10d5\u10d4\u10da\u10d0 \u10e4\u10d0\u10d8\u10da\u10d8\u10e1 push \u10d4\u10e0\u10d7\u10d8\u10d0\u10dc\u10d0\u10d3."""
    repo = item["repo"]
    snippets = item["snippets"]
    reason = item["reason"]

    # 1. \u10e0\u10d4\u10de\u10dd\u10e1 \u10e8\u10d4\u10e5\u10db\u10dc\u10d0 (\u10d7\u10e3 \u10d0\u10e0 \u10d0\u10e0\u10e1\u10d4\u10d1\u10dd\u10d1\u10e1)
    tech_str = ", ".join(
        str(t.value) if hasattr(t, 'value') else str(t)
        for t in item.get("tech_stack", [])[:3]
    )
    desc = f"Code World simulation project | {reason} | Tech: {tech_str}"

    try:
        _api_request("GET", f"/repos/{_GITHUB_USER}/{repo}")
    except RuntimeError as e:
        if "404" in str(e):
            try:
                _api_request("POST", "/user/repos", {
                    "name": repo,
                    "description": desc,
                    "private": False,
                    "auto_init": True,
                    "has_issues": True,
                })
                time.sleep(2)
            except Exception as ce:
                log.error(f"GitHub create repo error: {ce}")
                return
        else:
            log.error(f"GitHub check error: {e}")
            return

    # 2. README \u10d2\u10d4\u10dc\u10d4\u10e0\u10d0\u10ea\u10d8\u10d0
    try:
        readme_content = _generate_readme(item)
        _push_file(repo, "README.md", readme_content, f"Project {reason}: {repo}")
    except Exception as re:
        log.warning(f"GitHub README push failed for {repo}: {re}")
    time.sleep(0.5)

    # 3. \u10e7\u10d5\u10d4\u10da\u10d0 \u10e1\u10dc\u10d8\u10de\u10d4\u10e2\u10d8\u10e1 push \u10d4\u10dc\u10d8\u10e1 \u10db\u10d8\u10ee\u10d4\u10d3\u10d5\u10d8\u10d7 \u10d3\u10d0\u10d2\u10e0\u10e3\u10de\u10d4\u10d1\u10e3\u10da\u10d8
    files_pushed = 0
    for snippet in snippets:
        # Filenames are clean basenames (e.g. "handler.go", "models.py").
        # Build the full path from the snippet's language.
        path = snippet.filename
        if not path.startswith("src/") and "README" not in path:
            lang_name = snippet.language.value if hasattr(snippet.language, 'value') else str(snippet.language)
            lang_dir = _LANG_DIRS.get(lang_name, "misc")
            _safe_fn = snippet.filename
            for _ch in '/\\:*?"<>|':
                _safe_fn = _safe_fn.replace(_ch, '_')
            path = f"src/{lang_dir}/{_safe_fn}"

        quality_emoji = "\u2728" if snippet.quality > 0.7 else "\U0001f4dd" if snippet.quality > 0.4 else "\U0001f6a7"
        msg = (
            f"{quality_emoji} {snippet.description}\n\n"
            f"Author: dev#{snippet.author_id} | Quality: {snippet.quality:.2f} | "
            f"Lines: {snippet.lines} | Tick: {snippet.tick_created}"
        )

        try:
            _push_file(repo, path, snippet.content, msg)
            files_pushed += 1
        except Exception as fe:
            log.warning(f"GitHub push file failed {path}: {fe}")

        time.sleep(0.3)  # Rate limit

    # 4. \u10e1\u10e2\u10d0\u10e2\u10d8\u10e1\u10e2\u10d8\u10d9\u10d8\u10e1 \u10d2\u10d0\u10dc\u10d0\u10ee\u10da\u10d4\u10d1\u10d0
    with _push_lock:
        _stats["projects_pushed"] += 1
        _stats["total_files_pushed"] += files_pushed
        _stats["in_progress"] = max(0, _stats["in_progress"] - 1)

    log.info(f"GitHub \u2705 {repo}: {files_pushed} files pushed ({reason})")


def _push_file(repo: str, path: str, content: str, message: str):
    """\u10d4\u10e0\u10d7\u10d8 \u10e4\u10d0\u10d8\u10da\u10d8\u10e1 push/update."""
    sha = None
    try:
        existing = _api_request("GET", f"/repos/{_GITHUB_USER}/{repo}/contents/{path}")
        sha = existing.get("sha")
    except RuntimeError:
        pass

    # clean surrogates (from emojis)
    clean = content.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    encoded = base64.b64encode(clean.encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": encoded}
    if sha:
        payload["sha"] = sha

    _api_request("PUT", f"/repos/{_GITHUB_USER}/{repo}/contents/{path}", payload)


def _generate_readme(item: dict) -> str:
    """Generate a meaningful README.md with project description and structure."""
    snippets = item.get("snippets", [])
    repo = item["repo"]
    reason = item["reason"]

    # Language statistics
    lang_counts = {}
    total_lines = 0
    total_quality = 0
    bug_count = 0
    reviewed_count = 0
    for s in snippets:
        lang = s.language.value if hasattr(s.language, 'value') else str(s.language)
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        total_lines += s.lines
        total_quality += s.quality
        if s.has_bugs:
            bug_count += 1
        if s.reviewed:
            reviewed_count += 1

    avg_quality = total_quality / max(1, len(snippets))

    # Author statistics
    author_commits = {}
    for s in snippets:
        author_commits[s.author_id] = author_commits.get(s.author_id, 0) + 1

    tech_str = ", ".join(
        str(t.value) if hasattr(t, 'value') else str(t)
        for t in item.get("tech_stack", [])
    )

    # Build file tree from actual snippet filenames
    file_tree = sorted(set(s.filename for s in snippets))

    # Generate project description from tech stack and file names
    desc_parts = []
    if "python" in tech_str:
        desc_parts.append("Python backend services")
    if "javascript" in tech_str:
        desc_parts.append("JavaScript frontend/Node.js modules")
    if "go" in tech_str:
        desc_parts.append("Go microservices")
    if "rust" in tech_str:
        desc_parts.append("Rust system components")
    if "sql" in tech_str:
        desc_parts.append("SQL database schemas")
    if "html" in tech_str.lower() or "css" in tech_str.lower():
        desc_parts.append("HTML/CSS web interface")
    project_desc = ", ".join(desc_parts) if desc_parts else "a multi-language software project"

    status_emoji = "\u2705" if reason == "complete" else "\U0001f4e6"

    lines = [
        f"# {status_emoji} {repo}",
        f"",
        f"> **{repo}** is an autonomously generated project featuring {project_desc}.",
        f"> Built by {len(author_commits)} AI developer entities collaborating in the Code World simulation.",
        f"",
        f"## \U0001f4cb Overview",
        f"",
        f"This project was planned, architected, and coded by simulated developer entities.",
        f"Each entity specializes in different languages and roles (Architect, Reviewer, Tester, Team Lead, DevOps).",
        f"The codebase follows a planned file structure created during the architecture phase.",
        f"",
        f"**Tech Stack**: {tech_str or 'Mixed'}",
        f"",
        f"## \U0001f4c2 Project Structure",
        f"",
        f"```",
        f"{repo}/",
    ]
    for fp in file_tree:
        lines.append(f"  {fp}")
    lines += [
        f"```",
        f"",
        f"## \U0001f4ca Stats",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| \U0001f4c1 Files | {len(snippets)} |",
        f"| \U0001f4dd Lines of Code | {total_lines} |",
        f"| \u2b50 Avg Quality | {avg_quality:.0%} |",
        f"| \U0001f41b Bugs Found | {bug_count} |",
        f"| \u2705 Reviewed | {reviewed_count} |",
        f"| \U0001f465 Contributors | {len(author_commits)} entities |",
        f"| \U0001f4e6 Commits | {item.get('total_commits', len(snippets))} |",
        f"",
        f"## \U0001f468\u200d\U0001f4bb Contributors",
        f"",
    ]

    # Language breakdown
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        pct = count / max(1, len(snippets)) * 100
        bar = "\u2588" * int(pct / 5) + "\u2591" * (20 - int(pct / 5))
        lines.append(f"- **{lang}**: {bar} {pct:.0f}% ({count} files)")

    lines += [
        f"",
        f"### Top Contributors",
        f"",
    ]
    for dev_id, commits in sorted(author_commits.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"- Entity #{dev_id}: {commits} files")

    lines += [
        f"",
        f"---",
        f"",
        f"\U0001f30d **Generated by [WORLD 3](https://github.com/codeworldentities/world3)**",
        f"",
        f"*An autonomous world where AI entities learn, collaborate, and build real software projects.*",
    ]

    return "\n".join(lines)

def _clean_repo_name(project_name: str) -> str:
    parts = project_name.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return project_name.replace(" ", "-")


def get_stats() -> dict:
    """Dashboard-\u10d8\u10e1\u10d7\u10d5\u10d8\u10e1 GitHub \u10e1\u10e2\u10d0\u10e2\u10d8\u10e1\u10e2\u10d8\u10d9\u10d0."""
    with _push_lock:
        queue_size = len(_push_queue)
    return {
        "enabled": _GITHUB_ENABLED,
        "user": _GITHUB_USER,
        "queue_size": queue_size,
        "projects_pushed": _stats["projects_pushed"],
        "total_files_pushed": _stats["total_files_pushed"],
        "in_progress": _stats["in_progress"],
    }
