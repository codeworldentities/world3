"""Code World 3 — main file.

Startup:
    python main.py              — headless mode

In headless mode the simulation is managed from the dashboard.
Control: Pause, Speed, Save/Load — all via API.
"""

import logging
import os
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")


def _init_world():
    from core.world import World
    from persistence.save_load import load_world, get_autosave_path, get_latest_save

    world = World()

    autosave = get_autosave_path()
    latest = get_latest_save()
    load_path = None
    if os.path.exists(autosave):
        load_path = autosave
    if latest and (not load_path or os.path.getmtime(latest) > os.path.getmtime(load_path)):
        load_path = latest
    if load_path and load_world(world, load_path):
        print(f"📂 World restored: {os.path.basename(load_path)} (tick={world.tick})")
    else:
        print("🆕 New code world created")

    # output directory
    from config import CODE_OUTPUT_DIR
    os.makedirs(CODE_OUTPUT_DIR, exist_ok=True)

    return world


def _init_services(world):
    # Neo4j
    graph = None
    try:
        from persistence.graph_db import GraphDB
        graph = GraphDB()
        world.graph = graph
        if graph.connected:
            print("Neo4j ● Connected — graph active")
        else:
            print("Neo4j ○ Simulation running without graph")
    except ImportError:
        print("Neo4j ○ neo4j library not installed")
    except Exception as exc:
        print(f"Neo4j ○ error: {exc}")

    # LLM
    llm_ready = world.init_brain()
    if llm_ready:
        print(f"🧠 LLM ● Ollama ready — model: {world.brain.model}")
    else:
        print("🧠 LLM ○ Simulation running without LLM")

    # GitHub
    try:
        from config import GITHUB_TOKEN
        from systems.github_integration import configure as gh_configure
        if GITHUB_TOKEN:
            if gh_configure(GITHUB_TOKEN):
                from systems.github_integration import get_user
                print(f"🐙 GitHub ● Connected: {get_user()}")
            else:
                print("🐙 GitHub ○ Could not connect")
        else:
            print("🐙 GitHub ○ Token not configured")
    except Exception as exc:
        print(f"🐙 GitHub ○ error: {exc}")

    # API
    from api.server import start_api
    start_api(world, port=5000)

    return graph


def _autosave(world):
    try:
        from persistence.save_load import save_world, get_autosave_path
        path = save_world(world, get_autosave_path())
        print(f"💾 autosave: {path}")
    except Exception as exc:
        print(f"Autosave error: {exc}")


def _cleanup(world, graph):
    if graph and graph.connected:
        graph.close()
    if world.brain:
        world.brain.stop()


def run_headless(world, graph):
    from api.server import get_sim_paused, get_sim_speed
    from config import AUTOSAVE_INTERVAL

    print("━" * 50)
    print("💻 CODE WORLD — HEADLESS mode")
    print("📊 Dashboard: http://localhost:3000")
    print("🔌 API:       http://localhost:5000")
    print("━" * 50)

    running = True

    def _signal_handler(sig, frame):
        nonlocal running
        print("\n⏹ Shutting down...")
        running = False

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    last_autosave_tick = world.tick

    try:
        while running:
            if get_sim_paused():
                time.sleep(0.05)
                continue

            speed = get_sim_speed()
            for _ in range(speed):
                world.step()

            # autosave
            if world.tick - last_autosave_tick >= AUTOSAVE_INTERVAL:
                _autosave(world)
                last_autosave_tick = world.tick

            # print status
            if world.tick % 5000 == 0:
                alive = sum(1 for e in world.entities if e.alive)
                print(f"[tick {world.tick}] entities={alive} "
                      f"projects={len(world.settlements)} "
                      f"code={world.total_code_generated} "
                      f"era=v{world.era}.0")

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        print("📦 Final save...")
        _autosave(world)
        _cleanup(world, graph)
        print("✅ Code world stopped.")


def main():
    print("╔══════════════════════════════════════╗")
    print("║   CODE WORLD v3.0 — Code World   ║")
    print("╚══════════════════════════════════════╝")

    world = _init_world()
    graph = _init_services(world)
    run_headless(world, graph)


if __name__ == "__main__":
    main()
