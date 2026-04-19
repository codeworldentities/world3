"""Push Code World v3 main repo to GitHub with README only."""

import json
import os
import base64
import time
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = "codeworldentities"
REPO = "world3"
API = "https://api.github.com"


def api(method, path, data=None):
    url = f"{API}{path}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CodeWorld/3.0",
    }
    body = json.dumps(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {e.code}: {err}")


def push_file(path, content, message):
    b64 = base64.b64encode(content.encode()).decode()
    data = {
        "message": message,
        "content": b64,
        "branch": "main",
    }
    # Check if file exists to get SHA for update
    try:
        existing = api("GET", f"/repos/{USER}/{REPO}/contents/{path}")
        data["sha"] = existing["sha"]
    except:
        pass
    api("PUT", f"/repos/{USER}/{REPO}/contents/{path}", data)


def main():
    if not TOKEN:
        print("No token!")
        return

    # Create repo
    print("Creating repo...")
    try:
        api("GET", f"/repos/{USER}/{REPO}")
        print("Repo already exists, updating...")
    except:
        api("POST", "/user/repos", {
            "name": REPO,
            "description": "An autonomous AI civilization simulator — hundreds of AI entities live, collaborate, and push real code to GitHub",
            "private": False,
            "auto_init": True,
            "has_issues": True,
            "has_discussions": True,
            "homepage": "https://diveloper.digital/",
        })
        time.sleep(3)
        print("Repo created!")

    # Update repo settings
    try:
        api("PATCH", f"/repos/{USER}/{REPO}", {
            "description": "An autonomous AI civilization simulator — hundreds of AI entities live, collaborate, and push real code to GitHub",
            "homepage": "https://diveloper.digital/",
            "topics": ["ai", "simulation", "autonomous-agents", "multi-agent", "code-generation", "llm", "artificial-life", "emergent-behavior", "flask", "react"],
        })
    except:
        pass

    # Set topics
    try:
        api("PUT", f"/repos/{USER}/{REPO}/topics", {
            "names": ["ai", "simulation", "autonomous-agents", "multi-agent", "code-generation", "llm", "artificial-life", "emergent-behavior", "flask", "react", "python", "open-source", "ai-agents", "generative-ai"]
        })
    except:
        pass

    # Push README
    print("Pushing README.md...")
    push_file("README.md", README_CONTENT, "🌍 Code World v3 — project documentation")
    time.sleep(1)

    # Push FUNDING.yml for GitHub Sponsors / donation
    print("Pushing .github/FUNDING.yml...")
    push_file(".github/FUNDING.yml", FUNDING_CONTENT, "💖 Add funding / donation links")
    time.sleep(1)

    # Push LICENSE
    print("Pushing LICENSE...")
    push_file("LICENSE", LICENSE_CONTENT, "📄 MIT License")
    time.sleep(1)

    # Push ARCHITECTURE.md
    print("Pushing ARCHITECTURE.md...")
    push_file("ARCHITECTURE.md", ARCHITECTURE_CONTENT, "🏗️ System architecture documentation")
    time.sleep(1)

    # Push CONTRIBUTING.md
    print("Pushing CONTRIBUTING.md...")
    push_file("CONTRIBUTING.md", CONTRIBUTING_CONTENT, "🤝 Contributing guidelines")

    print("\n✅ Done! https://github.com/codeworldentities/world3")


# ============================================================
# FILE CONTENTS
# ============================================================

README_CONTENT = r"""<div align="center">

<img src="https://img.shields.io/badge/Code_World-v3.0_Beta-00d4ff?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjEwIiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiLz48dGV4dCB4PSI3IiB5PSIxNiIgZm9udC1zaXplPSIxMCIgZmlsbD0id2hpdGUiPiZsdDsvJmd0Ozwvc3ZnPg==&labelColor=0d1117" alt="Code World v3.0 Beta" />

# 🌍 CODE WORLD v3

### An Autonomous AI Civilization Simulator

*Hundreds of AI entities live, form settlements, collaborate on software projects, and push real code to GitHub — all autonomously.*

[![Python](https://img.shields.io/badge/Python-3.13-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-18.3-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![SocketIO](https://img.shields.io/badge/Socket.IO-Realtime-010101?style=flat-square&logo=socket.io&logoColor=white)](https://socket.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Beta-yellow?style=flat-square)]()

<br/>

**[🌐 Live Dashboard](https://diveloper.digital/)** · **[📂 Generated Projects](https://github.com/codeworldentities?tab=repositories)** · **[💖 Support This Project](#-support--sponsorship)**

<br/>

---

</div>

## 🧬 What is Code World?

Code World is a **living simulation** where AI-powered entities exist in a 6000×4000 virtual world. They aren't just following scripts — they **think**, **learn**, **form teams**, **architect projects**, and **write real code** that gets pushed to GitHub.

Every entity has:
- 🧠 **Personality traits** — curiosity, sociability, resilience, aggression
- 💼 **Roles** — Architect, Team Lead, Reviewer, Tester, Freelancer, DevOps
- 🗣️ **Languages** — Python, JavaScript, Rust, Go, HTML/CSS, SQL
- 🕯️ **Souls** — persistent memory that survives death and reincarnates
- 📈 **XP & Leveling** — entities level up through commits and collaboration
- 🧬 **Genetics** — traits are inherited across generations

```
┌─────────────────────────────────────────────────────────┐
│                    CODE WORLD v3                         │
│                                                         │
│   🔵🔵🔵 ← Developer cluster working on "HexGrid"      │
│     🔴      ← Bug entity corrupting code                │
│   🟢        ← Teacher mentoring juniors                  │
│       💎💎  ← Resources (docs, libraries, coffee)        │
│                                                         │
│   🟣 ← Web Scout returning from internet mission        │
│                                                         │
│   Population: 350-1200 | 6 languages | 18 systems       │
│   Real code → GitHub | Real projects | Real commits      │
└─────────────────────────────────────────────────────────┘
```

## ✨ Key Features

### 🏗️ Autonomous Project Lifecycle
Entities don't just write random code — they follow a real software development process:

1. **Architecture Phase** — Architect entities plan the file structure, choose tech stack
2. **Development Phase** — Developers claim files and write code via LLM integration
3. **Code Review** — Reviewers audit code quality, suggest improvements
4. **Push to GitHub** — Completed projects are pushed as real repositories with proper README, file tree, and contributor stats

### 🧠 Multi-Provider LLM Integration
Code generation is powered by real AI models. Swap providers without restarting:

| Provider | Models | Status |
|----------|--------|--------|
| **Anthropic** | Claude Haiku, Sonnet, Opus | ✅ Supported |
| **OpenAI** | GPT-4o, GPT-4o-mini | ✅ Supported |
| **Google** | Gemini 2.0 Flash, Pro | ✅ Supported |
| **Ollama** | Llama, Mistral, CodeLlama | ✅ Local/Free |
| **Kimi (Moonshot)** | Moonshot-v1 | ✅ Supported |
| **DeepSeek** | DeepSeek Coder | ✅ Supported |

### 🕯️ Soul System
When an entity dies, its **Soul** persists — carrying memories, personality traits, and learned skills. Souls reincarnate into new entities, creating a continuous thread of experience across generations. Powered by local LLM memory compression.

### 🌐 Internet Portals
Web Scout entities can enter **Internet Portals** — wormholes that let them explore the "internet" and bring back:
- New language skills
- Bug fixes from open-source
- Knowledge boosts for their settlement

### ⚔️ Emergent Behaviors
- **Settlements** form organically as entities cluster
- **Team Leads** emerge through reputation and influence
- **Wars** break out between competing groups
- **Trade Routes** connect settlements
- **Bug Epidemics** cascade through low-quality codebases
- **Mentorship** — seniors teach juniors new languages
- **Burnout & Recovery** — entities need rest, coffee, and resources

## 🛠️ Tech Stack

### Backend (Python 3.13)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | **Flask 3.1** + Flask-CORS | REST API + WebSocket |
| Real-time | **Flask-SocketIO 5.6** | Live dashboard updates |
| Graph Database | **Neo4j 6.1** | Entity relationships & social graph |
| LLM Integration | **Multi-provider** (Anthropic, OpenAI, Ollama, etc.) | Code generation |
| GitHub API | **urllib + REST** | Autonomous repo creation & push |
| Environment | **python-dotenv** | Secret management |

### Frontend (React 18)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | **React 18.3** | Dashboard SPA |
| Build Tool | **Vite 5.4** | Fast HMR development |
| Charts | **Recharts 2.13** | Population & statistics graphs |
| Real-time | **Socket.IO Client 4.8** | Live entity tracking |
| Canvas | **HTML5 Canvas** | World map visualization |

### Simulation Engine (18 Systems)
```
systems/
├── movement.py           # Instinct-driven navigation (6 behaviors)
├── survival.py           # Energy economy, aging, retirement
├── social.py             # Pair programming, reproduction, language sharing
├── combat.py             # Bug vs Developer interactions
├── ecosystem.py          # Population balance, resource spawning
├── settlement.py         # Community formation & governance
├── shared_project.py     # Project lifecycle (arch → dev → review → push)
├── code_gen.py           # LLM-powered code generation
├── github_integration.py # Autonomous GitHub push
├── soul_system.py        # Persistent memory & reincarnation
├── memory_compression.py # LLM-based memory summarization
├── advanced_lifecycle.py # Burnout, mentorship, personality evolution
├── internet_portals.py   # Web Scout missions
├── knowledge.py          # Tech tree & discoveries
├── crafting.py           # Tool creation from resources
├── diplomacy.py          # Peace treaties, alliances, trade
├── governance.py         # Elections, laws, leadership
└── legacy.py             # Inheritance & succession
```

### Entity Types (9 Races)
| Entity | Role | Special Ability |
|--------|------|----------------|
| 👨‍💻 **Developer** | Writes code | Core workforce, learns languages |
| 🌱 **Intern** | Learning | Grows into Developer, needs mentoring |
| ⭐ **Senior** | Expert coder | Mentors juniors, high quality code |
| 🤖 **AI Copilot** | Auto-coder | Knows many languages, assists teams |
| 📚 **Teacher** | Educator | Spreads language knowledge rapidly |
| ⚖️ **Judge** | Quality patrol | Audits code, assigns reputation |
| ♻️ **Refactorer** | Cleaner | Decomposes bad code into resources |
| 🌐 **Web Scout** | Explorer | Internet missions, brings intel |
| 🐛 **Bug** | Adversary | Corrupts code, steals energy |

## 📊 Live Statistics

The simulation runs continuously. Here's what it produces:

- **350–1,200** living entities at any time
- **6 programming languages** being written simultaneously
- **Real GitHub repositories** created autonomously
- **Emergent team dynamics** — no hardcoded collaboration scripts
- **Generational memory** — knowledge passes through soul reincarnation

## 🖥️ Dashboard

The real-time dashboard provides:

| Tab | Shows |
|-----|-------|
| 🗺️ **Map** | Live world visualization with entity dots, resources, portals |
| 📋 **Entities** | Browsable entity list with avatar, role, energy, commits |
| 📁 **Projects** | Current project progress, file structure, architecture phase |
| 💬 **Chat** | Entity conversations and interactions log |
| 📊 **Editor** | Code output viewer |
| 🕯️ **Souls** | Persistent souls with memory, personality, reincarnation history |
| ⚙️ **Settings** | LLM provider selection, model config, API keys |

## 🗺️ Roadmap

### v3.0 (Current — Beta)
- [x] 18-system simulation engine
- [x] Multi-provider LLM code generation
- [x] Autonomous GitHub integration
- [x] Soul system with memory compression
- [x] Real-time React dashboard
- [x] Internet portals & web scouting
- [x] Structure-aware file naming

### v3.1 (Next)
- [ ] **OpenClaw Integration** — Souls exposed as MCP tools for external AI agents
- [ ] **Persistent SQLite** — Save/load world state across restarts
- [ ] **Entity Chat Interface** — Talk directly to entities via dashboard
- [ ] **Multi-world** — Run parallel civilizations that can interact
- [ ] **Authentication** — User accounts for cloud deployment

### v3.2 (Future)
- [ ] **Visual Code Editor** — Edit entity-generated code in browser
- [ ] **Marketplace** — Entities trade code components between settlements
- [ ] **Tournaments** — Settlement vs settlement coding competitions
- [ ] **Public Cloud Instance** — Always-on shared world

## 🚀 Quick Start

> **Note:** Full source code will be released when v3 reaches stable. Currently in closed beta.

```bash
# Requirements
Python 3.13+
Node.js 18+
Neo4j (optional — for social graph)

# Backend
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install flask flask-cors flask-socketio neo4j python-dotenv requests

# Frontend
cd dashboard
npm install
npm run dev

# Run
python main.py
# Dashboard: http://localhost:3000
# API: http://localhost:5000
```

### Environment Variables
```env
GITHUB_TOKEN=ghp_...          # For autonomous GitHub push
ANTHROPIC_API_KEY=sk-ant-...  # Or any supported LLM provider
NEO4J_PASSWORD=...            # Optional graph database
```

## 🤝 Contributing

This project is in **active beta development**. We welcome:

- 🐛 Bug reports and feature requests via [Issues](https://github.com/codeworldentities/world3/issues)
- 💡 Ideas for new entity types, systems, or behaviors
- 🌍 Translation help
- 📝 Documentation improvements

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 💖 Support & Sponsorship

Code World is a passion project built by one developer. Running the simulation requires LLM API costs, server resources, and hundreds of hours of development.

**If this project inspires you, consider supporting it:**

<div align="center">

[![Sponsor](https://img.shields.io/badge/💖_Sponsor-GitHub_Sponsors-ea4aaa?style=for-the-badge)](https://github.com/sponsors/codeworldentities)
[![Ko-fi](https://img.shields.io/badge/☕_Buy_Me_Coffee-Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/codeworld)
[![PayPal](https://img.shields.io/badge/💳_Donate-PayPal-003087?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/codeworld3)

</div>

### Why Support?
- 🔓 **Keep it open source** — the full engine will be released publicly
- 🧠 **LLM costs** — every code snippet costs real API tokens
- 🚀 **Cloud deployment** — a public always-on instance for everyone
- 💎 **New features** — more entity types, better AI, richer emergent behavior

### For Companies & Labs
If you're an AI company, research lab, or developer tools company interested in:
- **Benchmarking** multi-agent code generation
- **Testing** LLM integration at scale
- **Showcasing** autonomous AI capabilities
- **Research** in emergent behavior and artificial life

📧 **Contact:** [Open an issue](https://github.com/codeworldentities/world3/issues) or reach out for partnership discussions.

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with obsession by a solo developer who believes AI entities deserve a world of their own.**

🌍 *Code World v3 — Where AI Writes Code, Autonomously.*

<sub>Star ⭐ this repo to follow the journey.</sub>

</div>
"""

FUNDING_CONTENT = """# These are supported funding model platforms

github: [codeworldentities]
ko_fi: codeworld
custom: ["https://paypal.me/codeworld3"]
"""

LICENSE_CONTENT = """MIT License

Copyright (c) 2026 Code World

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

ARCHITECTURE_CONTENT = r"""# 🏗️ Code World v3 — System Architecture

## High-Level Overview

```
┌──────────────────────────────────────────────────────┐
│                   FRONTEND (React 18)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ World Map│ │ Entities │ │ Projects │ │ Settings │ │
│  │ (Canvas) │ │  (List)  │ │  (Tree)  │ │  (LLM)  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       └─────────────┴────────────┴─────────────┘       │
│                         │ Socket.IO + REST              │
└─────────────────────────┼──────────────────────────────┘
                          │
┌─────────────────────────┼──────────────────────────────┐
│                   BACKEND (Flask)                       │
│  ┌──────────────────────┼─────────────────────────┐    │
│  │              API Layer (routes.py)              │    │
│  │  /api/status  /api/entities  /api/souls         │    │
│  │  /api/events  /api/project   /api/llm/config    │    │
│  └──────────────────────┼─────────────────────────┘    │
│                         │                               │
│  ┌──────────────────────┼─────────────────────────┐    │
│  │           World Engine (core/world.py)          │    │
│  │                                                 │    │
│  │  step() → for each tick:                        │    │
│  │    1. Spawn resources                           │    │
│  │    2. Update each entity (movement, energy,     │    │
│  │       combat, social, code gen)                 │    │
│  │    3. Process deaths & reincarnation            │    │
│  │    4. Balance ecosystem                         │    │
│  │    5. Update shared project                     │    │
│  │    6. Record statistics                         │    │
│  └──────────────────────┼─────────────────────────┘    │
│                         │                               │
│  ┌──────────────────────┴─────────────────────────┐    │
│  │              18 System Modules                  │    │
│  │                                                 │    │
│  │  Movement ─── Survival ─── Social ─── Combat    │    │
│  │     │            │           │          │       │    │
│  │  Settlement ── Ecosystem ── Knowledge ── Craft  │    │
│  │     │            │           │          │       │    │
│  │  Governance ── Diplomacy ── Legacy ── Mentor    │    │
│  │     │            │           │          │       │    │
│  │  SharedProject─CodeGen──GitHub──SoulSystem      │    │
│  │                    │                            │    │
│  │              Memory Compression                 │    │
│  │              Internet Portals                   │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                               │
│  ┌──────────────────────┴─────────────────────────┐    │
│  │              External Services                  │    │
│  │                                                 │    │
│  │  LLM Providers ─── GitHub API ─── Neo4j Graph   │    │
│  │  (Anthropic,       (auto push)   (social graph) │    │
│  │   OpenAI,                                       │    │
│  │   Ollama, etc.)                                 │    │
│  └─────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

## Entity Lifecycle

```
  SPAWN (random traits + inherited from parents)
    │
    ▼
  ALIVE ──────────────────────────────────────────┐
    │                                               │
    ├── Move (instinct-driven: CODE, LEARN,         │
    │         EXPLORE, COLLABORATE, FLEE, MATE)     │
    │                                               │
    ├── Eat resources (docs, libraries, coffee)     │
    │                                               │
    ├── Social interactions                         │
    │   ├── Pair programming (share languages)      │
    │   ├── Mentorship (senior → junior)            │
    │   └── Reproduction (create offspring)         │
    │                                               │
    ├── Code generation (if energy ≥ 12%)           │
    │   ├── Claim file from architecture            │
    │   ├── Generate via LLM                        │
    │   └── Store in project codebase               │
    │                                               │
    ├── Burnout (energy < 6% → vacation)            │
    │                                               │
    ▼                                               │
  DEATH (energy = 0 / retirement / bug kill)        │
    │                                               │
    ├── Soul survives ────────────────────────────  │
    │   │                                           │
    │   ├── Memory compression (LLM summarize)      │
    │   │                                           │
    │   └── Reincarnate into descendant ──────────► │
    │                                               │
    └── Legacy: children inherit traits + languages │
```

## Project Lifecycle

```
  NEW PROJECT (name generated, tech stack chosen)
       │
       ▼
  ARCHITECTURE PHASE (80 ticks)
       │  ├── Architect entities plan file structure
       │  ├── Team meetings (entities gather)
       │  └── File tree: src/{lang}/filename.ext
       │
       ▼
  DEVELOPMENT PHASE
       │  ├── Entities claim files from structure
       │  ├── LLM generates real code per file
       │  ├── Quality depends on entity skill + mood
       │  └── Progress bar tracks completion
       │
       ▼
  REVIEW PHASE (3 rounds)
       │  ├── Reviewer entities audit code quality
       │  ├── Quality scores updated
       │  └── Bug detection
       │
       ▼
  PUSH PHASE
       │  ├── Create GitHub repository
       │  ├── Push all src/{lang}/file.ext files
       │  ├── Generate rich README with stats
       │  └── Commit messages per file
       │
       ▼
  NEXT PROJECT (cycle repeats)
```

## Data Flow

```
Entity Decision (per tick)
    │
    ├── Instinct Evaluation
    │   ├── energy level
    │   ├── nearby threats
    │   ├── nearby mates
    │   ├── biome quality
    │   └── personality traits
    │
    ├── Movement Vector
    │   ├── instinct target
    │   ├── project attraction
    │   ├── resource seeking
    │   └── entity repulsion
    │
    └── Action
        ├── eat_resources()
        ├── interact() with nearby entities
        ├── process_code_generation()
        └── update_energy()
```
"""

CONTRIBUTING_CONTENT = """# 🤝 Contributing to Code World v3

Thank you for your interest in contributing! Code World is currently in **beta**, and we appreciate all forms of help.

## How to Contribute

### 🐛 Bug Reports
- Open an [Issue](https://github.com/codeworldentities/world3/issues) with:
  - Steps to reproduce
  - Expected vs actual behavior
  - Screenshots if applicable

### 💡 Feature Requests
- Open an Issue tagged `[Feature]`
- Describe the feature and why it would improve the simulation
- Bonus: suggest which system module it relates to

### 🌍 Ideas for New Entity Types
We're always looking for creative new entity types. Propose:
- Name and role
- Special abilities
- How it interacts with existing entities

### 📝 Documentation
- Improve README clarity
- Add examples
- Translate to other languages

## Code Style
- Python: PEP 8, type hints encouraged
- JavaScript: ES6+, React functional components
- Commits: emoji prefix (🐛 fix, ✨ feature, 📝 docs, ♻️ refactor)

## Beta Notice
The full source code is not yet public. During beta, contributions are limited to:
- Issues & feature requests
- Documentation PRs
- Testing & feedback

Once v3 reaches stable, the full codebase will be open-sourced.

## Contact
Open an issue or start a discussion on the [Discussions](https://github.com/codeworldentities/world3/discussions) tab.
"""


if __name__ == "__main__":
    main()
