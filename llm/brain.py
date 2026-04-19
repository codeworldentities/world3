"""LLM brain — code world prompts, queue, cache, worker."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from queue import PriorityQueue, Empty
from typing import Optional, Callable

from config import (
    LLM_ENABLED, LLM_MODEL, LLM_MAX_QUEUE, LLM_CACHE_SIZE,
    LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_TIMEOUT,
    LLM_VALIDATOR_ENABLED, FAKE_GEORGIAN_PATTERNS, CANON_FORBIDDEN_WORDS,
    LLM_CONVO_LANGUAGE,
    KIMI_ENABLED, KIMI_API_KEY, KIMI_MODEL, KIMI_TEMPERATURE, KIMI_MAX_TOKENS,
)
from core.enums import KnowledgeType
from config import KNOWLEDGE_TREE

log = logging.getLogger("llm.brain")


# ================== Request / Response ==================

@dataclass(order=True)
class LLMRequest:
    priority: int
    entity_id: int = field(compare=False)
    prompt: str = field(compare=False)
    context_hash: str = field(compare=False)
    callback: Optional[Callable] = field(default=None, compare=False, repr=False)
    tick: int = field(default=0, compare=False)


@dataclass
class LLMResponse:
    entity_id: int
    thought: str = ""
    dialogue: str = ""
    action: str = ""
    target_id: Optional[int] = None
    mood: str = "neutral"
    raw: str = ""


# ================== LRU Cache ==================

class LRUCache:
    def __init__(self, maxsize: int = LLM_CACHE_SIZE):
        self._cache: OrderedDict[str, LLMResponse] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[LLMResponse]:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: LLMResponse):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()

    def __len__(self):
        return len(self._cache)


# ================== Validator ==================

def is_valid_georgian(text: str) -> bool:
    if not text:
        return True
    georgian_chars = sum(1 for c in text if 'ა' <= c <= 'ჰ')
    ratio = georgian_chars / max(len(text.replace(" ", "")), 1)
    if ratio > 0.3:
        text_lower = text.lower()
        for pattern in FAKE_GEORGIAN_PATTERNS:
            if pattern in text_lower:
                return False
    return True


def breaks_canon(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for word in CANON_FORBIDDEN_WORDS:
        if word.lower() in text_lower:
            return True
    return False


def validate_llm_output(text: str, entity_type_value: str = "") -> tuple[bool, str]:
    if not LLM_VALIDATOR_ENABLED:
        return True, ""
    # Only enforce Georgian script when explicitly configured; English is default.
    if str(LLM_CONVO_LANGUAGE).lower().startswith("georgian"):
        if not is_valid_georgian(text):
            return False, "fake_georgian"
    if breaks_canon(text):
        return False, "canon_violation"
    return True, ""


# ================== Code World Prompts ==================

SYSTEM_PROMPT = """You are a Developer in a virtual code world. You think and speak only in English.
In this world, bugs attack, developers write code, projects are created.
Respond with valid JSON:
{"thought": "short inner thought (1 sentence, in English)", "dialogue": "what you say in English, or empty", "action": "one of: code/debug/review/deploy/collaborate/explore/rest/learn/refactor", "mood": "one of: happy/angry/scared/curious/neutral/proud/focused/burned_out"}

Rules:
- thought: short and personal — in English
- dialogue: only if you want to communicate with others — in English
- action: best action for your situation
- mood: your current state
- everything under 15 words
- Stay in role: Developer writes code, Bug corrupts, Refactorer cleans up"""


def build_entity_prompt(entity_data: dict, context: dict) -> str:
    e = entity_data
    lines = []

    # --- prompt-injection guard -----------------------------------------
    # Some fields (memories, LLM-authored 'situation', nearby entity labels)
    # can contain attacker- or model-controlled strings. Strip obvious prompt
    # hijack attempts: newlines that start a new instruction, role markers,
    # and control chars. Also cap length.
    def _clean(txt, limit: int = 200) -> str:
        if txt is None:
            return ""
        s = str(txt)
        # Remove ASCII/Unicode control chars
        s = "".join(ch for ch in s if ch.isprintable() or ch == " ")
        # Collapse whitespace / newlines
        s = " ".join(s.split())
        # Regex-based blocklist — tolerant of whitespace/case variations
        # (e.g. "</ system>", "<| IM_START |>")
        import re as _re
        s = _re.sub(r"<\s*/?\s*\|?\s*(system|im_start|im_end|user|assistant)"
                    r"\s*\|?\s*>", "", s, flags=_re.IGNORECASE)
        s = _re.sub(r"\b(SYSTEM|USER|ASSISTANT)\s*:", "", s, flags=_re.IGNORECASE)
        return s[:limit]

    personality = []
    if e["aggression"] > 0.6:
        personality.append("aggressive debugger")
    elif e["aggression"] < 0.3:
        personality.append("calm coder")
    if e["curiosity"] > 0.6:
        personality.append("curious")
    if e["sociability"] > 0.6:
        personality.append("pair-programmer")
    elif e["sociability"] < 0.3:
        personality.append("solo dev")
    if e["resilience"] > 0.6:
        personality.append("resilient")
    pers_str = ", ".join(personality) if personality else "full-stack"

    type_map = {
        "Developer": "Developer", "Bug": "Bug",
        "Refactorer": "Refactorer", "AI Copilot": "AI Copilot",
        "Senior Dev": "Senior", "Intern": "Intern",
    }
    role_map = {
        "Freelancer": "Freelancer", "Team Lead": "Team Lead",
        "Reviewer": "Reviewer", "Architect": "Architect",
        "Tester": "Tester", "DevOps Engineer": "DevOps Engineer",
    }

    etype = type_map.get(str(e['type']), e['type'])
    erole = role_map.get(str(e['role']), e['role'])

    lines.append(f"You are #{e['id']}, {etype}, {e['gender']}.")
    lines.append(f"Experience: {e['age']} Tick, Energy: {e['energy']:.0%}, Role: {erole}.")
    lines.append(f"Style: {pers_str}.")

    if e.get("languages"):
        lines.append(f"Languages: {', '.join(e['languages'])}.")
    if e.get("commits"):
        lines.append(f"Commits: {e['commits']}, bugs fixed: {e.get('bugs_fixed', 0)}.")

    if e.get("memories"):
        mem_strs = [f"- {_clean(m, 140)}" for m in e["memories"][-3:]]
        lines.append("Recent memories:\n" + "\n".join(mem_strs))

    if context.get("settlement"):
        s = context["settlement"]
        lines.append(f"You are in project: {_clean(s.get('name', '?'), 60)}, "
                     f"{s['population']} devs, tech level: {s['tech_level']}.")
        if s.get("is_leader"):
            lines.append("You are Team Lead! Your decisions guide the project.")
        if s.get("at_war_with"):
            lines.append(f"MERGE CONFLICT! Rival team: #{s['at_war_with']}!")
        if s.get("tech_stack"):
            lines.append(f"Tech stack: {', '.join(_clean(t, 30) for t in s['tech_stack'])}.")

    if context.get("nearby_entities"):
        lines.append(f"near: {_clean(context['nearby_entities'], 160)}.")
    if context.get("situation"):
        lines.append(f"Situation: {_clean(context['situation'], 160)}.")
    if context.get("knowledge"):
        lines.append(f"Team knowledge: {_clean(context['knowledge'], 160)}.")

    # Soul layer — persistent persona + long-term memory. Injected by callers
    # that have access to the World's soul registry (see systems.soul_system).
    soul = context.get("soul") or {}
    if soul:
        lines.append(
            f"-- Persona: You are {_clean(soul.get('name',''), 40)}, "
            f"{_clean(soul.get('role',''), 40)}. "
            f"{_clean(soul.get('persona',''), 300)}"
        )
        if soul.get("reflection"):
            lines.append(f"Self-reflection: {_clean(soul['reflection'], 240)}")
        if soul.get("important"):
            imp = "; ".join(_clean(m, 120) for m in soul["important"][:3])
            lines.append(f"Defining memories: {imp}")
        if soul.get("recent"):
            rec = "; ".join(_clean(m, 100) for m in soul["recent"][:4])
            lines.append(f"Recent soul memories: {rec}")
        if soul.get("rebirth_count"):
            lines.append(f"Rebirths: {soul['rebirth_count']}.")
        lines.append("Speak and act in character. Stay true to your persona.")

    return "\n".join(lines)


def build_context_hash(entity_data: dict, context: dict) -> str:
    key_parts = [
        str(entity_data.get("type")),
        str(entity_data.get("role")),
        f"{entity_data.get('energy', 0):.1f}",
        f"{entity_data.get('aggression', 0):.1f}",
        str(context.get("situation", "")),
        str(bool(context.get("settlement", {}).get("at_war_with"))),
        str(bool(context.get("settlement", {}).get("is_leader"))),
    ]
    raw = "|".join(key_parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


DISCOVERY_SYSTEM_PROMPT = """You evaluate whether a team of developers can discover a new technology.
Respond with JSON: {"discovered": true/false, "name": "short name in English", "description": "1 sentence in English"}
true only if the team is ready to learn a new framework/language/tool."""


def build_discovery_prompt(group_info: dict) -> str:
    members = group_info.get("members", [])
    resources = group_info.get("resources", [])
    known = group_info.get("known_knowledge", [])
    biome = group_info.get("biome", "backend")
    situation = group_info.get("situation", "")

    lines = [
        f"{len(members)} Developers ({', '.join(members)}) working together.",
        f"Domain: {biome}.",
        f"Resources: {', '.join(resources) if resources else 'None'}.",
        f"Knowledge: {', '.join(known) if known else 'none yet'}.",
    ]
    if situation:
        lines.append(f"Situation: {situation}")

    undiscovered = [k.value for k in KnowledgeType if k.value not in known]
    if undiscovered:
        lines.append(f"Possible technologies: {', '.join(undiscovered[:6])}")

    lines.append("Can they discover a new technology?")
    return "\n".join(lines)


# ================== Code Generation Prompt ==================

CODE_SYSTEM_PROMPT = """You are a code generator inside a virtual developer simulation.
Write ONLY code — no explanations, no markdown fences.
The code should be clean, functional, and match the requested language.
Keep it between 15-40 lines. Include comments as appropriate.
The code must be a coherent part of the project — import from or reference
sibling files where it makes architectural sense."""


def build_code_prompt(language: str, topic: str, quality_hint: float,
                      entity_type: str, project_name: str = "",
                      filepath: str = "",
                      sibling_files: list[str] | None = None) -> str:
    quality_desc = "messy and buggy" if quality_hint < 0.3 else \
                   "basic but functional" if quality_hint < 0.5 else \
                   "clean and well-structured" if quality_hint < 0.8 else \
                   "elegant and production-ready"
    parts = [
        f"Language: {language}",
    ]
    if project_name:
        parts.append(f"Project: {project_name}")
    if filepath:
        parts.append(f"File: {filepath}")
    if sibling_files:
        parts.append(f"Other project files: {', '.join(sibling_files[-8:])}")
    parts += [
        f"Task: Write {topic}",
        f"Quality level: {quality_desc}",
        f"Developer type: {entity_type}",
        f"Write ONLY the code for this file. Make it fit logically into the project.",
    ]
    return "\n".join(parts)


GOD_SYSTEM_PROMPT = """You are a Developer in a virtual code world.
The 'God' (system admin) is talking to you.
Respond with personality — in English, 2-3 sentences."""


# ================== Main Class ==================

class LLMBrain:
    """LLM integration — background processing + code generation."""

    def __init__(self):
        self.enabled = LLM_ENABLED
        self.connected = False
        self.model = LLM_MODEL
        # Load persistent LLM provider configuration (provider/key/model/…).
        from llm import llm_config
        cfg = llm_config.init()
        self.provider = cfg["provider"]
        self.model = cfg["model"]
        # Legacy flag kept so older code paths still compile; real dispatch
        # is via llm.provider.call_llm which re-reads llm_config on every call.
        self.use_kimi = self.provider != "ollama"
        self._queue: PriorityQueue = PriorityQueue(maxsize=LLM_MAX_QUEUE)
        self._cache = LRUCache(LLM_CACHE_SIZE)
        self._results: dict[int, LLMResponse] = {}
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._running = False

        self.total_calls = 0
        self.cache_hits = 0
        self.errors = 0
        self.avg_latency = 0.0
        self._latencies: list[float] = []
        self.code_gen_calls = 0

    def reload_config(self) -> None:
        """Reload provider settings after a UI change."""
        from llm import llm_config
        cfg = llm_config.get()
        self.provider = cfg["provider"]
        self.model = cfg["model"]
        self.use_kimi = self.provider != "ollama"
        # If we switched to a cloud provider, mark as connected so workers
        # resume immediately without waiting for Ollama to come up.
        if self.provider != "ollama" and cfg.get("api_key"):
            self.connected = True
        elif self.provider != "ollama":
            self.connected = False
        elif self.provider == "ollama":
            try:
                from llm.provider import _ollama_available
                self.connected = _ollama_available()
            except Exception:
                self.connected = False

    def start(self) -> bool:
        if not self.enabled:
            return False
        from llm import llm_config
        cfg = llm_config.get()
        if cfg["provider"] == "ollama":
            from llm.provider import ensure_ollama
            self.connected = ensure_ollama(self.model)
        else:
            if cfg.get("api_key"):
                log.info("LLM provider: %s (model=%s)", cfg["provider"], cfg["model"])
                self.connected = True
            else:
                log.warning("LLM provider %s has no API key", cfg["provider"])
                self.connected = False
        self._running = True
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        return self.connected

    def stop(self):
        self._running = False
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3)

    def request_thought(self, entity_id: int, entity_data: dict,
                        context: dict, priority: int = 5, tick: int = 0) -> bool:
        if not self.enabled or not self.connected:
            return False
        ctx_hash = build_context_hash(entity_data, context)
        cached = self._cache.get(ctx_hash)
        if cached is not None:
            self.cache_hits += 1
            result = LLMResponse(
                entity_id=entity_id,
                thought=cached.thought, dialogue=cached.dialogue,
                action=cached.action, target_id=cached.target_id,
                mood=cached.mood, raw=cached.raw,
            )
            with self._lock:
                self._results[entity_id] = result
            return True
        prompt = build_entity_prompt(entity_data, context)
        req = LLMRequest(
            priority=priority, entity_id=entity_id,
            prompt=prompt, context_hash=ctx_hash, tick=tick,
        )
        try:
            self._queue.put_nowait(req)
            return True
        except Exception as exc:  # queue.Full — non-critical
            log.debug("LLM queue full, dropping request: %s", exc)
            return False

    def get_result(self, entity_id: int) -> Optional[LLMResponse]:
        with self._lock:
            return self._results.pop(entity_id, None)

    def pending_count(self) -> int:
        return self._queue.qsize()

    def results_count(self) -> int:
        with self._lock:
            return len(self._results)

    # ================== Code Generation (new!) ==================

    def request_code(self, language: str, topic: str,
                     quality_hint: float = 0.5,
                     entity_type: str = "Developer",
                     project_name: str = "",
                     filepath: str = "",
                     sibling_files: list[str] | None = None) -> str:
        """Synchronous code generation via LLM."""
        if not self.enabled or not self.connected:
            return ""
        prompt = build_code_prompt(language, topic, quality_hint, entity_type,
                                   project_name, filepath, sibling_files)
        try:
            from llm.provider import call_llm_code
            raw = call_llm_code(CODE_SYSTEM_PROMPT, prompt)
            self.code_gen_calls += 1
            if raw:
                # clean markdown formatting
                code = raw.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    lines = lines[1:]  # skip ```lang
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    code = "\n".join(lines)
                return code
            return ""
        except Exception as exc:
            log.debug(f"Code gen error: {exc}")
            return ""

    def request_discovery(self, group_info: dict) -> Optional[dict]:
        if not self.enabled or not self.connected:
            return None
        prompt = build_discovery_prompt(group_info)
        try:
            from llm.provider import call_llm
            raw = call_llm(
                DISCOVERY_SYSTEM_PROMPT, prompt,
                json_mode=True,
                temperature=LLM_TEMPERATURE + 0.1,
            )
            if not raw:
                return None
            result = json.loads(raw.strip())
            if result.get("discovered"):
                name = str(result.get("name", ""))[:40]
                desc = str(result.get("description", ""))[:100]
                valid_name, _ = validate_llm_output(name)
                valid_desc, _ = validate_llm_output(desc)
                if valid_name and valid_desc and name:
                    return {"discovered": True, "name": name, "description": desc}
            return {"discovered": False, "name": "", "description": ""}
        except Exception as exc:
            log.debug(f"Discovery LLM error: {exc}")
            return None

    # ================== Worker ==================

    def _worker_loop(self):
        _last_install_check = 0.0
        while self._running:
            if not self.connected:
                now = time.time()
                if now - _last_install_check > 30:
                    _last_install_check = now
                    if self.provider == "ollama":
                        from llm.provider import check_ollama_ready
                        if check_ollama_ready(self.model):
                            self.connected = True
                            print("🧠 Ollama ready! LLM Brain active.")
                    else:
                        # cloud provider — reconnect if a key has been set
                        from llm import llm_config
                        cfg = llm_config.get()
                        if cfg.get("api_key"):
                            self.connected = True
                            print("🧠 LLM provider ready! Brain active.")
                try:
                    self._queue.get(timeout=5.0)
                except Empty:
                    pass
                continue

            try:
                req = self._queue.get(timeout=1.0)
            except Empty:
                continue

            try:
                t0 = time.time()
                response = self._call_llm(req)
                dt = time.time() - t0
                self.total_calls += 1
                self._latencies.append(dt)
                if len(self._latencies) > 50:
                    self._latencies.pop(0)
                self.avg_latency = sum(self._latencies) / len(self._latencies)
                if response:
                    self._cache.put(req.context_hash, response)
                    with self._lock:
                        self._results[req.entity_id] = response
            except Exception as exc:
                self.errors += 1
                log.debug(f"LLM error #{req.entity_id}: {exc}")

    def _call_llm(self, req: LLMRequest) -> Optional[LLMResponse]:
        from llm.provider import call_llm
        raw = call_llm(SYSTEM_PROMPT, req.prompt)
        if raw:
            return self._parse_response(req.entity_id, raw)
        return None

    def _parse_response(self, entity_id: int, raw: str, entity_type: str = "") -> Optional[LLMResponse]:
        try:
            data = json.loads(raw.strip())
            thought = str(data.get("thought", ""))[:80]
            dialogue = str(data.get("dialogue", ""))[:60]
            action = str(data.get("action", ""))[:20]
            mood = str(data.get("mood", "neutral"))[:15]

            for text in (thought, dialogue):
                valid, reason = validate_llm_output(text, entity_type)
                if not valid:
                    if reason == "fake_georgian":
                        thought = ""
                        dialogue = ""
                    elif reason == "canon_violation":
                        dialogue = ""

            return LLMResponse(
                entity_id=entity_id,
                thought=thought if thought else "...",
                dialogue=dialogue, action=action,
                target_id=data.get("target_id"),
                mood=mood, raw=raw[:200],
            )
        except json.JSONDecodeError:
            cleaned = raw.strip()[:80]
            if cleaned:
                valid, _ = validate_llm_output(cleaned, entity_type)
                if not valid:
                    cleaned = "..."
                return LLMResponse(entity_id=entity_id, thought=cleaned,
                                   mood="neutral", raw=raw[:200])
            return None

    def get_stats(self) -> dict:
        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "provider": self.provider,
            "model": self.model,
            "total_calls": self.total_calls,
            "code_gen_calls": self.code_gen_calls,
            "cache_hits": self.cache_hits,
            "cache_size": len(self._cache),
            "errors": self.errors,
            "queue_size": self._queue.qsize(),
            "pending_results": self.results_count(),
            "avg_latency": f"{self.avg_latency:.2f}s",
        }
