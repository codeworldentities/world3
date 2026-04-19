"""Soul system — granting, reincarnation, reflection, and soul-to-soul dialogue.

Design goals
------------
- Souls are scarce. Only a handful of entities at any time carry one.
- A Soul persists across death via reincarnation into a genetic descendant
  or, failing that, goes dormant (archived, loadable later).
- All hooks are additive. If Souls are disabled (no world.souls dict),
  everything still works.
"""
from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Iterable, Optional

from core.enums import EntityType, Role
from core.soul import Soul, SoulMemory, new_soul_id

if TYPE_CHECKING:
    from core.models import Entity
    from core.world import World


log = logging.getLogger("systems.soul")


# ================== Tunables ==================

try:
    from config import MAX_SOULS as _CFG_MAX_SOULS
    MAX_SOULS = _CFG_MAX_SOULS
except ImportError:
    MAX_SOULS = 30                  # hard cap on living+dormant souls
SOUL_GRANT_INTERVAL = 100       # ticks between grant sweeps
ELDER_AGE = 5000                # ticks to qualify as an elder
REFLECTION_INTERVAL = 500       # ticks between reflection regenerations
REFLECTION_MIN_MEMORIES = 12    # need at least this many to reflect
MEMORY_COMPRESS_THRESHOLD = 60  # compress oldest if memory grows past this
MEMORY_COMPRESS_KEEP = 30       # how many recent entries to always keep


# ================== Grant eligibility ==================

def _is_leader(world: "World", e: "Entity") -> bool:
    if e.settlement_id is None:
        return False
    sett = world.settlements.get(e.settlement_id)
    return bool(sett and sett.leader_id == e.id)


def _is_architect(e: "Entity") -> bool:
    return getattr(e.role, "name", "") in ("ARCHITECT", "SENIOR", "LEAD")


def _is_copilot(e: "Entity") -> bool:
    return e.entity_type == EntityType.AI_COPILOT


def _is_elder(e: "Entity") -> bool:
    return e.age >= ELDER_AGE


def eligible_for_soul(world: "World", e: "Entity") -> bool:
    if e.soul_id is not None:
        return False
    if not e.alive:
        return False
    if e.entity_type == EntityType.BUG:
        return False
    return (
        _is_leader(world, e)
        or _is_architect(e)
        or _is_copilot(e)
        or _is_elder(e)
    )


# ================== Persona generation ==================

_ROLE_TEMPLATE = {
    "leader":    "{name} is a team lead — decisive, protective of the codebase, trusting people over process.",
    "architect": "{name} thinks in systems. Patient, opinionated about structure, allergic to shortcuts.",
    "elder":     "{name} is an elder who has seen {age} ticks of code. Dry humour, long memory, slow to anger.",
    "copilot":   "{name} is an AI copilot: curious, tireless, humble about its own certainty.",
    "dev":       "{name} is a working developer who learned the craft by doing and still prefers shipping to talking.",
}


def _role_key(world: "World", e: "Entity") -> str:
    if _is_leader(world, e):
        return "leader"
    if _is_copilot(e):
        return "copilot"
    if _is_architect(e):
        return "architect"
    if _is_elder(e):
        return "elder"
    return "dev"


def _role_label(role_key: str) -> str:
    return {
        "leader": "Team Lead",
        "architect": "Architect",
        "elder": "Elder",
        "copilot": "AI Copilot",
        "dev": "Developer",
    }.get(role_key, "Developer")


def _traits_snapshot(e: "Entity") -> dict:
    return {
        "aggression": round(e.aggression, 3),
        "curiosity": round(e.curiosity, 3),
        "sociability": round(e.sociability, 3),
        "resilience": round(e.resilience, 3),
        "code_quality": round(e.code_quality, 3),
        "generation": e.generation,
        "languages": [l.name for l in e.languages_known][:5],
    }


def _fallback_persona(name: str, role_key: str, e: "Entity") -> str:
    return _ROLE_TEMPLATE[role_key].format(name=name, age=e.age)


def _llm_persona(world: "World", e: "Entity", name: str, role_key: str) -> str:
    """Best-effort LLM persona generation; fall back to template."""
    brain = getattr(world, "brain", None)
    if not brain or not getattr(brain, "connected", False):
        return _fallback_persona(name, role_key, e)
    provider = getattr(brain, "provider", None)
    if provider is None or not hasattr(provider, "generate"):
        return _fallback_persona(name, role_key, e)

    traits = _traits_snapshot(e)
    prompt = (
        "Write ONE short paragraph (2-3 sentences, max 300 chars) describing "
        f"the character of {name}, a {_role_label(role_key)} in a simulated code world. "
        f"Traits: {traits}. Age {e.age} ticks, generation {e.generation}. "
        "No lists, no meta, no greetings — just the character description."
    )
    try:
        text = provider.generate(prompt, max_tokens=120, temperature=0.7)
        text = (text or "").strip().replace("\n", " ")
        if 20 <= len(text) <= 500:
            return text
    except Exception as exc:
        log.debug("persona LLM failed: %s", exc)
    return _fallback_persona(name, role_key, e)


# ================== Naming ==================

_NAME_POOL = [
    "Ada", "Linus", "Grace", "Dennis", "Alan", "Margaret", "Ken",
    "Barbara", "Niklaus", "Brian", "Radia", "Donald", "Edsger",
    "Hedy", "John", "Frances", "Guido", "Brendan", "Bjarne", "Anders",
    "Katherine", "Rasmus", "Yukihiro", "James", "Joanne",
]


def _choose_name(world: "World", e: "Entity") -> str:
    if e.dev_name:
        return e.dev_name
    used = {s.name for s in getattr(world, "souls", {}).values()}
    candidates = [n for n in _NAME_POOL if n not in used]
    base = random.choice(candidates) if candidates else random.choice(_NAME_POOL)
    if base in used:
        base = f"{base}-{e.id}"
    return base


# ================== Grant ==================

def grant_soul(world: "World", e: "Entity") -> Optional[Soul]:
    souls = _world_souls(world)
    living = sum(1 for s in souls.values() if s.entity_id is not None)
    if living >= MAX_SOULS:
        return None

    role_key = _role_key(world, e)
    name = _choose_name(world, e)
    persona = _llm_persona(world, e, name, role_key)

    soul = Soul(
        id=new_soul_id(),
        entity_id=e.id,
        name=name,
        role=_role_label(role_key),
        born_tick=world.tick,
        personality_summary=persona,
        traits=_traits_snapshot(e),
        last_active_tick=world.tick,
    )
    soul.remember(
        world.tick, "birth",
        f"Awoke as {soul.role} in settlement {e.settlement_id}.",
        weight=1.0,
    )
    souls[soul.id] = soul
    e.soul_id = soul.id
    e.dev_name = name
    world.log_event(f"✨ A soul awoke: {name} ({soul.role})")
    log.info("granted soul %s to entity %s (%s)", soul.id, e.id, name)
    _audit("soul.granted", world.tick,
           soul_id=soul.id, name=name, role=soul.role, entity_id=e.id)
    _persist(world, soul)
    return soul


def _world_souls(world: "World") -> dict:
    if not hasattr(world, "souls") or world.souls is None:
        world.souls = {}
    return world.souls


# ================== Grant sweep (call from world.step) ==================

def maybe_grant_souls(world: "World") -> None:
    """Periodic sweep: grant souls to newly-eligible entities."""
    if world.tick % SOUL_GRANT_INTERVAL != 0:
        return
    souls = _world_souls(world)
    living = sum(1 for s in souls.values() if s.entity_id is not None)
    if living >= MAX_SOULS:
        return

    candidates = [e for e in world.entities if eligible_for_soul(world, e)]
    random.shuffle(candidates)
    budget = min(3, MAX_SOULS - living)
    for e in candidates[:budget]:
        grant_soul(world, e)


# ================== Reincarnation / death ==================

def on_entity_death(world: "World", dead: "Entity") -> None:
    """Called when an entity with a soul dies. Try to reincarnate."""
    if not dead.soul_id:
        return
    souls = _world_souls(world)
    soul = souls.get(dead.soul_id)
    if soul is None:
        return

    soul.remember(
        world.tick, "loss",
        f"Body #{dead.entity_id} died at age {dead.age}.",
        weight=0.9,
    )
    soul.previous_entity_ids.append(dead.id)

    heir = _find_heir(world, dead, soul)
    if heir is not None:
        soul.entity_id = heir.id
        soul.rebirth_count += 1
        soul.parent_soul_id = soul.parent_soul_id or soul.id
        heir.soul_id = soul.id
        if not heir.dev_name:
            heir.dev_name = soul.name
        soul.remember(
            world.tick, "achievement",
            f"Reborn in body #{heir.id} (rebirth #{soul.rebirth_count}).",
            weight=1.0,
        )
        world.log_event(f"♻ {soul.name} was reborn (#{soul.rebirth_count})")
        log.info("soul %s reincarnated into entity %s", soul.id, heir.id)
        _audit("soul.reincarnated", world.tick,
               soul_id=soul.id, name=soul.name, new_entity=heir.id,
               rebirth_count=soul.rebirth_count)
    else:
        # Dormant: detach body, keep soul for later load
        soul.entity_id = -1
        soul.remember(
            world.tick, "loss",
            "No heir found — the soul sleeps.",
            weight=0.8,
        )
        log.info("soul %s has gone dormant", soul.id)
    _persist(world, soul)


def _find_heir(world: "World", dead: "Entity", soul: Soul) -> Optional["Entity"]:
    """Prefer descendants in same settlement, same type, high resilience."""
    candidates: list["Entity"] = []
    for e in world.entities:
        if not e.alive or e.soul_id is not None:
            continue
        if e.entity_type == EntityType.BUG:
            continue
        score = 0.0
        if dead.id in (e.parent_a, e.parent_b):
            score += 3.0
        if e.settlement_id == dead.settlement_id:
            score += 1.0
        if e.entity_type == dead.entity_type:
            score += 0.5
        score += e.resilience * 0.5
        if score > 0.5:
            candidates.append((score, e))  # type: ignore[arg-type]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)  # type: ignore[index]
    return candidates[0][1]  # type: ignore[index]


# ================== Reflection + memory compression ==================

def maybe_reflect(world: "World") -> None:
    if world.tick % REFLECTION_INTERVAL != 0:
        return
    souls = _world_souls(world)
    if not souls:
        return
    brain = getattr(world, "brain", None)
    provider = getattr(brain, "provider", None) if brain else None
    has_llm = bool(brain and getattr(brain, "connected", False) and provider)

    for soul in souls.values():
        if soul.entity_id is None or soul.entity_id < 0:
            continue
        if len(soul.memory) < REFLECTION_MIN_MEMORIES:
            continue
        if has_llm:
            _llm_reflect(soul, provider, world.tick)
        else:
            _simple_reflect(soul, world.tick)
        _compress_memory(soul, world.tick)
        _persist(world, soul)


def _simple_reflect(soul: Soul, tick: int) -> None:
    imp = soul.important_memories(5)
    soul.reflection = " | ".join(m.text for m in imp)[:600]
    soul.reflection_tick = tick


def _llm_reflect(soul: Soul, provider, tick: int) -> None:
    recent = " ".join(f"[t{m.tick}] {m.text}" for m in soul.recent_memories(15))
    imp = " ".join(f"({m.text})" for m in soul.important_memories(5))
    prompt = (
        f"You are writing a reflection for {soul.name}, a {soul.role}. "
        f"Persona: {soul.personality_summary[:200]}. "
        f"Recent events: {recent[:600]}. "
        f"Defining memories: {imp[:300]}. "
        "Write ONE short paragraph (2-3 sentences) in first person summarising "
        "how they see their life so far. No greetings, no meta."
    )
    try:
        text = provider.generate(prompt, max_tokens=150, temperature=0.7)
        text = (text or "").strip().replace("\n", " ")
        if 20 <= len(text) <= 800:
            soul.reflection = text
            soul.reflection_tick = tick
            return
    except Exception as exc:
        log.debug("reflection LLM failed: %s", exc)
    _simple_reflect(soul, tick)


def _compress_memory(soul: Soul, tick: int) -> None:
    if len(soul.memory) <= MEMORY_COMPRESS_THRESHOLD:
        return
    # Keep the most-important + the most-recent; merge the rest into one entry
    keep_recent = soul.memory[-MEMORY_COMPRESS_KEEP:]
    rest = soul.memory[:-MEMORY_COMPRESS_KEEP]
    if not rest:
        return
    top = sorted(rest, key=lambda m: m.weight, reverse=True)[:5]
    merged_text = "Earlier life: " + " / ".join(m.text for m in top)[:400]
    merged = SoulMemory(
        tick=tick, kind="reflection",
        text=merged_text, weight=0.95,
    )
    soul.memory = [merged] + keep_recent


# ================== Soul-to-soul dialogue ==================

def maybe_soul_dialogue(world: "World") -> None:
    """Occasionally let two co-located souls share a real exchange."""
    if world.tick % 200 != 0:
        return
    souls = _world_souls(world)
    if len(souls) < 2:
        return
    living = [s for s in souls.values() if s.entity_id is not None and s.entity_id >= 0]
    if len(living) < 2:
        return
    ent_by_id = {e.id: e for e in world.entities if e.alive}
    pairs: list[tuple[Soul, Soul]] = []
    for i, a in enumerate(living):
        ea = ent_by_id.get(a.entity_id)
        if ea is None:
            continue
        for b in living[i + 1:]:
            eb = ent_by_id.get(b.entity_id)
            if eb is None:
                continue
            if ea.settlement_id is not None and ea.settlement_id == eb.settlement_id:
                pairs.append((a, b))
            elif abs(ea.x - eb.x) < 40 and abs(ea.y - eb.y) < 40:
                pairs.append((a, b))
    if not pairs:
        return
    a, b = random.choice(pairs)
    _run_dialogue(world, a, b)


def _run_dialogue(world: "World", a: Soul, b: Soul) -> None:
    brain = getattr(world, "brain", None)
    provider = getattr(brain, "provider", None) if brain else None

    topic = _pick_topic(world, a, b)
    line_a = _dialogue_line(provider, a, b, topic, speaker_is_a=True)
    line_b = _dialogue_line(provider, b, a, topic + " / " + line_a, speaker_is_a=False)

    a.remember(world.tick, "relation",
               f"Spoke with {b.name}: {line_b[:140]}",
               weight=0.6, other_soul_id=b.id)
    b.remember(world.tick, "relation",
               f"Spoke with {a.name}: {line_a[:140]}",
               weight=0.6, other_soul_id=a.id)
    affinity = random.uniform(-0.05, 0.15)
    a.update_affinity(b.id, affinity)
    b.update_affinity(a.id, affinity)

    world.log_event(f"💬 {a.name} ↔ {b.name}")
    convo = {
        "tick": world.tick,
        "speaker_id": a.entity_id, "listener_id": b.entity_id,
        "speaker_type": "soul", "listener_type": "soul",
        "dialogue": f"{a.name}: {line_a} | {b.name}: {line_b}",
    }
    world.conversations.append(convo)
    if len(world.conversations) > world.max_conversations:
        world.conversations.pop(0)

    _persist(world, a)
    _persist(world, b)


def _pick_topic(world: "World", a: Soul, b: Soul) -> str:
    options = [
        "the current project's direction",
        "a recent bug they dealt with",
        "the meaning of clean code",
        "a memory from an earlier era",
        "their next move",
    ]
    return random.choice(options)


def _dialogue_line(provider, me: Soul, other: Soul, topic: str, speaker_is_a: bool) -> str:
    if provider is None:
        return f"We should talk about {topic}."
    prompt = (
        f"You are {me.name}, a {me.role}. "
        f"Persona: {me.personality_summary[:220]}. "
        f"You are talking to {other.name} ({other.role}). "
        f"Topic: {topic}. "
        "Reply with ONE short line (max 200 chars), in character, no quotes, no meta."
    )
    try:
        text = provider.generate(prompt, max_tokens=80, temperature=0.8)
        text = (text or "").strip().replace("\n", " ")
        if text:
            return text[:220]
    except Exception as exc:
        log.debug("dialogue LLM failed: %s", exc)
    return f"Let's talk about {topic}."


# ================== Persistence helper ==================

def _persist(world: "World", soul: Soul) -> None:
    try:
        from persistence.soul_store import save_soul
        save_soul(soul)
    except Exception as exc:
        log.debug("soul persist failed: %s", exc)


def _audit(kind: str, tick: int, **data) -> None:
    try:
        from persistence.audit import record
        record(kind, tick, **data)
    except Exception as exc:
        log.debug("audit record failed: %s", exc)


# ================== Public iteration helpers ==================

def iter_living_souls(world: "World") -> Iterable[Soul]:
    for s in _world_souls(world).values():
        if s.entity_id is not None and s.entity_id >= 0:
            yield s


def get_soul_for_entity(world: "World", e: "Entity") -> Optional[Soul]:
    if not e.soul_id:
        return None
    return _world_souls(world).get(e.soul_id)
