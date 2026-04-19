# world3 — AI Code Ecosystem

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![LLM](https://img.shields.io/badge/LLM-Ollama-informational)](https://ollama.ai/)

A living simulation where AI developers, bugs, refactorers and copilots are
born, collaborate, write **real code** via a local LLM, commit to repos
and occasionally earn a **Soul** — a persistent persona with long-term
memory that survives save/load and even death (reincarnation).

> Watch a digital team of agents design, build and ship micro-projects
> while you sleep. Zero inference cost (Ollama).

---

## Features

- 🧬 **Code as life** — entities evolve, mate, work, argue, write code
- 🧠 **Selective Souls** — a scarce few carry persistent LTM + persona
- 🛠️ **Real output** — generated code lands in `output/` and can be pushed to GitHub
- 🎛️ **Live dashboard** — React/Vite, Flask + Socket.IO backend
- 🔌 **OpenClaw skill bridge** — talk to any soul from an external chat
- 💾 **Autosave** — world and souls survive restarts
- 🇬🇪 **Bilingual** — English-first, Georgian opt-in

---

## Quick start

```bash
# 1. Clone and install
git clone <this-repo> world3 && cd world3
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Unix
pip install -r requirements.txt

# 2. Configure
copy .env.example .env         # Windows
# cp .env.example .env         # Unix
# (optional) edit .env to set GITHUB_TOKEN, NEO4J_PASSWORD, etc.

# 3. (Optional) run Ollama for LLM brains
ollama pull llama3.2:3b
ollama serve

# 4. Run
python main.py
# then open http://127.0.0.1:5000
```

Or run with Docker:

```bash
docker compose up
```

---

## Project layout

```
world3/
├── core/              # world, entities, soul data model
├── systems/           # ecosystem, code_gen, settlement, soul_system, github
├── llm/               # Ollama + Kimi providers, prompts, cache
├── persistence/       # save/load, soul store, graph DB
├── api/               # Flask routes + Socket.IO server
├── dashboard/         # React/Vite frontend
├── openclaw-skill/    # external OpenClaw skill bridge
└── tests/             # pytest suite
```

---

## Selected docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — subsystem map
- [PAPER.md](PAPER.md) — research write-up (Soul architecture)
- [openclaw-skill/world3/README.md](openclaw-skill/world3/README.md) — OpenClaw bridge
- [.env.example](.env.example) — all configurable secrets

---

## Tests

```bash
pytest -q
```

---

## License

MIT — see [LICENSE](LICENSE).
