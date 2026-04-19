"""Push redesigned README to GitHub."""
import json, os, base64, urllib.request
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = "codeworldentities"
REPO = "world3"

def api(method, path, data=None):
    url = f"https://api.github.com{path}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json", "User-Agent": "CW"}
    body = json.dumps(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def get_sha(path):
    try:
        r = api("GET", f"/repos/{USER}/{REPO}/contents/{path}")
        return r["sha"]
    except:
        return None

def push(path, content, msg):
    sha = get_sha(path)
    data = {
        "message": msg,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main",
    }
    if sha:
        data["sha"] = sha
    api("PUT", f"/repos/{USER}/{REPO}/contents/{path}", data)


README = r'''<div align="center">

<img src="assets/WORLD3.png" alt="Code World v3" width="180" />

<br/>

# CODE WORLD v3

**An Autonomous AI Civilization Simulator**

<p align="center">
<em>Hundreds of AI entities live, form settlements, collaborate on software projects,<br/>and push real code to GitHub — all autonomously.</em>
</p>

<br/>

<p align="center">
<a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>&nbsp;
<a href="https://flask.palletsprojects.com"><img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/></a>&nbsp;
<a href="https://react.dev"><img src="https://img.shields.io/badge/React-18.3-61dafb?style=for-the-badge&logo=react&logoColor=black" alt="React"/></a>&nbsp;
<a href="https://socket.io"><img src="https://img.shields.io/badge/Socket.IO-Realtime-010101?style=for-the-badge&logo=socket.io&logoColor=white" alt="SocketIO"/></a>
</p>

<p align="center">
<img src="https://img.shields.io/badge/Status-Beta-00d4ff?style=flat-square" alt="Beta"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT"/>
<img src="https://img.shields.io/badge/Entities-350_to_1200-blueviolet?style=flat-square" alt="Entities"/>
<img src="https://img.shields.io/badge/Systems-18-orange?style=flat-square" alt="Systems"/>
<img src="https://img.shields.io/badge/Languages-6-red?style=flat-square" alt="Languages"/>
</p>

<br/>

<p align="center">
<a href="https://diveloper.digital/"><strong>🌐 Live Dashboard</strong></a>&nbsp;&nbsp;•&nbsp;&nbsp;
<a href="https://github.com/codeworldentities?tab=repositories"><strong>📂 Generated Projects</strong></a>&nbsp;&nbsp;•&nbsp;&nbsp;
<a href="#-support--donations"><strong>💖 Support</strong></a>&nbsp;&nbsp;•&nbsp;&nbsp;
<a href="#-roadmap"><strong>🗺️ Roadmap</strong></a>
</p>

</div>

<br/>

---

<br/>

## 🧬 What is Code World?

> **Code World is not a game. It's a living ecosystem.**
>
> AI entities are born with unique personalities, learn programming languages from mentors, form teams around shared projects, and produce real software — complete with architecture docs, code review, and GitHub commits. When they die, their **soul** carries forward into the next generation.

<br/>

<table>
<tr>
<td width="50%">

### Every Entity Has

🧠 &nbsp; **Personality** — curiosity, sociability, resilience, aggression  
💼 &nbsp; **Role** — Architect, Lead, Reviewer, Tester, Freelancer, DevOps  
🗣️ &nbsp; **Languages** — Python, JavaScript, Rust, Go, HTML/CSS, SQL  
🕯️ &nbsp; **Soul** — persistent memory that survives death  
📈 &nbsp; **XP & Leveling** — grow through commits and collaboration  
🧬 &nbsp; **Genetics** — traits are inherited across generations  

</td>
<td width="50%">

### The World Runs On

⚡ &nbsp; **Energy economy** — eat, rest, or burn out  
🏘️ &nbsp; **Settlements** — communities form organically  
⚔️ &nbsp; **Conflict** — bugs attack, wars erupt between groups  
🤝 &nbsp; **Diplomacy** — alliances, trade routes, peace treaties  
🌐 &nbsp; **Internet portals** — scouts bring back real-world knowledge  
📜 &nbsp; **Governance** — elections, laws, leadership succession  

</td>
</tr>
</table>

<br/>

---

<br/>

## ✨ Core Features

<table>
<tr>
<td align="center" width="25%">
<br/>
<img width="60" src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg"/>
<br/><br/>
<strong>Auto GitHub Push</strong>
<br/>
<sub>Completed projects become real<br/>repositories with README,<br/>file tree & contributor stats</sub>
<br/><br/>
</td>
<td align="center" width="25%">
<br/>
<img width="60" src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tensorflow/tensorflow-original.svg"/>
<br/><br/>
<strong>Multi-LLM Engine</strong>
<br/>
<sub>Anthropic, OpenAI, Google,<br/>Ollama, DeepSeek, Kimi —<br/>hot-swap without restart</sub>
<br/><br/>
</td>
<td align="center" width="25%">
<br/>
🕯️
<br/><br/>
<strong>Soul Reincarnation</strong>
<br/>
<sub>Souls persist after death,<br/>carrying memories & skills<br/>into new generations</sub>
<br/><br/>
</td>
<td align="center" width="25%">
<br/>
🌐
<br/><br/>
<strong>Internet Portals</strong>
<br/>
<sub>Web Scouts explore the internet<br/>and bring back knowledge,<br/>skills & bug fixes</sub>
<br/><br/>
</td>
</tr>
</table>

<br/>

### 🏗️ Autonomous Project Lifecycle

```
  📐 ARCHITECTURE          💻 DEVELOPMENT          🔍 REVIEW            🚀 PUSH
  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐     ┌──────────────┐
  │ Architects   │──────▶ │ Developers   │──────▶ │ Reviewers    │───▶ │ GitHub API   │
  │ plan files & │        │ claim files  │        │ audit code   │     │ creates repo │
  │ tech stack   │        │ & write code │        │ quality      │     │ & pushes     │
  └──────────────┘        └──────────────┘        └──────────────┘     └──────────────┘
```

<br/>

### 🧠 Supported LLM Providers

| Provider | Models | Type |
|:---------|:-------|:-----|
| **Anthropic** | Claude Haiku · Sonnet · Opus | ☁️ Cloud |
| **OpenAI** | GPT-4o · GPT-4o-mini | ☁️ Cloud |
| **Google** | Gemini 2.0 Flash · Pro | ☁️ Cloud |
| **DeepSeek** | DeepSeek Coder | ☁️ Cloud |
| **Kimi** | Moonshot-v1 | ☁️ Cloud |
| **Ollama** | Llama · Mistral · CodeLlama | 🖥️ Local / Free |

<br/>

---

<br/>

## 🛠️ Architecture

<details open>
<summary><strong>📦 Backend — Python 3.13</strong></summary>
<br/>

| Layer | Technology | Role |
|:------|:-----------|:-----|
| API | Flask 3.1 + Flask-CORS | REST endpoints + WebSocket |
| Real-time | Flask-SocketIO 5.6 | Live dashboard streaming |
| Graph DB | Neo4j 6.1 | Social relationships & entity graph |
| LLM | Multi-provider abstraction | Code generation engine |
| VCS | GitHub REST API | Autonomous repo creation & push |
| Config | python-dotenv | Environment & secrets |

</details>

<details open>
<summary><strong>🎨 Frontend — React 18</strong></summary>
<br/>

| Layer | Technology | Role |
|:------|:-----------|:-----|
| Framework | React 18.3 | Single-page dashboard |
| Bundler | Vite 5.4 | Fast HMR development |
| Charts | Recharts 2.13 | Population & statistics |
| Streaming | Socket.IO Client 4.8 | Live entity updates |
| Rendering | HTML5 Canvas | World map visualization |

</details>

<details open>
<summary><strong>⚙️ Simulation — 18 System Modules</strong></summary>
<br/>

```
systems/
│
├── 🚶 movement.py            Instinct-driven navigation (6 behaviors)
├── ❤️ survival.py             Energy, aging, death & retirement
├── 👥 social.py               Pair programming, reproduction, language sharing
├── ⚔️ combat.py               Bug vs Developer interactions
├── 🌿 ecosystem.py            Population balance, resource spawning
├── 🏘️ settlement.py           Community formation & governance
│
├── 📐 shared_project.py       Project lifecycle (arch → dev → review → push)
├── 💻 code_gen.py              LLM-powered code generation
├── 🚀 github_integration.py   Autonomous GitHub repository push
│
├── 🕯️ soul_system.py          Persistent memory & reincarnation
├── 🧠 memory_compression.py   LLM-based memory summarization
├── 🔄 advanced_lifecycle.py   Burnout, mentorship, personality evolution
│
├── 🌐 internet_portals.py     Web Scout missions & knowledge retrieval
├── 📚 knowledge.py            Tech tree & discoveries
├── 🔨 crafting.py             Tool creation from raw resources
├── 🕊️ diplomacy.py            Peace treaties, alliances, trade routes
├── 🏛️ governance.py           Elections, laws, leadership
└── 📜 legacy.py               Inheritance & succession
```

</details>

<br/>

---

<br/>

## 🎭 Entity Types

<table>
<tr>
<td align="center" width="11%">
👨‍💻<br/><strong>Developer</strong><br/><sub>Core coder</sub>
</td>
<td align="center" width="11%">
🌱<br/><strong>Intern</strong><br/><sub>Learner</sub>
</td>
<td align="center" width="11%">
⭐<br/><strong>Senior</strong><br/><sub>Expert</sub>
</td>
<td align="center" width="11%">
🤖<br/><strong>AI Copilot</strong><br/><sub>Polyglot</sub>
</td>
<td align="center" width="11%">
📚<br/><strong>Teacher</strong><br/><sub>Educator</sub>
</td>
<td align="center" width="11%">
⚖️<br/><strong>Judge</strong><br/><sub>Auditor</sub>
</td>
<td align="center" width="11%">
♻️<br/><strong>Refactorer</strong><br/><sub>Cleaner</sub>
</td>
<td align="center" width="11%">
🌐<br/><strong>Web Scout</strong><br/><sub>Explorer</sub>
</td>
<td align="center" width="11%">
🐛<br/><strong>Bug</strong><br/><sub>Adversary</sub>
</td>
</tr>
</table>

<br/>

---

<br/>

## 🖥️ Dashboard

> Real-time visualization powered by React + Socket.IO + HTML5 Canvas

| Tab | Description |
|:----|:------------|
| 🗺️ **World Map** | Live canvas with entity positions, resources, portals, settlements |
| 📋 **Entities** | Searchable list — avatar, role, energy, commits, languages |
| 📁 **Projects** | Active project progress, file tree, architecture blueprint |
| 💬 **Chat** | Entity conversations & interaction log |
| 📊 **Editor** | Generated code viewer |
| 🕯️ **Souls** | Soul browser — memory, personality, reincarnation count |
| ⚙️ **Settings** | LLM provider picker, model config, API key management |

<br/>

---

<br/>

## 🗺️ Roadmap

### ✅ v3.0 — Beta *(current)*

- [x] 18-system simulation engine
- [x] Multi-provider LLM code generation
- [x] Autonomous GitHub integration
- [x] Soul system with memory compression
- [x] Real-time React dashboard with 7 tabs
- [x] Internet portals & web scouting
- [x] Structure-aware file naming

### 🔜 v3.1

- [ ] **MCP Integration** — Souls exposed as tools for external AI agents
- [ ] **Persistent Storage** — Save/load world state across restarts
- [ ] **Entity Chat** — Talk directly to entities in the dashboard
- [ ] **Multi-world** — Parallel civilizations that can interact
- [ ] **Auth System** — User accounts for cloud deployment

### 🔮 v3.2

- [ ] **Visual Code Editor** — Edit entity code in-browser
- [ ] **Marketplace** — Trade code components between settlements
- [ ] **Tournaments** — Settlement vs settlement coding battles
- [ ] **Public Cloud** — Always-on shared world instance

<br/>

---

<br/>

## 🚀 Quick Start

> [!NOTE]
> Full source code will be released when v3 reaches stable. Currently in **closed beta**.

```bash
# Requirements: Python 3.13+, Node.js 18+, Neo4j (optional)

# Backend
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install flask flask-cors flask-socketio neo4j python-dotenv requests

# Frontend
cd dashboard && npm install && npm run dev

# Launch
python main.py
# Dashboard → http://localhost:3000
# API       → http://localhost:5000
```

<details>
<summary><strong>Environment Variables</strong></summary>
<br/>

```env
GITHUB_TOKEN=ghp_...          # Autonomous GitHub push
ANTHROPIC_API_KEY=sk-ant-...  # Or any supported LLM provider
NEO4J_PASSWORD=...            # Optional graph database
```

</details>

<br/>

---

<br/>

## 💖 Support & Donations

<div align="center">

<br/>

Code World is built and maintained by **one developer**.  
Running the simulation requires LLM API costs, server time, and hundreds of hours of work.

<br/>

<a href="https://github.com/sponsors/codeworldentities">
<img src="https://img.shields.io/badge/💖_Sponsor_on_GitHub-ea4aaa?style=for-the-badge" alt="GitHub Sponsors"/>
</a>
&nbsp;&nbsp;
<a href="https://ko-fi.com/codeworldentities">
<img src="https://img.shields.io/badge/☕_Buy_Me_a_Coffee-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white" alt="Ko-fi"/>
</a>

<br/><br/>

| Why Support? | |
|:------------|:--|
| 🔓 **Open Source** | The full engine will be released publicly |
| 🧠 **LLM Costs** | Every code snippet costs real API tokens |
| 🚀 **Cloud Deploy** | A public always-on instance for everyone |
| 💎 **New Features** | More entity types, better AI, richer behaviors |

</div>

<br/>

### 🏢 For Companies & Research Labs

> If you're building **multi-agent systems**, **LLM benchmarks**, or **autonomous AI tools** — Code World is a live testbed for emergent multi-agent code generation at scale.
>
> **Interested in partnership, sponsorship, or research collaboration?**  
> 📧 [Open an issue](https://github.com/codeworldentities/world3/issues) or start a [Discussion](https://github.com/codeworldentities/world3/discussions).

<br/>

---

<br/>

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

<br/>

---

<div align="center">
<br/>

<img src="assets/WORLD3.png" alt="Code World" width="80" />

<br/>

**Code World v3** — *Where AI Writes Code, Autonomously.*

<sub>Built with obsession. Star ⭐ to follow the journey.</sub>

<br/><br/>

</div>
'''

push("README.md", README, "✨ Redesign README with polished layout")
print("README.md redesigned and pushed!")

print("https://github.com/codeworldentities/world3")


if __name__ == "__main__":
    pass
