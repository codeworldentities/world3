# Selective Persistent Souls in a Multi-Agent Code Simulation

**Draft — work in progress.**

## Abstract

We describe *world3*, a tick-based multi-agent simulation whose agents
cooperate on software-engineering tasks using a local LLM for reasoning.
On top of the base simulation we add a **Soul** layer: a scarce,
persistent persona with long-term memory granted only to a small number
of entities. We argue that *selective* persistence — as opposed to the
common "every agent has unlimited memory" approach — produces emergent
cultural continuity at a fraction of the token cost, and preserves
tractability of save/load and replay.

## 1. Motivation

Existing generative-agent systems (Park et al. 2023, "Smallville";
Project Sid 2024; AI Town) give each agent a persistent memory stream.
This is expensive at scale and obscures the phenomena that actually
matter for emergent culture: a handful of named characters whose
continuity provides *narrative anchors* for the rest of the population.

We hypothesise that:

> **H1.** A simulation with O(n) entities and O(√n) souls produces
> qualitatively similar emergent narratives at dramatically lower
> compute/token cost.
>
> **H2.** A *reincarnation* mechanism (soul migrates to a descendant on
> death) makes long-horizon continuity possible without immortality.

## 2. Architecture

### 2.1 Entities vs Souls

Every agent is an `Entity` (body, traits, energy, position). Entities
that satisfy an eligibility predicate (team leader, architect, elder
past 5000 ticks, or AI copilot) may be granted a `Soul`:

```
Soul {
  id:          stable UUID, survives body death
  entity_id:   current body, -1 if dormant
  name, role, born_tick
  personality_summary: one-paragraph persona, LLM-generated at grant
  traits:     snapshot at grant time (stable identity anchor)
  memory:     list[SoulMemory]  (compressed every 500 ticks)
  reflection: first-person self-summary, LLM-regenerated periodically
  rebirth_count, previous_entity_ids, parent_soul_id
}
```

### 2.2 Grant policy

Grants are bounded by a global cap `MAX_SOULS` (default 30) and a
per-sweep budget (3). Eligibility is re-checked every 100 ticks.

### 2.3 Reincarnation

When a souled entity dies, the system searches for a heir in O(n):
descendants, same-settlement agents, and same-type agents score higher.
If an heir is found the soul migrates with a new memory entry
`"Reborn in body #x (rebirth #k)"` at weight 1.0. Otherwise the soul
goes dormant and is archived on disk.

### 2.4 Memory compression

When a soul's memory list exceeds 60 entries, we keep the 30 most
recent, pick the top 5 by weight from the remainder, and merge them
into a single `reflection`-kind entry of weight 0.95. This bounds both
memory footprint and prompt length.

### 2.5 Prompt injection

When a souled entity thinks, the LLM prompt is augmented with:

- persona summary (~300 chars)
- reflection (~240 chars)
- top-3 important memories
- most-recent 4 memories
- rebirth count

This is bounded O(1) tokens per thought regardless of memory size.

## 3. Implementation

- Language: Python 3.10+, Flask + Socket.IO, React/Vite
- LLM: Ollama (`llama3.2:3b`) for zero-cost inference; optional Kimi
- Persistence: JSON world save + per-soul JSON + Markdown card +
  append-only JSONL audit log
- External bridge: "OpenClaw skill" — CLI wrappers around
  `/api/soul/<id>/{memory,speak,bind}` endpoints

## 4. Evaluation (planned)

Metrics to compare **souled** vs **soul-less** baselines over 10k ticks:

| Metric | Expected direction |
|---|---|
| Unique recurring proper nouns in events | ↑ with souls |
| Compression ratio (memory/ticks) | ↓ with souls (bounded) |
| LLM tokens per tick | similar |
| Narrative coherence (human rating) | ↑ with souls |
| Code quality in settlements led by souled leaders | ↑ |

## 5. Limitations

- Persona generation is cold-started from trait vectors; early souls
  read as archetypes until enough memories accrue.
- The eligibility predicate is hand-crafted; a learned policy would be
  more general.
- No causal experiments yet; hypotheses H1/H2 are still conjectures.

## 6. Related work

- Park et al., "Generative Agents: Interactive Simulacra of Human
  Behavior" (UIST 2023)
- Project Sid (Altera, 2024)
- Hong et al., "MetaGPT: Meta Programming for Multi-Agent Framework"
- Tierra (Ray 1991), Avida (Lenski et al. 2003) — ALife antecedents

## 7. Reproducibility

Code: this repository. `pytest -q` runs unit tests. `docker compose up`
starts the full stack including an Ollama container. All RNG seeds are
derivable from `World.tick` and wall-clock time at init; a fixed-seed
mode is TBD.
