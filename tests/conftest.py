"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sys

# Ensure repo root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest


@pytest.fixture(autouse=True)
def _isolate_disk_state(tmp_path, monkeypatch):
    """Redirect soul store, save dir, and audit log to a temp dir per test.

    Prevents persisted state from prior runs (including the real
    `saves/souls/` folder) from leaking into unit tests — especially
    important because lazy-load in `World.step()` would otherwise hit
    the tier cap on the first tick.
    """
    import persistence.soul_store as ss
    import persistence.audit as au
    import persistence.save_load as sl

    monkeypatch.setattr(ss, "SOUL_DIR", str(tmp_path / "souls"))
    monkeypatch.setattr(au, "AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setattr(sl, "SAVE_DIR", str(tmp_path / "saves"))
    yield


@pytest.fixture
def fresh_world():
    """Return a freshly initialised World. Slow (~1–2s)."""
    from core.world import World
    return World()
