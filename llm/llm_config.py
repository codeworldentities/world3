"""Persistent LLM provider configuration.

Stores the user-selected LLM provider (ollama / openai / anthropic / gemini
/ deepseek / groq / openrouter / kimi / mistral / custom) together with its
API key and model in a small JSON file, so the choice survives restarts.

The file is read on startup by the LLM brain and can be mutated at runtime
via the /api/llm/config endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("llm.config")

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "saves" / "llm_config.json"
_LOCK = threading.Lock()

# Preset catalog — displayed to the user and used for validation.
# "key_env": optional environment variable fallback for the API key.
PROVIDERS: dict[str, dict[str, Any]] = {
    "ollama": {
        "label": "Ollama (local, free)",
        "requires_key": False,
        "base_url": "http://localhost:11434",
        "default_model": "llama3.2:3b",
        "models": [
            # Llama family
            "llama3.3:70b", "llama3.2:1b", "llama3.2:3b",
            "llama3.1:8b", "llama3.1:70b", "llama3.1:405b",
            "llama3:8b", "llama3:70b",
            # Qwen family
            "qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b",
            "qwen3.5:27b", "qwen3.5:35b", "qwen3.5:122b",
            # Requested custom alias/tag (if created locally or provided by a custom registry)
            "qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive",
            "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b",
            "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:72b",
            "qwen2.5-coder:1.5b", "qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen2.5-coder:32b",
            "qwq:32b",
            # Mistral / Mixtral
            "mistral:7b", "mistral-nemo:12b", "mistral-small:22b",
            "mixtral:8x7b", "mixtral:8x22b",
            # Phi
            "phi3:mini", "phi3:medium", "phi3.5:3.8b", "phi4:14b",
            # Gemma
            "gemma2:2b", "gemma2:9b", "gemma2:27b", "gemma3:4b", "gemma3:12b", "gemma3:27b",
            # DeepSeek
            "deepseek-coder-v2:16b", "deepseek-coder:6.7b", "deepseek-r1:7b",
            "deepseek-r1:14b", "deepseek-r1:32b", "deepseek-r1:70b",
            # Code-specialized
            "codellama:7b", "codellama:13b", "codellama:34b",
            "codegemma:7b", "starcoder2:3b", "starcoder2:15b",
            # Vision / multimodal
            "llava:7b", "llava:13b", "llama3.2-vision:11b", "llama3.2-vision:90b",
            # Embedding
            "nomic-embed-text", "mxbai-embed-large",
        ],
        "api_style": "ollama",
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "requires_key": True,
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": [
            # GPT-5 family (newest)
            "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-turbo",
            # GPT-4.1 family
            "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
            # GPT-4o family
            "gpt-4o", "gpt-4o-mini", "gpt-4o-2024-11-20", "gpt-4o-2024-08-06",
            "chatgpt-4o-latest",
            # Reasoning / o-series
            "o4-mini", "o3", "o3-mini", "o3-pro", "o1", "o1-mini", "o1-preview",
            # Legacy
            "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
        ],
        "api_style": "openai",
        "key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "requires_key": True,
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-haiku-4-7",
        "models": [
            # Claude 4.7 family (newest)
            "claude-opus-4-7", "claude-sonnet-4-7", "claude-haiku-4-7",
            # Claude 4.5 family
            "claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5",
            # Claude 4 family
            "claude-opus-4-1", "claude-opus-4-0",
            "claude-sonnet-4-1", "claude-sonnet-4-0",
            # Claude 3.7 / 3.5 family
            "claude-3-7-sonnet-latest", "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-latest", "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620",
            "claude-3-5-haiku-latest", "claude-3-5-haiku-20241022",
            # Legacy Claude 3
            "claude-3-opus-latest", "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
        ],
        "api_style": "anthropic",
        "key_env": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "label": "Google Gemini",
        "requires_key": True,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.5-flash",
        "models": [
            # Gemini 3.x (newest)
            "gemini-3.0-pro", "gemini-3.0-flash", "gemini-3.0-flash-lite",
            # Gemini 2.5
            "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
            "gemini-2.5-flash-thinking",
            # Gemini 2.0
            "gemini-2.0-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite",
            "gemini-2.0-flash-thinking-exp",
            # Gemini 1.5
            "gemini-1.5-pro", "gemini-1.5-pro-002",
            "gemini-1.5-flash", "gemini-1.5-flash-002", "gemini-1.5-flash-8b",
            # Experimental / vision
            "gemini-exp-1206", "gemini-pro-vision",
        ],
        "api_style": "gemini",
        "key_env": "GOOGLE_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "requires_key": True,
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": [
            "deepseek-chat", "deepseek-reasoner", "deepseek-coder",
            "deepseek-v3.1", "deepseek-v3", "deepseek-v2.5",
            "deepseek-r1", "deepseek-r1-lite", "deepseek-coder-v2",
            "deepseek-math", "deepseek-vl2",
        ],
        "api_style": "openai",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "groq": {
        "label": "Groq (fast free tier)",
        "requires_key": True,
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile", "llama-3.3-70b-specdec",
            "llama-3.1-8b-instant", "llama-3.1-70b-versatile", "llama-3.1-405b-reasoning",
            "llama3-groq-70b-8192-tool-use-preview",
            "llama3-groq-8b-8192-tool-use-preview",
            "llama-guard-3-8b",
            "mixtral-8x7b-32768", "gemma2-9b-it", "gemma-7b-it",
            "qwen-qwq-32b", "qwen-2.5-32b", "qwen-2.5-coder-32b",
            "deepseek-r1-distill-llama-70b", "deepseek-r1-distill-qwen-32b",
        ],
        "api_style": "openai",
        "key_env": "GROQ_API_KEY",
    },
    "openrouter": {
        "label": "OpenRouter (many models)",
        "requires_key": True,
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "models": [
            # Meta / Llama
            "meta-llama/llama-3.3-70b-instruct",
            "meta-llama/llama-3.1-405b-instruct",
            "meta-llama/llama-3.1-70b-instruct",
            "meta-llama/llama-3.1-8b-instruct",
            # Anthropic
            "anthropic/claude-opus-4-7", "anthropic/claude-sonnet-4-7",
            "anthropic/claude-haiku-4-7",
            "anthropic/claude-opus-4-5", "anthropic/claude-sonnet-4-5",
            "anthropic/claude-haiku-4-5",
            "anthropic/claude-3.7-sonnet", "anthropic/claude-3.5-sonnet",
            # OpenAI
            "openai/gpt-5", "openai/gpt-5-mini",
            "openai/gpt-4.1", "openai/gpt-4.1-mini", "openai/gpt-4o",
            "openai/gpt-4o-mini", "openai/o3", "openai/o3-mini", "openai/o4-mini",
            # Google
            "google/gemini-3.0-pro", "google/gemini-2.5-pro",
            "google/gemini-2.5-flash", "google/gemini-2.0-flash",
            # DeepSeek
            "deepseek/deepseek-chat", "deepseek/deepseek-r1",
            "deepseek/deepseek-v3",
            # Mistral / Qwen / others
            "mistralai/mistral-large", "mistralai/mixtral-8x22b-instruct",
            "qwen/qwen-2.5-72b-instruct", "qwen/qwq-32b-preview",
            "x-ai/grok-2", "x-ai/grok-beta",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "cohere/command-r-plus",
        ],
        "api_style": "openai",
        "key_env": "OPENROUTER_API_KEY",
    },
    "kimi": {
        "label": "Kimi (Moonshot)",
        "requires_key": True,
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "models": [
            "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k",
            "moonshot-v1-auto",
            "kimi-k2", "kimi-k1.5", "kimi-latest",
            "kimi-thinking-preview", "kimi-vision-preview",
        ],
        "api_style": "openai",
        "key_env": "KIMI_API_KEY",
    },
    "mistral": {
        "label": "Mistral AI",
        "requires_key": True,
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "models": [
            "mistral-large-latest", "mistral-large-2411", "mistral-large-2407",
            "mistral-medium-latest", "mistral-medium-3",
            "mistral-small-latest", "mistral-small-3.1",
            "ministral-8b-latest", "ministral-3b-latest",
            "open-mistral-nemo", "open-mixtral-8x22b", "open-mixtral-8x7b",
            "pixtral-large-latest", "pixtral-12b",
            "codestral-latest", "codestral-mamba",
        ],
        "api_style": "openai",
        "key_env": "MISTRAL_API_KEY",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "requires_key": True,
        "base_url": "",
        "default_model": "",
        "models": [],
        "api_style": "openai",
        "key_env": "CUSTOM_LLM_API_KEY",
    },
}


_DEFAULT: dict[str, Any] = {
    "provider": "ollama",
    "api_key": "",
    "model": PROVIDERS["ollama"]["default_model"],
    "base_url": PROVIDERS["ollama"]["base_url"],
    "temperature": 0.7,
    "max_tokens": 200,
}

_current: dict[str, Any] = {}


def _load_from_disk() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("llm_config: failed to load %s: %s", _CONFIG_PATH, exc)
        return {}


def _save_to_disk(data: dict[str, Any]) -> None:
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        log.warning("llm_config: failed to save %s: %s", _CONFIG_PATH, exc)


def _merged(loaded: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(_DEFAULT)
    cfg.update({k: v for k, v in loaded.items() if k in _DEFAULT})
    # Coerce provider to a known preset, fall back to ollama.
    if cfg["provider"] not in PROVIDERS:
        cfg["provider"] = "ollama"
    preset = PROVIDERS[cfg["provider"]]
    # If base_url is missing, inherit from preset.
    if not cfg.get("base_url"):
        cfg["base_url"] = preset["base_url"]
    if not cfg.get("model"):
        cfg["model"] = preset["default_model"]
    # API key fallback from environment when blank.
    if not cfg.get("api_key") and preset.get("key_env"):
        cfg["api_key"] = os.getenv(preset["key_env"], "")
    return cfg


def init() -> dict[str, Any]:
    """Load the config from disk once and return the merged snapshot."""
    with _LOCK:
        if _current:
            return dict(_current)
        _current.update(_merged(_load_from_disk()))
        return dict(_current)


def get() -> dict[str, Any]:
    with _LOCK:
        if not _current:
            _current.update(_merged(_load_from_disk()))
        return dict(_current)


def get_public() -> dict[str, Any]:
    """Return the current config with API key masked for UI display."""
    cfg = get()
    key = cfg.get("api_key") or ""
    masked = ""
    if key:
        masked = key[:4] + "…" + key[-4:] if len(key) > 10 else "set"
    return {
        "provider": cfg["provider"],
        "model": cfg["model"],
        "base_url": cfg["base_url"],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "has_key": bool(key),
        "key_preview": masked,
    }


def update(changes: dict[str, Any]) -> dict[str, Any]:
    """Apply partial changes, persist them, and return the new config."""
    with _LOCK:
        if not _current:
            _current.update(_merged(_load_from_disk()))

        new = dict(_current)
        if "provider" in changes:
            prov = str(changes["provider"])
            if prov not in PROVIDERS:
                raise ValueError(f"unknown provider: {prov}")
            new["provider"] = prov
            preset = PROVIDERS[prov]
            # When switching providers, refresh base_url/model to preset defaults
            # unless caller explicitly set them in the same request.
            if "base_url" not in changes:
                new["base_url"] = preset["base_url"]
            if "model" not in changes:
                new["model"] = preset["default_model"]

        for field in ("api_key", "model", "base_url"):
            if field in changes:
                val = changes[field]
                if val is None:
                    continue
                new[field] = str(val).strip()

        for field in ("temperature", "max_tokens"):
            if field in changes:
                try:
                    new[field] = float(changes[field]) if field == "temperature" else int(changes[field])
                except (TypeError, ValueError):
                    pass

        _current.clear()
        _current.update(_merged(new))
        _save_to_disk(_current)
        return dict(_current)


def list_providers() -> list[dict[str, Any]]:
    """Preset catalog for the UI (no secrets)."""
    return [
        {
            "id": pid,
            "label": meta["label"],
            "requires_key": meta["requires_key"],
            "default_model": meta["default_model"],
            "models": meta["models"],
            "base_url": meta["base_url"],
        }
        for pid, meta in PROVIDERS.items()
    ]
