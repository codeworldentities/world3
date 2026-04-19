"""Shared HTTP helpers for the world3 OpenClaw skill."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


def api_base() -> str:
    return os.environ.get("WORLD3_API", "http://127.0.0.1:5000").rstrip("/")


def _request(method: str, path: str, payload: dict | None = None, timeout: float = 10.0):
    url = api_base() + path
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def get(path: str, **params) -> dict:
    if params:
        path = path + "?" + urllib.parse.urlencode(params)
    return _request("GET", path)


def post(path: str, payload: dict | None = None) -> dict:
    return _request("POST", path, payload=payload)
