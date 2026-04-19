"""Neo4j graph database — code world relationships."""

from __future__ import annotations

import logging
from typing import Optional

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DB

log = logging.getLogger("graph_db")


class GraphDB:

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER,
                 password: str = NEO4J_PASSWORD):
        self.driver = None
        self.connected = False
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            self.connected = True
            log.info("Neo4j connected: %s", uri)
            self._ensure_indexes()
        except (ServiceUnavailable, AuthError, OSError) as exc:
            log.warning("Neo4j unavailable (%s) — continuing without graph.", exc)
            self.connected = False

    def close(self):
        if self.driver:
            self.driver.close()
            self.connected = False

    def _ensure_indexes(self):
        with self.driver.session(database=NEO4J_DB) as s:
            s.run("CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.eid)")
            s.run("CREATE INDEX group_id IF NOT EXISTS FOR (g:Group) ON (g.gid)")
            s.run("CREATE INDEX memory_tick IF NOT EXISTS FOR (m:Memory) ON (m.tick)")
            s.run("CREATE INDEX knowledge_id IF NOT EXISTS FOR (k:Knowledge) ON (k.kid)")
            s.run("CREATE INDEX code_id IF NOT EXISTS FOR (c:Code) ON (c.cid)")

    def sync_entities(self, entities: list, tick: int):
        if not self.connected:
            return
        data = []
        for e in entities:
            data.append({
                "eid": e.id,
                "etype": e.entity_type.value,
                "gender": e.gender.value,
                "generation": e.generation,
                "energy": round(e.energy, 3),
                "age": e.age,
                "alive": e.alive,
                "group_id": e.group_id,
                "x": round(e.x, 1),
                "y": round(e.y, 1),
                "aggression": round(e.aggression, 3),
                "curiosity": round(e.curiosity, 3),
                "sociability": round(e.sociability, 3),
                "resilience": round(e.resilience, 3),
                "active_instinct": e.instincts.active.value if e.instincts.active else None,
                "commits": e.commits,
                "bugs_fixed": e.bugs_fixed,
                "languages": [l.value for l in e.languages_known] if e.languages_known else [],
                "tick": tick,
            })
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._merge_entities_tx, data)
        except Exception as exc:
            log.error("sync_entities error: %s", exc)

    @staticmethod
    def _merge_entities_tx(tx, data):
        tx.run("""
            UNWIND $data AS d
            MERGE (e:Entity {eid: d.eid})
            SET e.etype = d.etype,
                e.gender = d.gender,
                e.generation = d.generation,
                e.energy = d.energy,
                e.age = d.age,
                e.alive = d.alive,
                e.group_id = d.group_id,
                e.x = d.x, e.y = d.y,
                e.aggression = d.aggression,
                e.curiosity = d.curiosity,
                e.sociability = d.sociability,
                e.resilience = d.resilience,
                e.active_instinct = d.active_instinct,
                e.commits = d.commits,
                e.bugs_fixed = d.bugs_fixed,
                e.languages = d.languages,
                e.last_tick = d.tick
        """, data=data)

    def mark_dead(self, entity_ids: list[int], tick: int):
        if not self.connected or not entity_ids:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._mark_dead_tx, entity_ids, tick)
        except Exception as exc:
            log.error("mark_dead error: %s", exc)

    @staticmethod
    def _mark_dead_tx(tx, eids, tick):
        tx.run("""
            UNWIND $eids AS eid
            MATCH (e:Entity {eid: eid})
            SET e.alive = false, e.died_tick = $tick
        """, eids=eids, tick=tick)

    def sync_relationships(self, rel_updates: list[dict]):
        if not self.connected or not rel_updates:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._merge_rels_tx, rel_updates)
        except Exception as exc:
            log.error("sync_relationships error: %s", exc)

    @staticmethod
    def _merge_rels_tx(tx, rels):
        tx.run("""
            UNWIND $rels AS r
            MATCH (a:Entity {eid: r.from_id})
            MATCH (b:Entity {eid: r.to_id})
            MERGE (a)-[k:KNOWS]->(b)
            SET k.strength = r.strength
        """, rels=rels)

    def sync_parents(self, parent_links: list[dict]):
        if not self.connected or not parent_links:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._merge_parents_tx, parent_links)
        except Exception as exc:
            log.error("sync_parents error: %s", exc)

    @staticmethod
    def _merge_parents_tx(tx, links):
        tx.run("""
            UNWIND $links AS l
            MATCH (p:Entity {eid: l.parent_id})
            MATCH (c:Entity {eid: l.child_id})
            MERGE (p)-[:PARENT_OF]->(c)
        """, links=links)

    def sync_groups(self, groups_data: list[dict], memberships: list[dict]):
        if not self.connected:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                if groups_data:
                    s.execute_write(self._merge_groups_tx, groups_data)
                if memberships:
                    s.execute_write(self._merge_memberships_tx, memberships)
        except Exception as exc:
            log.error("sync_groups error: %s", exc)

    @staticmethod
    def _merge_groups_tx(tx, gdata):
        tx.run("""
            UNWIND $gdata AS g
            MERGE (gr:Group {gid: g.gid})
            SET gr.food_pref = g.food_pref,
                gr.aggression = g.aggression,
                gr.cooperation = g.cooperation
        """, gdata=gdata)

    @staticmethod
    def _merge_memberships_tx(tx, memberships):
        tx.run("""
            UNWIND $memberships AS m
            MATCH (e:Entity {eid: m.eid})
            MATCH (g:Group {gid: m.gid})
            MERGE (e)-[:MEMBER_OF]->(g)
        """, memberships=memberships)

    def batch_add_bug_reports(self, reports: list[dict]):
        if not self.connected or not reports:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._batch_bug_reports_tx, reports)
        except Exception as exc:
            log.error("batch_add_bug_reports error: %s", exc)

    @staticmethod
    def _batch_bug_reports_tx(tx, reports):
        tx.run("""
            UNWIND $reports AS r
            MATCH (b:Entity {eid: r.bug_id})
            MATCH (d:Entity {eid: r.dev_id})
            CREATE (b)-[:REPORTED_TO {tick: r.tick, snippet_id: r.snippet_id, snippet_desc: r.snippet_desc}]->(d)
        """, reports=reports)

    def batch_add_matings(self, matings: list[dict]):
        if not self.connected or not matings:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._batch_matings_tx, matings)
        except Exception as exc:
            log.error("batch_add_matings error: %s", exc)

    @staticmethod
    def _batch_matings_tx(tx, matings):
        tx.run("""
            UNWIND $matings AS m
            MATCH (a:Entity {eid: m.parent_a})
            MATCH (b:Entity {eid: m.parent_b})
            MERGE (a)-[:PAIRED_WITH {tick: m.tick}]->(b)
            WITH a, b, m
            MATCH (c:Entity {eid: m.child_id})
            MERGE (a)-[:PARENT_OF]->(c)
            MERGE (b)-[:PARENT_OF]->(c)
        """, matings=matings)

    def batch_add_memories(self, memories: list[dict]):
        if not self.connected or not memories:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._batch_memories_tx, memories)
        except Exception as exc:
            log.error("batch_add_memories error: %s", exc)

    @staticmethod
    def _batch_memories_tx(tx, batch):
        tx.run("""
            UNWIND $batch AS m
            MATCH (e:Entity {eid: m.eid})
            CREATE (mem:Memory {tick: m.tick, event: m.event, value: m.value})
            CREATE (e)-[:REMEMBERS]->(mem)
            WITH mem, m
            WHERE m.other_id IS NOT NULL
            MATCH (o:Entity {eid: m.other_id})
            CREATE (mem)-[:ABOUT]->(o)
        """, batch=batch)

    def batch_add_discoveries(self, discoveries: list[dict]):
        if not self.connected or not discoveries:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._batch_discoveries_tx, discoveries)
        except Exception as exc:
            log.error("batch_add_discoveries error: %s", exc)

    @staticmethod
    def _batch_discoveries_tx(tx, discoveries):
        tx.run("""
            UNWIND $discoveries AS d
            CREATE (k:Knowledge {kid: d.kid, ktype: d.ktype, name: d.name, tick: d.tick})
            WITH k, d
            WHERE d.eid IS NOT NULL
            MATCH (e:Entity {eid: d.eid})
            CREATE (e)-[:DISCOVERED]->(k)
        """, discoveries=discoveries)

    def batch_add_code(self, code_entries: list[dict]):
        if not self.connected or not code_entries:
            return
        try:
            with self.driver.session(database=NEO4J_DB) as s:
                s.execute_write(self._batch_code_tx, code_entries)
        except Exception as exc:
            log.error("batch_add_code error: %s", exc)

    @staticmethod
    def _batch_code_tx(tx, entries):
        tx.run("""
            UNWIND $entries AS c
            CREATE (code:Code {cid: c.cid, language: c.language, quality: c.quality,
                               filename: c.filename, tick: c.tick})
            WITH code, c
            MATCH (e:Entity {eid: c.author_id})
            CREATE (e)-[:WROTE]->(code)
        """, entries=entries)

    def get_entity_graph(self, entity_id: int) -> dict:
        if not self.connected:
            return {}
        with self.driver.session(database=NEO4J_DB) as s:
            result = s.run("""
                MATCH (e:Entity {eid: $eid})
                OPTIONAL MATCH (e)-[k:KNOWS]->(friend:Entity)
                OPTIONAL MATCH (e)-[:PARENT_OF]->(child:Entity)
                OPTIONAL MATCH (parent:Entity)-[:PARENT_OF]->(e)
                OPTIONAL MATCH (e)-[:MEMBER_OF]->(g:Group)
                OPTIONAL MATCH (e)-[:REMEMBERS]->(mem:Memory)
                OPTIONAL MATCH (e)-[:WROTE]->(code:Code)
                RETURN e,
                       collect(DISTINCT {fid: friend.eid, strength: k.strength}) AS friends,
                       collect(DISTINCT child.eid) AS children,
                       collect(DISTINCT parent.eid) AS parents,
                       g.gid AS group_id,
                       collect(DISTINCT {tick: mem.tick, event: mem.event}) AS memories,
                       collect(DISTINCT {cid: code.cid, lang: code.language}) AS code_written
            """, eid=entity_id)
            record = result.single()
            if not record:
                return {}
            return {
                "entity": dict(record["e"]),
                "friends": [f for f in record["friends"] if f["fid"] is not None],
                "children": [c for c in record["children"] if c is not None],
                "parents": [p for p in record["parents"] if p is not None],
                "group_id": record["group_id"],
                "memories": record["memories"][:20],
                "code_written": [c for c in record["code_written"] if c["cid"] is not None],
            }

    def get_strongest_bonds(self, limit: int = 20) -> list[dict]:
        if not self.connected:
            return []
        with self.driver.session(database=NEO4J_DB) as s:
            result = s.run("""
                MATCH (a:Entity)-[k:KNOWS]->(b:Entity)
                WHERE k.strength > 0.3
                RETURN a.eid AS from_id, b.eid AS to_id, k.strength AS strength
                ORDER BY k.strength DESC
                LIMIT $limit
            """, limit=limit)
            return [dict(r) for r in result]

    def clear_all(self):
        if not self.connected:
            return
        with self.driver.session(database=NEO4J_DB) as s:
            s.run("MATCH (n) DETACH DELETE n")
