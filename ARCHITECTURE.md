# Architecture

world3 is a tick-based multi-agent simulation with an attached LLM and
persistence layer. This document is a map, not a spec — see code for detail.

## 30-second overview

```
┌──────────────────┐     ┌────────────────────┐     ┌──────────────┐
│  Dashboard (Vite)│◀──▶│  Flask + SocketIO   │◀──▶│   World      │
│  React UI        │     │  api/server.py      │     │  core/world  │
└──────────────────┘     └─────────┬──────────┘     └──────┬───────┘
                                   │                        │
                                   ▼                        ▼
                         ┌──────────────────┐    ┌──────────────────┐
                         │  routes.py       │    │  systems/*       │
                         │  /api/*          │    │  ecosystem,      │
                         │  /souls          │    │  code_gen,       │
                         └──────────────────┘    │  settlement,     │
                                   │              │  soul_system,   │
                                   ▼              │  github         │
                         ┌──────────────────┐    └────────┬─────────┘
                         │  persistence/*   │             │
                         │  save_load,      │             ▼
                         │  soul_store,     │    ┌──────────────────┐
                         │  audit,          │    │   llm/brain      │
                         │  graph_db        │    │   Ollama / Kimi  │
                         └──────────────────┘    └──────────────────┘
```

## Directories

| Path | Role |
|---|---|
| `core/` | world, entities, enums, dataclasses, soul data model |
| `systems/` | pure functions advancing one subsystem per tick |
| `llm/` | prompt construction, validator, async request queue, providers |
| `persistence/` | save/load world, soul store, audit log, Neo4j graph sync |
| `api/` | Flask app, routes, Socket.IO broadcast loop |
| `dashboard/` | React/Vite front-end |
| `openclaw-skill/world3/` | external skill pack for OpenClaw |
| `static/souls.html` | soul gallery web page |
| `tests/` | pytest |

## Tick flow (`World.step()`)

1. Signals decay
2. Spawn resources
3. Update each entity (move, perceive, act)
4. Particles
5. Deaths → legacy & **soul reincarnation**
6. Ecosystem balance
7. Stats
8. Emergency respawn
9. Territories (every 50)
10. Shared project (every 50)
11. Crafting (every 200)
12. Knowledge discovery
13. Code sharing
14. Diplomacy + wars
15. Team lead elections
16. **Code generation + review + natural bugs**
17. **LLM thinking + conversations**
18. Neo4j sync
19. **Soul granting / reflection / soul-to-soul dialogue**

## Soul layer (summary — see `PAPER.md`)

- Every entity has an optional `soul_id`.
- Souls live in `World.souls: dict[str, Soul]`, persisted as
  `saves/souls/<id>.json` + `saves/souls/<id>.md`.
- Granted selectively to leaders, architects, AI copilots, or elders.
- On death a heir is chosen and the soul migrates; otherwise it goes
  dormant and can be re-bound later.
- Reflection and memory compression run every 500 ticks via LLM when
  available, otherwise via deterministic fallback.

## Configuration

All runtime knobs live in `config.py`. Secrets are loaded from `.env`
via `python-dotenv`. Tier quotas (`WORLD3_TIER=free|pro|enterprise`)
cap `MAX_SOULS` and `MAX_GITHUB_PUSHES_PER_DAY`.

## Testing

`pytest -q` runs world init, stepping, soul granting, save/load round-trip
and API smoke tests. Soul-store tests isolate to a temp directory.
