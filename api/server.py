"""API Server — Flask + WebSocket (code world)."""

from __future__ import annotations

import logging
import os
import threading
import time

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

from config import API_CORS_ORIGINS

log = logging.getLogger("api.server")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
CORS(app, resources={r"/api/*": {"origins": API_CORS_ORIGINS}})
socketio = SocketIO(app, cors_allowed_origins=API_CORS_ORIGINS, async_mode="threading")

_world = None
_world_lock = threading.Lock()

_sim_paused = False
_sim_speed = 1


def set_world(world):
    global _world
    with _world_lock:
        _world = world


def get_world():
    with _world_lock:
        return _world


def get_sim_paused():
    return _sim_paused


def set_sim_paused(val: bool):
    global _sim_paused
    _sim_paused = val


def get_sim_speed():
    return _sim_speed


def set_sim_speed(val: int):
    global _sim_speed
    _sim_speed = max(1, min(32, val))


# ================== WebSocket Translation ==================

_broadcast_running = False


def _broadcast_loop():
    global _broadcast_running
    _broadcast_running = True
    last_events_snap = ()
    last_convos_snap = ()
    while _broadcast_running:
        w = get_world()
        if w:
            try:
                # Snapshot mutable collections first; the simulation thread
                # may mutate w.entities / w.events concurrently, so we copy
                # references under no expensive work. tuple() is atomic for
                # reference-typed lists in CPython and avoids "size changed
                # during iteration" errors.
                entities_snap = tuple(w.entities)
                events_snap = tuple(w.events[-5:]) if w.events else ()
                convos_snap = tuple(w.conversations[-3:]) if w.conversations else ()

                type_counts = {}
                for e in entities_snap:
                    tname = e.entity_type.value
                    type_counts[tname] = type_counts.get(tname, 0) + 1

                snapshot = {
                    "tick": w.tick,
                    "entities": len(entities_snap),
                    "resources": len(w.resources),
                    "settlements": len(w.settlements),
                    "type_counts": type_counts,
                    "time_label": w.time_label,
                    "era": w.era,
                    "light_level": round(w.light_level, 2),
                    "paused": _sim_paused,
                    "speed": _sim_speed,
                    "knowledge_count": w.total_knowledge_discovered,
                    "total_code": w.total_code_generated,
                }
                socketio.emit("world_tick", snapshot)

                # Emit events only when there is a real delta; otherwise the
                # UI receives the same tail repeatedly and shows duplicates.
                if events_snap and events_snap != last_events_snap:
                    socketio.emit("events", list(events_snap))
                    last_events_snap = events_snap

                if convos_snap and convos_snap != last_convos_snap:
                    socketio.emit("conversations", list(convos_snap))
                    last_convos_snap = convos_snap

            except Exception as exc:
                log.debug(f"Broadcast error: {exc}")
        time.sleep(0.5)


def start_broadcast():
    t = threading.Thread(target=_broadcast_loop, daemon=True)
    t.start()


def stop_broadcast():
    global _broadcast_running
    _broadcast_running = False


# ================== Server Startup ==================

_server_thread = None
_server_started_at = time.time()


def get_server_uptime_seconds() -> float:
    return max(0.0, time.time() - _server_started_at)


def start_api(world, port: int = 5000):
    global _server_thread
    set_world(world)

    from api.routes import register_routes
    register_routes(app)

    def _run():
        start_broadcast()
        socketio.run(app, host="0.0.0.0", port=port,
                     debug=False, use_reloader=False,
                     allow_unsafe_werkzeug=True,
                     log_output=False)

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()
    log.info(f"API started: http://localhost:{port}")
    print(f"🖥 Code World API ● http://localhost:{port}")
    return True


def stop_api():
    stop_broadcast()
