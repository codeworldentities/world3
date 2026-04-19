"""Soul persistence — JSON (full state) + Markdown (human-readable card).

Souls are stored separately from world saves so they survive even when a world
file is wiped, and so OpenClaw / external tools can read them as plain files.

Layout under <project>/saves/souls/:
    <soul_id>.json   — canonical, machine-readable
    <soul_id>.md     — human-readable persona card (optional, best-effort)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict

from core.soul import Soul

log = logging.getLogger("persistence.soul_store")

SOUL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "saves", "souls"
)


def _ensure_dir() -> None:
    os.makedirs(SOUL_DIR, exist_ok=True)


def soul_json_path(soul_id: str) -> str:
    return os.path.join(SOUL_DIR, f"{soul_id}.json")


def soul_md_path(soul_id: str) -> str:
    return os.path.join(SOUL_DIR, f"{soul_id}.md")


def save_soul(soul: Soul, write_markdown: bool = True) -> str:
    _ensure_dir()
    path = soul_json_path(soul.id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(soul.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

    if write_markdown:
        try:
            _write_markdown_card(soul)
        except Exception as e:
            log.debug("soul markdown card failed for %s: %s", soul.id, e)

    return path


def save_all_souls(souls: Dict[str, Soul]) -> None:
    for s in souls.values():
        try:
            save_soul(s)
        except Exception as e:
            log.warning("failed to save soul %s: %s", s.id, e)


def load_all_souls() -> Dict[str, Soul]:
    out: Dict[str, Soul] = {}
    if not os.path.isdir(SOUL_DIR):
        return out
    for fname in os.listdir(SOUL_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SOUL_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            soul = Soul.from_dict(data)
            out[soul.id] = soul
        except Exception as e:
            log.warning("failed to load soul %s: %s", fname, e)
    return out


def delete_soul(soul_id: str) -> None:
    for p in (soul_json_path(soul_id), soul_md_path(soul_id)):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError as e:
            log.debug("delete_soul %s failed: %s", p, e)


def _write_markdown_card(soul: Soul) -> None:
    lines = [
        f"# {soul.name}",
        "",
        f"- **Role**: {soul.role}",
        f"- **Born**: tick {soul.born_tick}",
        f"- **Rebirths**: {soul.rebirth_count}",
        f"- **Entity body**: #{soul.entity_id}",
        f"- **Soul ID**: `{soul.id}`",
        "",
        "## Personality",
        "",
        soul.personality_summary or "_(not yet generated)_",
        "",
    ]
    if soul.traits:
        lines.append("## Traits")
        lines.append("")
        for k, v in soul.traits.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")
    if soul.reflection:
        lines.append("## Reflection")
        lines.append("")
        lines.append(soul.reflection)
        lines.append("")
    recent = soul.recent_memories(12)
    if recent:
        lines.append("## Recent memories")
        lines.append("")
        for m in recent:
            lines.append(f"- **t{m.tick}** [{m.kind}, w={m.weight:.2f}] {m.text}")
        lines.append("")

    with open(soul_md_path(soul.id), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
