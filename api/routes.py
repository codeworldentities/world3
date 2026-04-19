"""API Routes — all endpoints for the code world."""

from __future__ import annotations

import logging
import statistics

from flask import Flask, request, jsonify

import config
from config import LLM_MAX_TOKENS, WORLD_WIDTH, WORLD_HEIGHT
from core.enums import DiplomacyState, EntityType, Role

log = logging.getLogger("api.routes")


def _safe_int_arg(name: str, default: int, lo: int = 0, hi: int = 10_000) -> int:
    """Parse an integer query arg with bounds clamping. Returns default on error."""
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, val))


def _pop_by_type(entities) -> dict:
    counts: dict = {}
    for e in entities:
        tname = e.entity_type.value
        counts[tname] = counts.get(tname, 0) + 1
    return counts


# ================== Helpers ==================

def _entity_to_dict(e) -> dict:
    return {
        "id": e.id,
        "x": round(e.x, 1),
        "y": round(e.y, 1),
        "type": e.entity_type.value,
        "energy": round(e.energy, 3),
        "gender": e.gender.value,
        "age": e.age,
        "alive": e.alive,
        "generation": e.generation,
        "speed": round(e.speed, 3),
        "aggression": round(e.aggression, 2),
        "curiosity": round(e.curiosity, 2),
        "sociability": round(e.sociability, 2),
        "resilience": round(e.resilience, 2),
        "role": e.role.value if e.role else "Freelancer",
        "group_id": e.group_id,
        "settlement_id": e.settlement_id,
        "brain_level": e.brain_level,
        "last_thought": e.last_thought,
        "last_dialogue": e.last_dialogue,
        "llm_mood": e.llm_mood,
        "llm_action": e.llm_action,
        "instinct": e.instincts.active.value if e.instincts and e.instincts.active else "",
        "memories": [
            {"tick": m.tick, "event": m.event, "other_id": m.other_id}
            for m in (e.memories[-10:] if e.memories else [])
        ],
        "relationships": {
            str(k): round(v, 2)
            for k, v in sorted(e.relationships.items(), key=lambda x: -abs(x[1]))[:10]
        } if e.relationships else {},
        "inventory": {k: v for k, v in e.inventory.items() if v > 0} if e.inventory else {},
        "crafted": [ct.value for ct in e.crafted] if e.crafted else [],
        "known_knowledge": [k.value for k in e.known_knowledge] if e.known_knowledge else [],
        # code world new fields
        "languages": [l.value for l in e.languages_known] if e.languages_known else [],
        "commits": e.commits,
        "bugs_fixed": e.bugs_fixed,
        "code_quality": round(e.code_quality, 2),
        "reviews_done": e.reviews_done,
        "reputation": round(getattr(e, "reputation", 0.5), 3),
        "burnout": bool(getattr(e, "burnout", False)),
        "burnout_ticks": int(getattr(e, "burnout_ticks", 0)),
        "web_source": getattr(e, "web_source", ""),
        "web_mission_until": int(getattr(e, "web_mission_until", 0)),
        "web_reports": int(getattr(e, "web_reports", 0)),
        "found_bug_in": e.found_bug_in,
        "reported_to_dev": e.reported_to_dev,
        "pair_partner_id": e.pair_partner_id,
    }


def _settlement_to_dict(s) -> dict:
    from config import CODE_MAX_PER_PROJECT
    codebase_size = len(s.codebase)
    progress = min(100, round(codebase_size / CODE_MAX_PER_PROJECT * 100))
    gh_url = None
    if progress >= 100 and s.project_name:
        gh_url = f"https://github.com/ProjectMakerGeorgia/{s.project_name}"
    return {
        "id": s.id,
        "group_id": s.group_id,
        "x": round(s.x, 1),
        "y": round(s.y, 1),
        "population": s.population,
        "tech_level": s.tech_level,
        "techs": [t.value for t in s.techs],
        "stored_resources": round(s.stored_resources, 1),
        "buildings": s.buildings,
        "leader_id": s.leader_id,
        "diplomacy": {str(k): v.value for k, v in s.diplomacy.items()},
        "project_name": s.project_name,
        "tech_stack": [l.value for l in s.tech_stack] if s.tech_stack else [],
        "total_commits": s.total_commits,
        "bug_count": s.bug_count,
        "codebase_size": codebase_size,
        "progress": progress,
        "github_url": gh_url,
        "phase": getattr(s, 'phase', 'development'),
        "team_meetings": getattr(s, 'team_meetings', 0),
        "radius": getattr(s, 'radius', 50),
    }


GOD_SYSTEM_PROMPT = """You are a Developer in a virtual code world. The system admin is talking to you.
Respond as a Developer — first person, with your programmer personality.
Response should be brief (2-3 sentences), lively and in character.
Always respond in English."""


TUNABLE_PARAMS = {
    "FEATURE_CHANCE": {"type": "float", "min": 0.0, "max": 0.1, "desc": "New feature creation probability"},
    "BURNOUT_ENERGY_THRESHOLD": {"type": "float", "min": 0.01, "max": 0.3, "desc": "Energy level that triggers burnout recovery"},
    "BURNOUT_RECOVERY_TICKS": {"type": "int", "min": 20, "max": 1000, "desc": "Ticks spent in burnout recovery"},
    "REP_JUDGE_REWARD": {"type": "float", "min": 0.0, "max": 0.1, "desc": "Reputation gain from judge reward"},
    "REP_JUDGE_PENALTY": {"type": "float", "min": -0.1, "max": 0.0, "desc": "Reputation loss from judge penalty"},
    "SKILL_DECAY_UNUSED_AFTER": {"type": "int", "min": 50, "max": 5000, "desc": "Ticks before unused skill decay starts"},
    "CASCADE_SPREAD_CHANCE": {"type": "float", "min": 0.0, "max": 0.5, "desc": "Chance for critical bugs to spread"},
    "MIGRATION_CHANCE": {"type": "float", "min": 0.0, "max": 0.05, "desc": "Chance strong developers leave projects"},
    "RESOURCE_SPAWN_RATE": {"type": "float", "min": 0.0, "max": 0.2, "desc": "Resource spawn rate"},
    "RESOURCE_ENERGY": {"type": "float", "min": 0.05, "max": 1.0, "desc": "Resource energy"},
    "BUG_ENERGY_MULT": {"type": "float", "min": 1.0, "max": 2.0, "desc": "Bug energy cost"},
    "MAX_BUG_RATIO": {"type": "float", "min": 0.05, "max": 0.5, "desc": "Max bug ratio"},
    "VISION_RADIUS": {"type": "float", "min": 20.0, "max": 200.0, "desc": "Vision radius"},
    "INTERACTION_RADIUS": {"type": "float", "min": 10.0, "max": 100.0, "desc": "Interaction radius"},
    "DAY_LENGTH": {"type": "int", "min": 100, "max": 5000, "desc": "Sprint duration"},
    "MAX_ENTITIES": {"type": "int", "min": 100, "max": 5000, "desc": "Max entities"},
    "LLM_THINK_INTERVAL": {"type": "int", "min": 50, "max": 1000, "desc": "LLM think interval"},
    "LLM_CONVO_INTERVAL": {"type": "int", "min": 50, "max": 1000, "desc": "Conversation interval"},
    "LLM_CONVO_RADIUS": {"type": "float", "min": 30.0, "max": 300.0, "desc": "Conversation radius"},
    "LLM_TEMPERATURE": {"type": "float", "min": 0.1, "max": 2.0, "desc": "LLM temperature"},
    "CODE_GEN_INTERVAL": {"type": "int", "min": 50, "max": 1000, "desc": "Code generation interval"},
}


# ================== Route Registration ==================

def register_routes(app: Flask):
    from api.server import get_world, get_sim_paused, set_sim_paused, get_sim_speed, set_sim_speed, socketio
    from api.server import get_server_uptime_seconds
    from api.server import STATIC_DIR
    from flask import send_from_directory

    @app.route("/souls")
    def _soul_gallery():
        """Static soul-gallery UI."""
        return send_from_directory(STATIC_DIR, "souls.html")

    @app.route("/api/status")
    def api_status():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        type_counts = {}
        role_counts = {}
        for e in w.entities:
            tname = e.entity_type.value
            type_counts[tname] = type_counts.get(tname, 0) + 1
            rname = e.role.value if e.role else "Freelancer"
            role_counts[rname] = role_counts.get(rname, 0) + 1

        brain_info = None
        if w.brain:
            brain_info = w.brain.get_stats()

        github_info = None
        try:
            from systems.github_integration import get_stats, is_enabled
            if is_enabled():
                github_info = get_stats()
        except Exception as exc:
            log.debug("github stats unavailable: %s", exc)

        # active project info
        active_proj = None
        try:
            from systems.shared_project import get_active_project, get_completed_projects
            ap = get_active_project(w)
            if ap:
                from config import CODE_MAX_PER_PROJECT
                _max = ap.max_files or CODE_MAX_PER_PROJECT
                active_proj = {
                    "id": ap.id,
                    "name": ap.project_name,
                    "progress": min(100, round(len(ap.codebase) / _max * 100)),
                    "files": len(ap.codebase),
                    "max_files": _max,
                    "commits": ap.total_commits,
                    "bugs": ap.bug_count,
                    "population": ap.population,
                    "tech_stack": [l.value if hasattr(l, 'value') else str(l) for l in ap.tech_stack],
                    "phase": getattr(ap, 'phase', 'development'),
                    "team_meetings": getattr(ap, 'team_meetings', 0),
                    "review_rounds": getattr(ap, 'review_rounds', 0),
                    "file_structure": getattr(ap, 'file_structure', []),
                }
        except Exception as exc:
            log.debug("active project unavailable: %s", exc)

        avg_reputation = 0.0
        burnout_active = 0
        if w.entities:
            reps = [getattr(e, "reputation", 0.5) for e in w.entities if e.alive]
            avg_reputation = sum(reps) / len(reps) if reps else 0.0
            burnout_active = sum(1 for e in w.entities if e.alive and getattr(e, "burnout", False))

        return jsonify({
            "tick": w.tick,
            "era": w.era,
            "time_label": w.time_label,
            "is_night": w.is_night,
            "light_level": round(w.light_level, 2),
            "world_width": WORLD_WIDTH,
            "world_height": WORLD_HEIGHT,
            "entities": len(w.entities),
            "resources": len(w.resources),
            "settlements": len(w.settlements),
            "type_counts": type_counts,
            "role_counts": role_counts,
            "total_born": w.total_born,
            "total_died": w.total_died,
            "total_bug_reports": w.total_bug_reports,
            "total_code_generated": w.total_code_generated,
            "wars": len([war for war in w.wars if war.is_active]),
            "trade_routes": len([tr for tr in w.trade_routes if tr.active]),
            "knowledge_discovered": w.total_knowledge_discovered,
            "avg_reputation": round(avg_reputation, 3),
            "burnout_active": burnout_active,
            "team_memory_entries": len(getattr(w, "_team_memory", [])),
            "internet": {
                "portals": len(getattr(w, "web_portals", [])),
                "portal_trips": int(getattr(w, "total_portal_trips", 0)),
                "web_reports": int(getattr(w, "total_web_reports", 0)),
                "open_source_growth": round(float(getattr(w, "open_source_growth", 0.0)), 3),
            },
            "brain": brain_info,
            "github": github_info,
            "active_project": active_proj,
        })

    @app.route("/api/entities")
    def api_entities():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        etype = request.args.get("type")
        role = request.args.get("role")
        has_brain = request.args.get("brain")
        try:
            limit = int(request.args.get("limit", 100))
            offset = int(request.args.get("offset", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "limit/offset must be integers"}), 400
        limit = max(1, min(1000, limit))
        offset = max(0, offset)

        # Validate enum arguments at the boundary — reject unknown values early
        if etype is not None:
            valid_types = {t.value for t in EntityType}
            if etype not in valid_types:
                return jsonify({"error": f"Unknown type: {etype}",
                                "valid": sorted(valid_types)}), 400
        if role is not None:
            valid_roles = {r.value for r in Role}
            if role not in valid_roles:
                return jsonify({"error": f"Unknown role: {role}",
                                "valid": sorted(valid_roles)}), 400

        entities = w.entities
        if etype:
            entities = [e for e in entities if e.entity_type.value == etype]
        if role:
            entities = [e for e in entities if e.role and e.role.value == role]
        if has_brain:
            entities = [e for e in entities if e.brain_level > 0]

        total = len(entities)
        entities = entities[offset:offset + limit]

        return jsonify({
            "total": total,
            "offset": offset,
            "limit": limit,
            "entities": [_entity_to_dict(e) for e in entities],
        })

    @app.route("/api/entity/<int:entity_id>")
    def api_entity(entity_id: int):
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        for e in w.entities:
            if e.id == entity_id:
                data = _entity_to_dict(e)
                data["memories"] = [
                    {"tick": m.tick, "event": m.event, "other_id": m.other_id,
                     "value": round(m.value, 2)}
                    for m in (e.memories[-25:] if e.memories else [])
                ]
                data["relationships"] = {
                    str(k): round(v, 2) for k, v in e.relationships.items()
                } if e.relationships else {}
                data["biome"] = w.get_biome(e.x, e.y).value
                return jsonify(data)

        return jsonify({"error": "Entity not found"}), 404

    @app.route("/api/settlements")
    def api_settlements():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        return jsonify({
            "settlements": [_settlement_to_dict(s) for s in w.settlements.values()],
        })

    @app.route("/api/completed-projects")
    def api_completed_projects():
        """List of completed projects with GitHub links."""
        try:
            from systems.shared_project import get_completed_projects
            return jsonify({"projects": get_completed_projects()})
        except Exception as exc:
            log.debug("completed-projects unavailable: %s", exc)
            return jsonify({"projects": []})

    @app.route("/api/wars")
    def api_wars():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        return jsonify({
            "wars": [
                {
                    "id": war.id,
                    "group_a": war.group_a,
                    "group_b": war.group_b,
                    "duration": war.duration,
                    "casualties_a": war.casualties_a,
                    "casualties_b": war.casualties_b,
                    "active": war.is_active,
                    "winner": war.winner,
                }
                for war in w.wars
            ],
        })

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        entity_id = data.get("entity_id")
        message = str(data.get("message", "")).strip()[:500]
        if not entity_id or not message:
            return jsonify({"error": "entity_id and message required"}), 400

        entity = None
        for e in w.entities:
            if e.id == entity_id:
                entity = e
                break
        if not entity:
            return jsonify({"error": "Entity not found"}), 404

        entity_data = w._build_entity_data(entity)
        context = w._build_llm_context(entity)
        entity_desc = _build_chat_context(entity_data, context)

        try:
            from llm.provider import call_llm
            answer = call_llm(
                GOD_SYSTEM_PROMPT,
                f"Developer state:\n{entity_desc}\n\nAdmin question: {message}",
                json_mode=False,
                temperature=0.7,
                max_tokens=LLM_MAX_TOKENS * 2,
            )
            if not answer:
                return jsonify({"error": "LLM did not return a response"}), 502

            entity.remember(w.tick, f"Admin asked: {message[:50]}", None, 0.8)

            return jsonify({
                "entity_id": entity_id,
                "response": answer,
                "entity_name": f"#{entity.id} ({entity.entity_type.value})",
                "mood": entity.llm_mood or "neutral",
            })

        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ================== LLM Provider Configuration ==================

    @app.route("/api/llm/providers")
    def api_llm_providers():
        try:
            from llm import llm_config
            return jsonify({
                "providers": llm_config.list_providers(),
                "current": llm_config.get_public(),
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/llm/config", methods=["GET", "POST"])
    def api_llm_config():
        from llm import llm_config

        if request.method == "GET":
            try:
                return jsonify({
                    "config": llm_config.get_public(),
                    "providers": llm_config.list_providers(),
                })
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

        data = request.get_json(silent=True) or {}
        changes = {}

        for field in ("provider", "model", "base_url", "temperature", "max_tokens"):
            if field in data:
                changes[field] = data[field]

        # Explicit key update (including empty string if caller wants to clear).
        if "api_key" in data:
            changes["api_key"] = data.get("api_key", "")

        if not changes:
            return jsonify({"error": "No changes provided"}), 400

        try:
            llm_config.update(changes)
            w = get_world()
            if w and getattr(w, "brain", None):
                w.brain.reload_config()
            return jsonify({"ok": True, "config": llm_config.get_public()})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/llm/test", methods=["POST"])
    def api_llm_test():
        try:
            from llm.provider import test_current_provider
            result = test_current_provider()
            code = 200 if result.get("ok") else 502
            return jsonify(result), code
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/conversations")
    def api_conversations():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        limit = _safe_int_arg("limit", 20, lo=1, hi=1000)
        return jsonify({"conversations": w.conversations[-limit:]})

    @app.route("/api/params")
    def api_params():
        params = {}
        for name, meta in TUNABLE_PARAMS.items():
            val = getattr(config, name, None)
            if val is not None:
                params[name] = {"value": val, **meta}
        return jsonify({"params": params})

    @app.route("/api/params", methods=["POST"])
    def api_set_params():
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        changed = {}
        errors = {}

        for name, value in data.items():
            if name not in TUNABLE_PARAMS:
                errors[name] = "unknown parameter"
                continue

            meta = TUNABLE_PARAMS[name]
            try:
                if meta["type"] == "int":
                    value = int(value)
                else:
                    value = float(value)

                if value < meta["min"] or value > meta["max"]:
                    errors[name] = f"out of range [{meta['min']}, {meta['max']}]"
                    continue

                old_val = getattr(config, name)
                setattr(config, name, value)
                changed[name] = {"old": old_val, "new": value}

            except (ValueError, TypeError) as exc:
                errors[name] = str(exc)

        if changed:
            socketio.emit("params_changed", changed)

        return jsonify({"changed": changed, "errors": errors})

    @app.route("/api/smite/<int:entity_id>", methods=["POST"])
    def api_smite(entity_id: int):
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        for e in w.entities:
            if e.id == entity_id:
                e.energy = 0
                e.alive = False
                e.remember(w.tick, "Admin rm -rf", None, -1.0)
                return jsonify({"ok": True, "message": f"Entity #{entity_id} terminated"})
        return jsonify({"error": "Entity not found"}), 404

    @app.route("/api/bless/<int:entity_id>", methods=["POST"])
    def api_bless(entity_id: int):
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        for e in w.entities:
            if e.id == entity_id:
                e.energy = min(1.0, e.energy + 0.3)
                e.remember(w.tick, "Admin boost", None, 1.0)
                return jsonify({"ok": True, "energy": round(e.energy, 3)})
        return jsonify({"error": "Entity not found"}), 404

    @app.route("/api/spawn", methods=["POST"])
    def api_spawn():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        data = request.get_json() or {}
        x = data.get("x")
        y = data.get("y")
        if x is not None and y is not None:
            e = w.spawn_entity(float(x), float(y))
        else:
            e = w.spawn_entity()

        if e:
            return jsonify({"ok": True, "entity": _entity_to_dict(e)})
        return jsonify({"error": "Could not spawn"}), 500

    @app.route("/api/events")
    def api_events():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        limit = _safe_int_arg("limit", 50, lo=1, hi=1000)
        return jsonify({"events": w.events[-limit:]})

    @app.route("/api/portals")
    def api_portals():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        return jsonify({"portals": list(getattr(w, "web_portals", []))})

    @app.route("/api/knowledge")
    def api_knowledge():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        discoveries = []
        for kid, k in w.knowledge_db.items():
            discoveries.append({
                "id": k.id,
                "type": k.knowledge_type.value,
                "name": k.name,
                "description": k.description,
                "discovered_at_tick": k.discovered_at_tick,
                "discovered_by_entity": k.discovered_by_entity,
                "discovered_by_group": k.discovered_by_group,
            })

        group_knowledge = {}
        for gid, k_list in w.group_knowledge.items():
            group_knowledge[str(gid)] = [k.value for k in k_list]

        return jsonify({
            "total_discovered": w.total_knowledge_discovered,
            "discoveries": discoveries,
            "group_knowledge": group_knowledge,
        })

    @app.route("/api/population")
    def api_population():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        return jsonify({
            "total": list(w.pop_total),
            "developer": list(w.pop_developer),
            "bug": list(w.pop_bug),
            "refactorer": list(w.pop_refactorer),
            "copilot": list(w.pop_copilot),
            "senior": list(w.pop_senior),
            "intern": list(w.pop_intern),
            "web_scout": list(getattr(w, "pop_web_scout", [])),
            "energy_avg": list(w.energy_avg),
        })

    @app.route("/api/code")
    def api_code():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        limit = _safe_int_arg("limit", 20, lo=1, hi=500)
        snippets = sorted(w.code_snippets.values(),
                          key=lambda s: s.tick_created, reverse=True)[:limit]
        return jsonify({
            "total": len(w.code_snippets),
            "snippets": [
                {
                    "id": s.id,
                    "author_id": s.author_id,
                    "language": s.language.value,
                    "description": s.description,
                    "quality": round(s.quality, 2),
                    "reviewed": s.reviewed,
                    "has_bugs": s.has_bugs,
                    "lines": s.lines,
                    "filename": s.filename,
                    "tick_created": s.tick_created,
                }
                for s in snippets
            ],
        })

    @app.route("/api/code/<int:snippet_id>")
    def api_code_detail(snippet_id: int):
        """Snippet details — with code content."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        s = w.code_snippets.get(snippet_id)
        if not s:
            return jsonify({"error": "Snippet not found"}), 404
        return jsonify({
            "id": s.id,
            "author_id": s.author_id,
            "language": s.language.value,
            "description": s.description,
            "content": s.content,
            "quality": round(s.quality, 2),
            "reviewed": s.reviewed,
            "has_bugs": s.has_bugs,
            "lines": s.lines,
            "filename": s.filename,
            "tick_created": s.tick_created,
            "reviewer_id": s.reviewer_id,
        })

    @app.route("/api/project/<int:settlement_id>/files")
    def api_project_files(settlement_id: int):
        """Project file tree — for file manager."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        sett = w.settlements.get(settlement_id)
        if not sett:
            return jsonify({"error": "Project not found"}), 404

        _LANG_DIRS = {
            "python": "python", "javascript": "javascript",
            "rust": "rust", "go": "go", "html_css": "web", "sql": "sql",
        }

        tree = {}
        files = []
        for s in sett.codebase:
            lang = s.language.value if hasattr(s.language, 'value') else str(s.language)
            lang_dir = _LANG_DIRS.get(lang, "misc")
            path = f"src/{lang_dir}/{s.filename}"
            files.append({
                "id": s.id,
                "path": path,
                "filename": s.filename,
                "language": lang,
                "quality": round(s.quality, 2),
                "has_bugs": s.has_bugs,
                "reviewed": s.reviewed,
                "lines": s.lines,
                "author_id": s.author_id,
                "tick_created": s.tick_created,
            })
            tree.setdefault(f"src/{lang_dir}", []).append(s.filename)

        gh_pushed = False
        try:
            from systems.github_integration import is_project_pushed, is_enabled
            if is_enabled() and sett.project_name:
                gh_pushed = is_project_pushed(sett.project_name)
        except (ImportError, AttributeError, OSError) as exc:
            log.debug("github status check failed: %s", exc)

        return jsonify({
            "project_name": sett.project_name,
            "population": sett.population,
            "total_commits": sett.total_commits,
            "bug_count": sett.bug_count,
            "codebase_size": len(sett.codebase),
            "github_pushed": gh_pushed,
            "tree": tree,
            "files": files,
        })

    @app.route("/api/code/latest")
    def api_code_latest():
        """Recently written code — for visualization."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        if not w.code_snippets:
            return jsonify({"snippet": None})
        latest = max(w.code_snippets.values(), key=lambda s: s.tick_created)
        return jsonify({
            "snippet": {
                "id": latest.id,
                "author_id": latest.author_id,
                "language": latest.language.value,
                "description": latest.description,
                "content": latest.content,
                "quality": round(latest.quality, 2),
                "has_bugs": latest.has_bugs,
                "reviewed": latest.reviewed,
                "lines": latest.lines,
                "filename": latest.filename,
                "tick_created": latest.tick_created,
            }
        })

    @app.route("/api/control", methods=["GET"])
    def api_control_get():
        return jsonify({"paused": get_sim_paused(), "speed": get_sim_speed()})

    @app.route("/api/debug/push-test", methods=["POST"])
    def api_debug_push_test():
        """Test — full batch push simulation."""
        import traceback
        results = []
        try:
            from systems.github_integration import (
                _api_request, _push_file, _generate_readme,
                _GITHUB_USER, _GITHUB_ENABLED, _LANG_DIRS, _pushed_projects
            )
            if not _GITHUB_ENABLED:
                return jsonify({"error": "GitHub not enabled"}), 400

            w = get_world()
            if not w or not w.code_snippets:
                return jsonify({"error": "No code snippets"}), 400

            results.append(f"GitHub user: {_GITHUB_USER}")
            results.append(f"Pushed projects set: {_pushed_projects}")

            # simulate an item like _do_batch_push receives
            snippets = list(w.code_snippets.values())[:3]
            item = {
                "type": "batch",
                "repo": "TestPush",
                "project_name": "TestPush-99",
                "snippets": snippets,
                "tech_stack": [],
                "total_commits": 3,
                "bug_count": 0,
                "population": 10,
                "founded_tick": 0,
                "reason": "test",
            }

            # Step 1: ensure repo
            try:
                _api_request("GET", f"/repos/{_GITHUB_USER}/TestPush")
                results.append("Repo exists")
            except RuntimeError as e:
                if "404" in str(e):
                    _api_request("POST", "/user/repos", {
                        "name": "TestPush",
                        "description": "Test push",
                        "private": False,
                        "auto_init": True,
                    })
                    import time; time.sleep(3)
                    results.append("Repo created")
                else:
                    results.append(f"Repo check error: {e}")
                    return jsonify({"results": results}), 500

            # Step 2: README
            try:
                readme = _generate_readme(item)
                results.append(f"README generated: {len(readme)} chars")
                _push_file("TestPush", "README.md", readme, "test readme")
                results.append("README pushed OK")
            except Exception as e:
                results.append(f"README FAILED: {e}\n{traceback.format_exc()}")

            # Step 3: each snippet
            for snippet in snippets:
                try:
                    lang_name = snippet.language.value if hasattr(snippet.language, 'value') else str(snippet.language)
                    lang_dir = _LANG_DIRS.get(lang_name, "misc")
                    safe_fn = snippet.filename.replace("/", "_").replace("\\", "_")
                    path = f"src/{lang_dir}/{safe_fn}"
                    results.append(f"Pushing: {path} (lang={lang_name}, dir={lang_dir})")
                    _push_file("TestPush", path, snippet.content, f"test: {snippet.description}")
                    results.append(f"  OK: {path}")
                except Exception as e:
                    results.append(f"  FAIL: {path}: {e}")

            return jsonify({"ok": True, "results": results})
        except Exception as e:
            results.append(f"OUTER ERROR: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e), "results": results}), 500

    @app.route("/api/control", methods=["POST"])
    def api_control_post():
        data = request.get_json(force=True) or {}
        if "paused" in data:
            set_sim_paused(bool(data["paused"]))
        if "speed" in data:
            set_sim_speed(int(data["speed"]))
        socketio.emit("control_changed", {
            "paused": get_sim_paused(), "speed": get_sim_speed()
        })
        return jsonify({"ok": True, "paused": get_sim_paused(), "speed": get_sim_speed()})

    @app.route("/api/reset", methods=["POST"])
    def api_reset():
        """Simulation restart — new world."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        
        # stop
        set_sim_paused(True)
        socketio.emit("control_changed", {"paused": True, "speed": get_sim_speed()})
        
        try:
            # clear GitHub pushed_projects
            try:
                from systems.github_integration import _pushed_projects
                _pushed_projects.clear()
            except (ImportError, AttributeError) as exc:
                log.debug("github pushed_projects clear skipped: %s", exc)
            
            # clear shared_project history and user-request queue
            try:
                from systems.shared_project import completed_projects, _used_names, _requested_projects
                completed_projects.clear()
                _used_names.clear()
                _requested_projects.clear()
            except (ImportError, AttributeError) as exc:
                log.debug("shared_project clear skipped: %s", exc)
            
            # world reset
            w.reset()
            
            return jsonify({"ok": True, "tick": w.tick})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/save", methods=["POST"])
    def api_save():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        try:
            from persistence.save_load import save_world
            import os
            path = save_world(w)
            return jsonify({"ok": True, "path": os.path.basename(path)})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/load", methods=["POST"])
    def api_load():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        try:
            from persistence.save_load import load_world, get_autosave_path, get_latest_save
            import os
            autosave = get_autosave_path()
            latest = get_latest_save()
            load_path = None
            if os.path.exists(autosave):
                load_path = autosave
            if latest and (not load_path or os.path.getmtime(latest) > os.path.getmtime(load_path)):
                load_path = latest
            if load_path and load_world(w, load_path):
                return jsonify({"ok": True, "file": os.path.basename(load_path), "tick": w.tick})
            return jsonify({"error": "No save found"}), 404
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ================== GitHub Token Configuration ==================

    @app.route("/api/github/configure", methods=["POST"])
    def api_github_configure():
        data = request.get_json(silent=True)
        if not data or not data.get("token"):
            return jsonify({"error": "token is required"}), 400
        token = data["token"].strip()
        if not token.startswith(("ghp_", "gho_", "github_pat_")):
            return jsonify({"error": "Invalid token format"}), 400
        try:
            from systems.github_integration import configure as gh_configure, get_user, get_stats
            if gh_configure(token):
                return jsonify({"ok": True, "user": get_user(), "stats": get_stats()})
            return jsonify({"error": "Failed to connect — check token"}), 400
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/github/disconnect", methods=["POST"])
    def api_github_disconnect():
        try:
            from systems import github_integration as gh
            gh._GITHUB_ENABLED = False
            gh._GITHUB_TOKEN = None
            gh._GITHUB_USER = None
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/github/status")
    def api_github_status():
        try:
            from systems.github_integration import get_stats, is_enabled, get_user
            return jsonify({
                "enabled": is_enabled(),
                "user": get_user(),
                "stats": get_stats() if is_enabled() else None,
            })
        except Exception:
            return jsonify({"enabled": False, "user": None, "stats": None})

    # ================== Custom Project Request ==================

    @app.route("/api/project/request", methods=["POST"])
    def api_project_request():
        """Add user-requested project to queue."""
        data = request.get_json(silent=True)
        if not data or not data.get("name"):
            return jsonify({"error": "name is required"}), 400
        name = data["name"].strip()
        if not name or len(name) > 50:
            return jsonify({"error": "Name must be 1-50 characters"}), 400
        try:
            from systems.shared_project import queue_project, get_project_queue
            proj = queue_project(
                name=name,
                description=data.get("description", ""),
                tech_stack=data.get("tech_stack", []),
                max_files=int(data.get("max_files", 0)),
            )
            return jsonify({"ok": True, "queued": proj, "queue_size": len(get_project_queue())})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/project/queue")
    def api_project_queue():
        """Queue of requested projects."""
        try:
            from systems.shared_project import get_project_queue
            return jsonify({"queue": get_project_queue()})
        except Exception:
            return jsonify({"queue": []})

    # ================== Metrics / Analytics ==================

    @app.route("/api/metrics")
    def api_metrics():
        """Aggregated stats for dashboards / B2B analytics."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        alive = [e for e in w.entities if e.alive]
        quality_vals = [e.code_quality for e in alive if e.code_quality > 0]
        avg_quality = sum(quality_vals) / len(quality_vals) if quality_vals else 0.0
        bugs_live = sum(1 for e in alive if e.entity_type.value == "Bug")
        commits = sum(e.commits for e in alive)
        reviews = sum(e.reviews_done for e in alive)
        bugs_fixed = sum(e.bugs_fixed for e in alive)
        avg_reputation = (sum(getattr(e, "reputation", 0.5) for e in alive) / len(alive)) if alive else 0.0
        burnout_active = sum(1 for e in alive if getattr(e, "burnout", False))
        high_reputation = sum(1 for e in alive if getattr(e, "reputation", 0.5) >= 0.7)
        team_memory = getattr(w, "_team_memory", []) or []
        team_memory_quality_avg = (sum(m.get("quality", 0.0) for m in team_memory) / len(team_memory)) if team_memory else 0.0

        active_wars = sum(1 for war in w.wars if war.is_active)
        souls = getattr(w, "souls", {}) or {}
        souls_living = sum(1 for s in souls.values()
                           if s.entity_id is not None and s.entity_id >= 0)

        return jsonify({
            "tick": w.tick,
            "era": w.era,
            "population": {
                "total": len(alive),
                "by_type": _pop_by_type(alive),
            },
            "code": {
                "total_generated": w.total_code_generated,
                "avg_quality": round(avg_quality, 3),
                "commits": commits,
                "reviews": reviews,
                "bugs_fixed": bugs_fixed,
                "bugs_live": bugs_live,
                "snippets": len(w.code_snippets),
            },
            "projects": {
                "settlements": len(w.settlements),
                "active_wars": active_wars,
                "trade_routes": sum(1 for tr in w.trade_routes if tr.active),
            },
            "souls": {
                "total": len(souls),
                "living": souls_living,
                "dormant": len(souls) - souls_living,
            },
            "cumulative": {
                "born": w.total_born,
                "died": w.total_died,
                "matings": w.total_matings,
                "interactions": w.total_interactions,
                "knowledge_discovered": w.total_knowledge_discovered,
                "mentorships": getattr(w, "total_mentorships", 0),
                "burnouts": getattr(w, "total_burnouts", 0),
                "migrations": getattr(w, "total_migrations", 0),
            },
            "lifecycle": {
                "burnout_active": burnout_active,
                "avg_reputation": round(avg_reputation, 3),
                "high_reputation": high_reputation,
                "team_memory_entries": len(team_memory),
                "team_memory_avg_quality": round(team_memory_quality_avg, 3),
            },
            "internet": {
                "portals": len(getattr(w, "web_portals", [])),
                "portal_trips": int(getattr(w, "total_portal_trips", 0)),
                "web_reports": int(getattr(w, "total_web_reports", 0)),
                "open_source_growth": round(float(getattr(w, "open_source_growth", 0.0)), 3),
            },
        })

    @app.route("/api/metrics/timeseries")
    def api_metrics_timeseries():
        """Recent population / energy history for charts."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        return jsonify({
            "tick": w.tick,
            "population": {
                "developer": list(w.pop_developer),
                "bug": list(w.pop_bug),
                "refactorer": list(w.pop_refactorer),
                "copilot": list(w.pop_copilot),
                "senior": list(w.pop_senior),
                "intern": list(w.pop_intern),
                "total": list(w.pop_total),
            },
            "energy_avg": list(w.energy_avg),
        })

    @app.route("/api/b2b/readiness")
    def api_b2b_readiness():
        """Operational + product readiness score for B2B packaging."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503

        alive = [e for e in w.entities if e.alive]
        total = len(w.entities)
        alive_n = len(alive)
        bug_live = sum(1 for e in alive if e.entity_type.value == "Bug")

        quality_vals = [e.code_quality for e in alive if e.code_quality > 0]
        avg_quality = sum(quality_vals) / len(quality_vals) if quality_vals else 0.0

        commits = sum(e.commits for e in alive)
        reviews = sum(e.reviews_done for e in alive)
        bugs_fixed = sum(e.bugs_fixed for e in alive)
        review_coverage = reviews / max(1, commits)
        bug_fix_ratio = bugs_fixed / max(1, bug_live + bugs_fixed)
        bug_pressure = bug_live / max(1, alive_n)

        pop_series = list(w.pop_total)
        pop_stdev = statistics.pstdev(pop_series) if len(pop_series) >= 2 else 0.0

        step_samples = list(getattr(w, "step_ms_samples", []))
        step_ema = float(getattr(w, "step_ms_ema", 0.0) or 0.0)
        step_p95 = 0.0
        if step_samples:
            sorted_samples = sorted(step_samples)
            idx = min(len(sorted_samples) - 1, int(len(sorted_samples) * 0.95))
            step_p95 = sorted_samples[idx]

        active_wars = sum(1 for war in w.wars if war.is_active)
        uptime_s = float(get_server_uptime_seconds())
        uptime_min = uptime_s / 60.0

        score = 0
        blockers = []
        strengths = []

        if uptime_min >= 30:
            score += 10
            strengths.append("runtime stability window >= 30m")
        elif uptime_min >= 10:
            score += 7
            strengths.append("runtime stability window >= 10m")
        else:
            blockers.append("low uptime sample (<10m) for reliability evidence")

        if 100 <= alive_n <= int(config.MAX_ENTITIES * 0.9):
            score += 12
            strengths.append("population within healthy operating band")
        else:
            blockers.append("population outside healthy operating band")

        if pop_stdev >= 3:
            score += 8
            strengths.append("population shows organic dynamics (not static)")
        else:
            blockers.append("population dynamics too flat; lifecycle tuning still needed")

        if avg_quality >= 0.65:
            score += 12
            strengths.append("code quality baseline is strong")
        elif avg_quality >= 0.5:
            score += 7
        else:
            blockers.append("code quality below B2B confidence threshold")

        if review_coverage >= 0.6:
            score += 10
            strengths.append("review coverage is healthy")
        elif review_coverage >= 0.35:
            score += 6
        else:
            blockers.append("low review coverage per commit")

        if bug_pressure <= 0.2:
            score += 10
            strengths.append("live bug pressure is controlled")
        elif bug_pressure <= 0.3:
            score += 6
        else:
            blockers.append("bug pressure too high")

        if bug_fix_ratio >= 0.55:
            score += 8
            strengths.append("bug resolution rate is acceptable")
        else:
            blockers.append("bug fix throughput is low")

        if step_p95 > 0:
            if step_p95 <= 30:
                score += 12
                strengths.append("tick latency p95 <= 30ms")
            elif step_p95 <= 60:
                score += 8
            elif step_p95 <= 120:
                score += 4
            else:
                blockers.append("tick latency p95 too high for stable multi-tenant workloads")
        else:
            blockers.append("missing tick latency samples")

        if active_wars <= 3:
            score += 8
        else:
            blockers.append("too many active conflicts; simulation instability risk")

        tier = "prototype"
        if score >= 80:
            tier = "b2b-ready"
        elif score >= 60:
            tier = "pilot-ready"
        elif score >= 40:
            tier = "pre-pilot"

        milestones = [
            {
                "name": "Pilot Reliability",
                "target": "14-day uninterrupted run with automated alerts",
                "status": "done" if uptime_min >= 14 * 24 * 60 else "todo",
            },
            {
                "name": "Quality Governance",
                "target": "avg_quality >= 0.65 and review_coverage >= 0.60",
                "status": "done" if (avg_quality >= 0.65 and review_coverage >= 0.60) else "todo",
            },
            {
                "name": "Operational Performance",
                "target": "tick p95 <= 60ms",
                "status": "done" if (step_p95 and step_p95 <= 60) else "todo",
            },
            {
                "name": "Customer Packaging",
                "target": "tenant auth, billing, usage quotas, SLAs",
                "status": "todo",
            },
        ]

        return jsonify({
            "score": score,
            "tier": tier,
            "blockers": blockers,
            "strengths": strengths,
            "kpis": {
                "uptime_seconds": round(uptime_s, 1),
                "population_alive": alive_n,
                "population_total_list": total,
                "population_stddev": round(pop_stdev, 3),
                "avg_code_quality": round(avg_quality, 4),
                "review_coverage": round(review_coverage, 4),
                "bug_fix_ratio": round(bug_fix_ratio, 4),
                "bug_pressure": round(bug_pressure, 4),
                "active_wars": active_wars,
                "tick_ms_ema": round(step_ema, 3),
                "tick_ms_p95": round(step_p95, 3),
            },
            "milestones": milestones,
            "valuation_path": {
                "stage_now": "prototype_to_pilot",
                "target_band_usd": "1M-10M",
                "focus": [
                    "pilot customers",
                    "retention + recurring usage",
                    "operational SLO compliance",
                    "clear pricing and packaging",
                ],
            },
        })

    @app.route("/api/audit")
    def api_audit():
        """Tail of the structured audit log."""
        n = _safe_int_arg("n", 100, lo=1, hi=1000)
        try:
            from persistence.audit import tail
            return jsonify({"events": tail(n)})
        except Exception as exc:
            return jsonify({"error": str(exc), "events": []}), 500

    # ================== Civilization (goal + governance + era) ==================

    @app.route("/api/civilization")
    def api_civilization():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        try:
            from systems.legacy import detect_era_name
            goal = getattr(w, "civilization_goal", None)
            gov = getattr(w, "governance", None)
            proposals = []
            flags = {}
            if gov is not None:
                proposals = [p.to_dict() for p in gov.proposals[-20:]]
                flags = dict(gov.flags)
            return jsonify({
                "tick": w.tick,
                "era": detect_era_name(w),
                "era_num": getattr(w, "era", 1),
                "goal": goal.to_dict() if goal else None,
                "proposals": proposals,
                "flags": flags,
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/civilization/vote", methods=["POST"])
    def api_civilization_vote():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()[:80]
        description = (data.get("description") or "").strip()[:240]
        if not title:
            return jsonify({"error": "title is required"}), 400
        try:
            from systems.governance import vote, _ensure_state
            _ensure_state(w)
            p = vote(w, title, description)
            return jsonify({"proposal": p.to_dict()})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ================== Souls (persistent personas) ==================

    @app.route("/api/souls")
    def api_souls():
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        souls = getattr(w, "souls", {}) or {}
        out = []
        for s in souls.values():
            out.append({
                "id": s.id,
                "name": s.name,
                "role": s.role,
                "entity_id": s.entity_id,
                "born_tick": s.born_tick,
                "rebirth_count": s.rebirth_count,
                "memories": len(s.memory),
                "dormant": s.entity_id is None or s.entity_id < 0,
                "openclaw_bound": s.openclaw_bound,
                "reflection": (s.reflection or "")[:240],
                "profile": (getattr(s, "profile", "") or "")[:240],
                "skills": [sk.get("name") for sk in getattr(s, "skills", [])][:12],
                "skill_count": len(getattr(s, "skills", [])),
            })
        return jsonify({"souls": out, "count": len(out)})

    @app.route("/api/soul/<soul_id>")
    def api_soul_detail(soul_id: str):
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        souls = getattr(w, "souls", {}) or {}
        s = souls.get(soul_id)
        if s is None:
            return jsonify({"error": "Soul not found"}), 404
        return jsonify({
            "soul": s.to_dict(),
        })

    @app.route("/api/soul/<soul_id>/memory", methods=["POST"])
    def api_soul_add_memory(soul_id: str):
        """Inject an external memory (e.g. from OpenClaw / admin)."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        souls = getattr(w, "souls", {}) or {}
        s = souls.get(soul_id)
        if s is None:
            return jsonify({"error": "Soul not found"}), 404
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text or len(text) > 400:
            return jsonify({"error": "text is required (1-400 chars)"}), 400
        kind = (data.get("kind") or "external").strip()[:32]
        try:
            weight = float(data.get("weight", 0.7))
        except (TypeError, ValueError):
            weight = 0.7
        weight = max(0.0, min(1.0, weight))
        s.remember(w.tick, kind, text, weight=weight)
        try:
            from persistence.soul_store import save_soul
            save_soul(s)
        except Exception as exc:
            log.debug("soul save after memory failed: %s", exc)
        return jsonify({"ok": True, "memories": len(s.memory)})

    @app.route("/api/soul/<soul_id>/speak", methods=["POST"])
    def api_soul_speak(soul_id: str):
        """Generate an in-character line from this soul (LLM-backed)."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        souls = getattr(w, "souls", {}) or {}
        s = souls.get(soul_id)
        if s is None:
            return jsonify({"error": "Soul not found"}), 404
        data = request.get_json(silent=True) or {}
        prompt_q = (data.get("question") or "").strip()[:400]
        provider = getattr(getattr(w, "brain", None), "provider", None)
        if provider is None:
            return jsonify({"error": "LLM not connected"}), 503
        composed = (
            f"You are {s.name}, a {s.role}. Persona: {s.personality_summary[:300]}. "
            f"Reflection: {s.reflection[:200]}. "
            f"Question from outside: {prompt_q or 'Tell me something about your work.'} "
            "Reply with ONE short in-character line (max 240 chars). No meta."
        )
        try:
            text = provider.generate(composed, max_tokens=120, temperature=0.8)
            text = (text or "").strip().replace("\n", " ")[:240]
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
        if text:
            s.remember(w.tick, "external",
                       f"Outside asked: {prompt_q[:80]} — said: {text[:120]}",
                       weight=0.5)
            try:
                from persistence.soul_store import save_soul
                save_soul(s)
            except (OSError, ValueError) as exc:
                log.debug("save_soul failed: %s", exc)
        return jsonify({"text": text, "name": s.name, "role": s.role})

    @app.route("/api/soul/<soul_id>/bind", methods=["POST"])
    def api_soul_bind(soul_id: str):
        """Toggle OpenClaw binding for this soul (exposes it to the skill bridge)."""
        w = get_world()
        if not w:
            return jsonify({"error": "World not initialized"}), 503
        souls = getattr(w, "souls", {}) or {}
        s = souls.get(soul_id)
        if s is None:
            return jsonify({"error": "Soul not found"}), 404
        data = request.get_json(silent=True) or {}
        s.openclaw_bound = bool(data.get("bound", True))
        try:
            from persistence.soul_store import save_soul
            save_soul(s)
        except (OSError, ValueError) as exc:
            log.debug("save_soul failed: %s", exc)
        return jsonify({"ok": True, "openclaw_bound": s.openclaw_bound})


def _build_chat_context(entity_data: dict, context: dict) -> str:
    lines = []
    e = entity_data

    type_map = {
        "Developer": "Developer", "Bug": "Bug",
        "Refactorer": "Refactorer", "AI Copilot": "AI Copilot",
        "Senior Dev": "Senior", "Intern": "Intern",
    }
    role_map = {
        "Freelancer": "Freelancer", "Team Lead": "Team Lead",
        "Reviewer": "Reviewer", "Architect": "Architect",
        "Tester": "Tester", "DevOps Engineer": "DevOps Engineer",
    }

    etype = type_map.get(str(e['type']), e['type'])
    erole = role_map.get(str(e['role']), e['role'])

    lines.append(f"I am Developer #{e['id']}, {etype}.")
    lines.append(f"Experience: {e['age']} Tick, Energy: {e['energy']:.0%}, Role: {erole}.")

    if e.get("languages"):
        lines.append(f"I know: {', '.join(e['languages'])}.")
    if e.get("commits"):
        lines.append(f"Commits: {e['commits']}, bugs fixed: {e.get('bugs_fixed', 0)}.")

    traits = []
    if e["aggression"] > 0.6:
        traits.append("aggressive debugger")
    elif e["aggression"] < 0.3:
        traits.append("calm coder")
    if e["curiosity"] > 0.6:
        traits.append("curious")
    if e["sociability"] > 0.6:
        traits.append("pair-programmer")
    if traits:
        lines.append(f"traits: {', '.join(traits)}.")

    if e.get("memories"):
        lines.append("Recent memories:")
        for m in e["memories"][-3:]:
            lines.append(f"  - {m}")

    if context.get("settlement"):
        s = context["settlement"]
        lines.append(f"Project: {s.get('name', '?')}, {s['population']} devs.")
        if s.get("is_leader"):
            lines.append("I am Team Lead.")
        if s.get("tech_stack"):
            lines.append(f"Tech stack: {', '.join(s['tech_stack'])}.")

    if context.get("situation"):
        lines.append(f"Situation: {context['situation']}.")

    return "\n".join(lines)
