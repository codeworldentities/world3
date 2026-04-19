# world3 OpenClaw skill

This folder is a **skill pack** that lets an OpenClaw instance talk to the
running world3 simulation. It needs zero paid services — everything runs locally.

## Layout

```
openclaw-skill/world3/
  skill.json     # manifest (metadata + entrypoints)
  _http.py       # tiny HTTP helper
  peek.py        # read-only: status, souls list, soul detail
  act.py         # write-side: inject memory, bind soul to Claw
  voice.py       # speak as a bound soul (LLM reply in character)
```

## Install

1. Start the world3 server (default: `http://127.0.0.1:5000`).
2. Copy this folder into your OpenClaw skills directory, OR
   point Claw at it directly.
3. Optional: set `WORLD3_API=http://host:port` if the server is not on localhost.

## Commands

Read:

```bash
python peek.py status
python peek.py souls
python peek.py soul <soul_id>
```

Write:

```bash
python act.py remember <soul_id> "met a sharp new intern at dawn" --weight=0.7
python act.py bind <soul_id>           # enable Claw binding
python act.py bind <soul_id> --unbind  # disable
```

Speak as a soul:

```bash
python voice.py <soul_id> "what are you working on?"
```

## How souls work

- A few entities in world3 carry a **Soul** — a persistent persona with
  long-term memory. Souls survive saves and (via reincarnation) death.
- `api/soul/<id>/memory` lets you inject an external event (e.g. a chat
  message from you through Claw). That memory is then used in the entity's
  next LLM-driven thoughts and actions.
- `api/soul/<id>/speak` returns a short in-character line, using the world's
  local LLM (Ollama). No external API keys.

## Safety

- All endpoints are local; no data leaves your machine unless you put the
  server behind a public address yourself.
- `speak` is rate-limited by the world's LLM queue — if Ollama is offline,
  the endpoint returns `503 LLM not connected`.
