"""Benchmark configured LLM providers/models for world3.

Runs a small, repeatable test suite over selected candidates and prints
latency + simple quality signals. Restores original llm_config afterwards.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
import requests

from llm import llm_config
from llm.provider import call_llm, call_llm_code, test_current_provider


@dataclass
class Candidate:
    provider: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None


@dataclass
class Result:
    provider: str
    model: str
    ok: bool
    latency_ms: int
    handshake_ok: bool
    reasoning_chars: int
    code_chars: int
    code_looks_valid: bool
    error: str = ""


def _looks_like_code(txt: str) -> bool:
    t = txt or ""
    needles = ("def ", "function ", "class ", "import ", "return ")
    return any(n in t for n in needles)


def _run_single(c: Candidate) -> Result:
    changes: dict[str, object] = {
        "provider": c.provider,
        "model": c.model,
    }
    if c.base_url:
        changes["base_url"] = c.base_url
    if c.api_key_env:
        changes["api_key"] = os.getenv(c.api_key_env, "")

    if c.provider != "ollama" and c.api_key_env and not str(changes.get("api_key", "")).strip():
        return Result(
            provider=c.provider,
            model=c.model,
            ok=False,
            latency_ms=0,
            handshake_ok=False,
            reasoning_chars=0,
            code_chars=0,
            code_looks_valid=False,
            error=f"missing API key in env: {c.api_key_env}",
        )

    if c.provider == "ollama":
        base = c.base_url or "http://localhost:11434"
        try:
            resp = requests.get(f"{base}/api/tags", timeout=2)
            if resp.status_code != 200:
                return Result(
                    provider=c.provider,
                    model=c.model,
                    ok=False,
                    latency_ms=0,
                    handshake_ok=False,
                    reasoning_chars=0,
                    code_chars=0,
                    code_looks_valid=False,
                    error=f"ollama not ready: HTTP {resp.status_code}",
                )
        except requests.RequestException as exc:
            return Result(
                provider=c.provider,
                model=c.model,
                ok=False,
                latency_ms=0,
                handshake_ok=False,
                reasoning_chars=0,
                code_chars=0,
                code_looks_valid=False,
                error=f"ollama not reachable at {base}: {exc}",
            )

    llm_config.update(changes)

    t0 = time.time()
    hs = test_current_provider()
    latency_ms = int((time.time() - t0) * 1000)

    if not hs.get("ok"):
        return Result(
            provider=c.provider,
            model=c.model,
            ok=False,
            latency_ms=latency_ms,
            handshake_ok=False,
            reasoning_chars=0,
            code_chars=0,
            code_looks_valid=False,
            error=str(hs.get("error", "handshake failed")),
        )

    t1 = time.time()
    reasoning = call_llm(
        "You are concise and technical.",
        "Explain in one short sentence why test coverage matters.",
        json_mode=False,
        temperature=0.2,
        max_tokens=80,
    ) or ""
    code = call_llm_code(
        "You write clean production code.",
        "Write a Python function fibonacci(n) that returns nth fibonacci number.",
        temperature=0.2,
        max_tokens=180,
    ) or ""
    latency_ms = int((time.time() - t1) * 1000)

    return Result(
        provider=c.provider,
        model=c.model,
        ok=True,
        latency_ms=latency_ms,
        handshake_ok=True,
        reasoning_chars=len(reasoning),
        code_chars=len(code),
        code_looks_valid=_looks_like_code(code),
        error="",
    )


def main() -> None:
    original = llm_config.get()

    candidates = [
        Candidate("ollama", "llama3.1:8b", "http://localhost:11434"),
        Candidate("ollama", "qwen3.5:9b", "http://localhost:11434"),
        Candidate("ollama", "qwen3.5:35b", "http://localhost:11434"),
        Candidate("openrouter", "meta-llama/llama-3.1-405b-instruct", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ]

    results: list[Result] = []
    try:
        for c in candidates:
            print(f"\n=== Testing {c.provider}:{c.model} ===")
            try:
                r = _run_single(c)
            except Exception as exc:
                r = Result(
                    provider=c.provider,
                    model=c.model,
                    ok=False,
                    latency_ms=0,
                    handshake_ok=False,
                    reasoning_chars=0,
                    code_chars=0,
                    code_looks_valid=False,
                    error=str(exc),
                )
            results.append(r)
            print(json.dumps(asdict(r), ensure_ascii=False, indent=2))
    finally:
        llm_config.update(
            {
                "provider": original.get("provider", "ollama"),
                "model": original.get("model", "llama3.2:3b"),
                "base_url": original.get("base_url", "http://localhost:11434"),
                "api_key": original.get("api_key", ""),
                "temperature": original.get("temperature", 0.7),
                "max_tokens": original.get("max_tokens", 200),
            }
        )

    out = Path("output") / "llm_benchmark_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSaved:", out)
    ok_results = [r for r in results if r.ok]
    if ok_results:
        best = sorted(ok_results, key=lambda x: (not x.code_looks_valid, x.latency_ms))[0]
        print(f"Best currently reachable: {best.provider}:{best.model} | latency={best.latency_ms}ms")
    else:
        print("No candidate was reachable. Check Ollama service and API keys.")


if __name__ == "__main__":
    main()
