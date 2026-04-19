"""Event Bus — decoupled communication between subsystems."""

from __future__ import annotations
from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Simple synchronous publish/subscribe event bus."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        hlist = self._handlers.get(event_type)
        if hlist and handler in hlist:
            hlist.remove(handler)

    def publish(self, event_type: str, **data: Any) -> None:
        for handler in self._handlers.get(event_type, []):
            handler(**data)

    def clear(self) -> None:
        self._handlers.clear()


# ================== Event Types ==================

# Entity lifecycle
ENTITY_BORN = "entity.born"
ENTITY_DIED = "entity.died"
ENTITY_MOVED = "entity.moved"

# Resources
RESOURCE_CONSUMED = "resource.consumed"
RESOURCE_SPAWNED = "resource.spawned"

# Social
INTERACTION = "interaction"
CONVERSATION_START = "conversation.start"
CONVERSATION_END = "conversation.end"
RELATIONSHIP_CHANGED = "relationship.changed"

# Feature creation (reproduction)
FEATURE_CREATED = "feature.created"
FEATURE_FAILED = "feature.failed"

# Debugging (combat)
DEBUG_START = "debug.start"
DEBUG_KILL = "debug.kill"
ENTITY_FLED = "entity.fled"

# Groups / Projects
GROUP_FORMED = "group.formed"
GROUP_DISSOLVED = "group.dissolved"
PROJECT_FOUNDED = "project.founded"
PROJECT_DESTROYED = "project.destroyed"

# Knowledge / Tech
TECH_DISCOVERED = "tech.discovered"
KNOWLEDGE_DISCOVERED = "knowledge.discovered"
KNOWLEDGE_SPREAD = "knowledge.spread"

# Open source sharing (trade)
SHARE_ROUTE_OPENED = "share.route.opened"
SHARE_EXECUTED = "share.executed"
DIPLOMACY_CHANGED = "diplomacy.changed"
MERGE_CONFLICT_STARTED = "merge_conflict.started"
MERGE_CONFLICT_ENDED = "merge_conflict.ended"

# Code generation (NEW!)
CODE_GENERATED = "code.generated"
CODE_REVIEWED = "code.reviewed"
CODE_COMMITTED = "code.committed"
BUG_INTRODUCED = "bug.introduced"
BUG_FIXED = "bug.fixed"

# LLM
LLM_THOUGHT = "llm.thought"
LLM_DIALOGUE = "llm.dialogue"

# God API
GOD_SMITE = "god.smite"
GOD_BLESS = "god.bless"

# aliases — world2 compatibility
MATING_SUCCESS = FEATURE_CREATED
MATING_FAILED = FEATURE_FAILED
HUNT_START = DEBUG_START
HUNT_KILL = DEBUG_KILL
SETTLEMENT_FOUNDED = PROJECT_FOUNDED
SETTLEMENT_DESTROYED = PROJECT_DESTROYED
TRADE_ROUTE_OPENED = SHARE_ROUTE_OPENED
TRADE_EXECUTED = SHARE_EXECUTED
WAR_DECLARED = MERGE_CONFLICT_STARTED
WAR_ENDED = MERGE_CONFLICT_ENDED
