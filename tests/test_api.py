"""API route smoke tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def api_client():
    from flask import Flask
    from api.routes import register_routes
    from api import server as api_server
    from core.world import World

    w = World()
    api_server.set_world(w)
    app = Flask(__name__)
    # register_routes pulls socketio + paused state lazily; we only need routes.
    # It imports get_world from api.server which we've just primed.
    register_routes(app)
    app.config["TESTING"] = True
    return app.test_client(), w


def test_status_endpoint(api_client):
    client, _ = api_client
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.get_json()
    assert "error" not in data or data.get("error") is None


def test_souls_endpoint_empty(api_client):
    client, _ = api_client
    r = client.get("/api/souls")
    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 0
    assert data["souls"] == []


def test_soul_404(api_client):
    client, _ = api_client
    r = client.get("/api/soul/nonexistent")
    assert r.status_code == 404


def test_soul_memory_injection(api_client):
    from systems.soul_system import grant_soul

    client, w = api_client
    for _ in range(3):
        w.step()
    e = next(x for x in w.entities if x.alive)
    s = grant_soul(w, e)

    r = client.post(f"/api/soul/{s.id}/memory",
                    json={"text": "user said hi", "weight": 0.6})
    assert r.status_code == 200
    assert r.get_json()["memories"] >= 2


def test_soul_memory_rejects_long_text(api_client):
    from systems.soul_system import grant_soul

    client, w = api_client
    for _ in range(3):
        w.step()
    e = next(x for x in w.entities if x.alive)
    s = grant_soul(w, e)

    r = client.post(f"/api/soul/{s.id}/memory", json={"text": "x" * 500})
    assert r.status_code == 400
