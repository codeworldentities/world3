"""Soul memory compression + identity layer — Phase 7.

Implements three patterns from the 2026 agent landscape, adapted to run 100%
on local Ollama (no paid APIs, no GPU requirement):

    * DeerFlow — context compression: summarise old state to filesystem,
      keep the working set small.
    * DeepTutor — dual memory: ``reflection`` (what happened) +
      ``profile`` (who am I).
    * Hermes — skill loop: successful behaviours accrete as named skills.

All LLM calls go through ``llm.provider.call_ollama`` with aggressive
fallbacks — if the model is down, compression degrades to a deterministic
truncation rather than crashing the tick.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from config import (
    SOUL_COMPRESSION_ENABLED,
    SOUL_MEMORY_COMPRESSION_THRESHOLD,
    SOUL_MEMORY_KEEP_IMPORTANT,
    SOUL_MEMORY_KEEP_RECENT,
    SOUL_PROFILE_UPDATE_INTERVAL,
    SOUL_REFLECTION_INTERVAL,
    SOUL_SKILLS_MAX,
)

if TYPE_CHECKING:
    from core.soul import Soul

log = logging.getLogger("systems.memory_compression")


# ================== Fallback summariser (no LLM) ==================

def _deterministic_summary(texts: list[str], max_chars: int = 280) -> str:
    """Last-resort summary when Ollama is unavailable. Concatenates
    first, middle and last event text, truncated to keep output bounded."""
    if not texts:
        return ""
    if len(texts) <= 3:
        joined = " | ".join(texts)
    else:
        joined = f"{texts[0]} | ... {len(texts) - 2} events ... | {texts[-1]}"
    return joined[:max_chars]


# ================== LLM calls ==================

def _summarise_via_ollama(memories_text: list[str]) -> Optional[str]:
    """Ask the local model for a one-paragraph reflection. Returns None
    on any failure; caller falls back to the deterministic summary."""
    try:
        from llm.provider import call_ollama  # local import to avoid cycle
    except ImportError:
        return None

    if not memories_text:
        return ""

    system = (
        "You compress an entity's long-term memory. "
        "Return a single JSON object with key 'summary' whose value is one "
        "concise paragraph (<=60 words) describing themes, relationships, and "
        "pivotal events. Do not list raw events. No markdown."
    )
    user = "EVENTS:\n- " + "\n- ".join(memories_text[:80])  # bound input

    raw = call_ollama(system, user, max_tokens=200, json_mode=True)
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        s = obj.get("summary", "").strip()
        return s or None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _build_profile_via_ollama(
    name: str, role: str, traits: dict, reflection: str
) -> Optional[str]:
    """Regenerate stable identity statement."""
    try:
        from llm.provider import call_ollama
    except ImportError:
        return None

    system = (
        "You write a stable self-description for an autonomous agent. "
        "Return JSON {'profile': <one paragraph, <=50 words, first person>}. "
        "Emphasise values, working style, and goals — not events."
    )
    trait_str = ", ".join(f"{k}={v}" for k, v in list(traits.items())[:8])
    user = (
        f"NAME: {name}\nROLE: {role}\nTRAITS: {trait_str}\n"
        f"RECENT LIFE: {reflection[:400] or '(none yet)'}"
    )
    raw = call_ollama(system, user, max_tokens=160, json_mode=True)
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        p = obj.get("profile", "").strip()
        return p or None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


# ================== Public API ==================

def needs_compression(soul: "Soul") -> bool:
    return (
        SOUL_COMPRESSION_ENABLED
        and len(soul.memory) > SOUL_MEMORY_COMPRESSION_THRESHOLD
    )


def compress_soul_memory(soul: "Soul", tick: int) -> bool:
    """Compress the oldest half of ``soul.memory`` into a single reflection.

    Preserves:
      * the ``SOUL_MEMORY_KEEP_RECENT`` newest memories verbatim;
      * the ``SOUL_MEMORY_KEEP_IMPORTANT`` highest-weight older memories verbatim;
      * one synthetic ``SoulMemory(kind='reflection')`` summarising the rest.

    Returns True if any compression happened.
    """
    if not needs_compression(soul):
        return False

    from core.soul import SoulMemory  # local import (soul imports this module? no, but be safe)

    mems = soul.memory
    keep_recent = mems[-SOUL_MEMORY_KEEP_RECENT:] if SOUL_MEMORY_KEEP_RECENT > 0 else []
    older = mems[:-SOUL_MEMORY_KEEP_RECENT] if SOUL_MEMORY_KEEP_RECENT > 0 else list(mems)
    if not older:
        return False

    # Preserve top-K important from the older pool
    important = sorted(older, key=lambda m: m.weight, reverse=True)[:SOUL_MEMORY_KEEP_IMPORTANT]
    important_ids = {id(m) for m in important}
    to_summarise = [m for m in older if id(m) not in important_ids]

    if not to_summarise:
        return False

    texts = [m.text for m in to_summarise if m.text]
    summary = _summarise_via_ollama(texts) or _deterministic_summary(texts)
    if not summary:
        return False

    reflection_mem = SoulMemory(
        tick=tick,
        kind="reflection",
        text=summary,
        weight=0.5,
        metadata={
            "compressed_count": len(to_summarise),
            "from_tick": to_summarise[0].tick,
            "to_tick": to_summarise[-1].tick,
        },
    )

    # Rebuild memory list: [reflection] + important (sorted by tick) + recent
    important_sorted = sorted(important, key=lambda m: m.tick)
    soul.memory = [reflection_mem] + important_sorted + keep_recent
    soul.reflection = summary
    soul.reflection_tick = tick
    log.info(
        "Soul %s (%s) compressed %d memories -> reflection (kept %d recent, %d important)",
        soul.id[:6], soul.name, len(to_summarise),
        len(keep_recent), len(important_sorted),
    )
    return True


def maybe_refresh_reflection(soul: "Soul", tick: int) -> bool:
    """Periodically regenerate ``soul.reflection`` even without compression,
    so named characters always have a fresh life-summary for prompts."""
    if not SOUL_COMPRESSION_ENABLED:
        return False
    if tick - soul.reflection_tick < SOUL_REFLECTION_INTERVAL:
        return False
    texts = [m.text for m in soul.memory[-30:] if m.text]
    if not texts:
        return False
    summary = _summarise_via_ollama(texts) or _deterministic_summary(texts)
    if not summary:
        return False
    soul.reflection = summary
    soul.reflection_tick = tick
    return True


def maybe_refresh_profile(soul: "Soul", tick: int) -> bool:
    """Periodically regenerate ``soul.profile`` — the stable identity layer."""
    if not SOUL_COMPRESSION_ENABLED:
        return False
    if tick - soul.profile_tick < SOUL_PROFILE_UPDATE_INTERVAL:
        return False
    profile = _build_profile_via_ollama(
        soul.name, soul.role, soul.traits or {}, soul.reflection or "",
    )
    if not profile:
        # first-time fallback: use personality_summary
        if not soul.profile and soul.personality_summary:
            soul.profile = soul.personality_summary[:240]
            soul.profile_tick = tick
            return True
        return False
    soul.profile = profile
    soul.profile_tick = tick
    return True


# ================== Skill loop (Hermes pattern) ==================

def grant_skill(
    soul: "Soul",
    name: str,
    description: str,
    tick: int,
) -> bool:
    """Record that this soul has demonstrated a named capability.

    If the skill already exists its ``uses`` counter is incremented instead
    of duplicating the entry. Oldest skills are evicted when above the cap.
    Returns True if a new skill was added.
    """
    if not name:
        return False
    name = name.strip().lower()[:48]
    for s in soul.skills:
        if s.get("name") == name:
            s["uses"] = int(s.get("uses", 0)) + 1
            s["last_tick"] = tick
            return False
    soul.skills.append({
        "name": name,
        "description": (description or "")[:180],
        "acquired_tick": tick,
        "last_tick": tick,
        "uses": 1,
    })
    # Evict oldest-and-least-used if over cap
    if len(soul.skills) > SOUL_SKILLS_MAX:
        soul.skills.sort(key=lambda s: (s.get("uses", 0), s.get("last_tick", 0)))
        soul.skills = soul.skills[-SOUL_SKILLS_MAX:]
    log.debug("Soul %s learned skill '%s'", soul.id[:6], name)
    return True


# ================== World-level orchestrator ==================

def tick_compression(souls, tick: int) -> dict:
    """Run one pass across all souls. Safe to call frequently — each soul
    has its own cadence. Returns stats for instrumentation."""
    compressed = refreshed_ref = refreshed_prof = 0
    for soul in souls:
        try:
            if compress_soul_memory(soul, tick):
                compressed += 1
            elif maybe_refresh_reflection(soul, tick):
                refreshed_ref += 1
            if maybe_refresh_profile(soul, tick):
                refreshed_prof += 1
        except (AttributeError, TypeError, ValueError) as exc:
            log.debug("compression skipped for soul: %s", exc)
    return {
        "compressed": compressed,
        "reflections_refreshed": refreshed_ref,
        "profiles_refreshed": refreshed_prof,
    }
