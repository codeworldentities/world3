"""LLM Provider — Ollama/OpenAI-compatible interface."""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from config import (
    LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    KIMI_ENABLED, KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL,
    KIMI_MAX_TOKENS, KIMI_TEMPERATURE,
)

log = logging.getLogger("llm.provider")

OLLAMA_DIR = Path(__file__).resolve().parent.parent / ".ollama"
_install_process: Optional[subprocess.Popen] = None
_install_lock = threading.Lock()


def _ollama_available() -> bool:
    try:
        r = requests.get(f"{LLM_BASE_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except (requests.RequestException, OSError):
        return False


def _ollama_installed() -> bool:
    if shutil.which("ollama") is not None:
        return True
    local_path = OLLAMA_DIR / "ollama.exe"
    if local_path.exists():
        return True
    default_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return default_path.exists()


def _model_exists(model: str) -> bool:
    try:
        r = requests.get(f"{LLM_BASE_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            for m in models:
                if m.get("name", "").startswith(model.split(":")[0]):
                    return True
    except (requests.RequestException, OSError, ValueError) as exc:
        log.debug("model_exists check failed: %s", exc)
    return False


def _get_ollama_cmd() -> str:
    which = shutil.which("ollama")
    if which:
        return which
    local = OLLAMA_DIR / "ollama.exe"
    if local.exists():
        return str(local)
    default = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    if default.exists():
        return str(default)
    return "ollama"


def _install_ollama() -> bool:
    global _install_process
    if platform.system() != "Windows":
        log.warning("auto-install only on Windows")
        return False
    with _install_lock:
        if _install_process is not None:
            if _install_process.poll() is None:
                return False
            _install_process = None
            if _ollama_installed():
                return True
            return False
        OLLAMA_DIR.mkdir(parents=True, exist_ok=True)
        print("🧠 Ollama installing in background...")
        try:
            _install_process = subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command",
                 f"$env:OLLAMA_INSTALL_DIR='{OLLAMA_DIR}'; "
                 f"irm https://ollama.com/install.ps1 | iex"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return False
        except Exception as exc:
            log.warning(f"install.ps1 failed: {exc}")
            return False


def _start_ollama_serve() -> bool:
    cmd = _get_ollama_cmd()
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if platform.system() == "Windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen([cmd, "serve"], **kwargs)
        for i in range(30):
            time.sleep(1)
            if _ollama_available():
                return True
        return False
    except Exception:
        return False


def _pull_model(model: str) -> bool:
    print(f"🧠 Pulling model {model}...")
    try:
        r = requests.post(
            f"{LLM_BASE_URL}/api/pull",
            json={"name": model}, timeout=600, stream=True,
        )
        for line in r.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if data.get("status") == "success":
                        break
                except json.JSONDecodeError:
                    pass
        print(f"✅ Model {model} ready!")
        return True
    except Exception as exc:
        log.warning(f"Model pull failed: {exc}")
        return False


def ensure_ollama(model: str = LLM_MODEL) -> bool:
    if _ollama_available():
        if not _model_exists(model):
            return _pull_model(model)
        return True
    if _ollama_installed():
        if _start_ollama_serve():
            if not _model_exists(model):
                return _pull_model(model)
            return True
        return False
    _install_ollama()
    return False


def check_ollama_ready(model: str = LLM_MODEL) -> bool:
    if _ollama_available():
        if not _model_exists(model):
            return _pull_model(model)
        return True
    if _ollama_installed():
        if _start_ollama_serve():
            if not _model_exists(model):
                return _pull_model(model)
            return True
    with _install_lock:
        if _install_process is not None and _install_process.poll() is None:
            return False
        if _install_process is not None:
            globals()["_install_process"] = None
    if _ollama_installed():
        if _start_ollama_serve():
            if not _model_exists(model):
                return _pull_model(model)
            return True
    return False


def call_ollama(system_prompt: str, user_prompt: str,
                temperature: float = LLM_TEMPERATURE,
                max_tokens: int = LLM_MAX_TOKENS,
                json_mode: bool = True,
                model: str = LLM_MODEL,
                max_retries: int = 2) -> Optional[str]:
    """Call Ollama with exponential-backoff retry on transient errors."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(f"{LLM_BASE_URL}/api/chat", json=payload, timeout=LLM_TIMEOUT)
            if r.status_code == 200:
                return r.json().get("message", {}).get("content", "")
            # 4xx non-retryable; 5xx retryable
            if 400 <= r.status_code < 500:
                log.warning("Ollama HTTP %s (no retry)", r.status_code)
                return None
            log.warning("Ollama HTTP %s (attempt %d/%d)",
                        r.status_code, attempt + 1, max_retries + 1)
        except requests.Timeout as exc:
            last_exc = exc
            log.warning("Ollama timeout (attempt %d/%d)",
                        attempt + 1, max_retries + 1)
        except requests.ConnectionError as exc:
            last_exc = exc
            log.warning("Ollama connection error (attempt %d/%d): %s",
                        attempt + 1, max_retries + 1, exc)
        except (requests.RequestException, ValueError, OSError) as exc:
            last_exc = exc
            log.debug("Ollama error (attempt %d/%d): %s",
                      attempt + 1, max_retries + 1, exc)
        if attempt < max_retries:
            time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s
    if last_exc is not None:
        log.warning("Ollama gave up after %d attempts: %s",
                    max_retries + 1, last_exc)
    return None


def call_ollama_code(system_prompt: str, user_prompt: str,
                     temperature: float = 0.4,
                     max_tokens: int = 300,
                     model: str = LLM_MODEL) -> Optional[str]:
    """Code generation — without JSON mode, to return clean code."""
    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        r = requests.post(f"{LLM_BASE_URL}/api/chat", json=payload, timeout=LLM_TIMEOUT + 5)
        if r.status_code != 200:
            return None
        return r.json().get("message", {}).get("content", "")
    except (requests.RequestException, ValueError, OSError) as exc:
        log.debug("Ollama code call failed: %s", exc)
        return None


def call_openai_compatible(system_prompt: str, user_prompt: str,
                           base_url: str = KIMI_BASE_URL,
                           api_key: str = KIMI_API_KEY,
                           model: str = KIMI_MODEL,
                           temperature: float = KIMI_TEMPERATURE,
                           max_tokens: int = KIMI_MAX_TOKENS,
                           json_mode: bool = True) -> Optional[str]:
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        r = requests.post(
            f"{base_url}/chat/completions",
            headers=headers, json=payload,
            timeout=LLM_TIMEOUT + 5,
        )
        if r.status_code != 200:
            log.debug(f"OpenAI-compatible HTTP {r.status_code}: {r.text[:200]}")
            return None
        return r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except (requests.RequestException, ValueError, OSError) as exc:
        log.debug(f"OpenAI-compatible error: {exc}")
        return None


# ====================================================================
#  Multi-provider dispatch (Anthropic / Gemini / OpenAI-compatible /
#  Ollama). The active provider is read from `llm.llm_config` on every
#  call, so changes made via the UI take effect immediately.
# ====================================================================


def call_anthropic(system_prompt: str, user_prompt: str,
                   base_url: str, api_key: str, model: str,
                   temperature: float, max_tokens: int,
                   json_mode: bool = True) -> Optional[str]:
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        sys_text = system_prompt
        if json_mode:
            sys_text = f"{system_prompt}\nRespond with a single valid JSON object and nothing else."
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": sys_text,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        r = requests.post(
            f"{base_url}/messages", headers=headers, json=payload,
            timeout=LLM_TIMEOUT + 5,
        )
        if r.status_code != 200:
            log.debug("Anthropic HTTP %s: %s", r.status_code, r.text[:200])
            return None
        data = r.json()
        blocks = data.get("content") or []
        # content is a list of blocks like {type: 'text', text: '...'}
        for b in blocks:
            if b.get("type") == "text":
                return b.get("text", "")
        return None
    except (requests.RequestException, ValueError, OSError) as exc:
        log.debug("Anthropic error: %s", exc)
        return None


def call_gemini(system_prompt: str, user_prompt: str,
                base_url: str, api_key: str, model: str,
                temperature: float, max_tokens: int,
                json_mode: bool = True) -> Optional[str]:
    try:
        url = f"{base_url}/models/{model}:generateContent"
        payload: dict = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        r = requests.post(
            url, params={"key": api_key}, json=payload,
            timeout=LLM_TIMEOUT + 5,
        )
        if r.status_code != 200:
            log.debug("Gemini HTTP %s: %s", r.status_code, r.text[:200])
            return None
        data = r.json()
        cands = data.get("candidates") or []
        if not cands:
            return None
        parts = cands[0].get("content", {}).get("parts") or []
        for p in parts:
            if "text" in p:
                return p["text"]
        return None
    except (requests.RequestException, ValueError, OSError) as exc:
        log.debug("Gemini error: %s", exc)
        return None


def _call_configured(system_prompt: str, user_prompt: str,
                     *, json_mode: bool = True,
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None) -> Optional[str]:
    """Dispatch to the provider chosen in llm.llm_config."""
    from llm import llm_config
    cfg = llm_config.get()
    provider = cfg["provider"]
    temp = cfg["temperature"] if temperature is None else temperature
    mx = cfg["max_tokens"] if max_tokens is None else max_tokens
    model = cfg["model"]
    base = cfg["base_url"]
    key = cfg["api_key"]

    preset = llm_config.PROVIDERS.get(provider, {})
    style = preset.get("api_style", "openai")

    if provider == "ollama" or style == "ollama":
        return call_ollama(
            system_prompt, user_prompt,
            temperature=temp, max_tokens=mx,
            json_mode=json_mode, model=model,
        )
    if style == "anthropic":
        return call_anthropic(
            system_prompt, user_prompt,
            base_url=base, api_key=key, model=model,
            temperature=temp, max_tokens=mx, json_mode=json_mode,
        )
    if style == "gemini":
        return call_gemini(
            system_prompt, user_prompt,
            base_url=base, api_key=key, model=model,
            temperature=temp, max_tokens=mx, json_mode=json_mode,
        )
    # default: OpenAI-compatible
    return call_openai_compatible(
        system_prompt, user_prompt,
        base_url=base, api_key=key, model=model,
        temperature=temp, max_tokens=mx, json_mode=json_mode,
    )


def call_llm(system_prompt: str, user_prompt: str,
             json_mode: bool = True,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> Optional[str]:
    """Public entry point for JSON/text LLM calls."""
    return _call_configured(
        system_prompt, user_prompt,
        json_mode=json_mode,
        temperature=temperature, max_tokens=max_tokens,
    )


def call_llm_code(system_prompt: str, user_prompt: str,
                  temperature: float = 0.4,
                  max_tokens: int = 300) -> Optional[str]:
    """Code generation — never JSON mode."""
    return _call_configured(
        system_prompt, user_prompt,
        json_mode=False,
        temperature=temperature, max_tokens=max_tokens,
    )


def test_current_provider() -> dict:
    """Round-trip test against the currently configured provider.
    Returns {ok: bool, provider, model, answer?, error?, latency_ms}."""
    from llm import llm_config
    cfg = llm_config.get()
    t0 = time.time()
    try:
        raw = _call_configured(
            "You are a helper. Respond briefly.",
            "Reply with the single word: READY",
            json_mode=False, temperature=0.0, max_tokens=20,
        )
        dt = int((time.time() - t0) * 1000)
        if not raw:
            return {"ok": False, "provider": cfg["provider"],
                    "model": cfg["model"], "error": "no response",
                    "latency_ms": dt}
        return {"ok": True, "provider": cfg["provider"],
                "model": cfg["model"], "answer": raw.strip()[:120],
                "latency_ms": dt}
    except Exception as exc:
        dt = int((time.time() - t0) * 1000)
        return {"ok": False, "provider": cfg["provider"],
                "model": cfg["model"], "error": str(exc)[:200],
                "latency_ms": dt}
