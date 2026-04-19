"""Tests for systems/diplomacy.py — smoke tests for trade/war state transitions."""
from __future__ import annotations


def _tiny_world(tmp_path, monkeypatch):
    # Force autosave off for perf
    monkeypatch.setenv("WORLD3_TIER", "free")
    from core.world import World
    w = World()
    # Disable LLM to keep this deterministic
    w.brain = None
    return w


def test_update_trade_routes_runs_without_settlements(tmp_path, monkeypatch):
    from systems.diplomacy import update_trade_routes
    w = _tiny_world(tmp_path, monkeypatch)
    # No settlements yet — must not raise
    update_trade_routes(w)
    assert w.trade_routes == []


def test_execute_trades_safe_on_empty(tmp_path, monkeypatch):
    from systems.diplomacy import execute_trades
    w = _tiny_world(tmp_path, monkeypatch)
    execute_trades(w)  # no raise


def test_update_diplomacy_handles_no_settlements(tmp_path, monkeypatch):
    from systems.diplomacy import update_diplomacy
    w = _tiny_world(tmp_path, monkeypatch)
    update_diplomacy(w)


def test_update_wars_handles_no_wars(tmp_path, monkeypatch):
    from systems.diplomacy import update_wars
    w = _tiny_world(tmp_path, monkeypatch)
    update_wars(w)
    assert w.wars == []
