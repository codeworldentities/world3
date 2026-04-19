"""Civilization Goal — global direction the world is trying to achieve.

Lightweight, LLM-free. Watches world-level counters and reports progress
against a named target. Nudges entities toward contributing behaviours by
granting a small energy boost when they help the goal.

One goal at a time; goals can be swapped at runtime via the API.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.world import World
    from core.models import Entity

log = logging.getLogger("core.civilization_goal")


@dataclass
class CivilizationGoal:
    name: str = "produce_high_quality_code"
    target: int = 500                       # commits-equivalent threshold
    progress: int = 0
    started_tick: int = 0
    achieved_tick: int = 0
    achieved: bool = False
    history: list[dict] = field(default_factory=list)
    max_history: int = 10

    def update(self, world: "World") -> None:
        """Recompute progress from world counters. Cheap (O(entities))."""
        if self.name == "produce_high_quality_code":
            commits = sum(getattr(e, "commits", 0) for e in world.entities)
            bugs_fixed = sum(getattr(e, "bugs_fixed", 0) for e in world.entities)
            self.progress = commits + bugs_fixed * 2
        elif self.name == "build_great_settlements":
            self.progress = sum(
                len(getattr(s, "codebase", [])) for s in getattr(world, "settlements", {}).values()
            )
        elif self.name == "survive_and_thrive":
            alive = sum(1 for e in world.entities if e.alive)
            self.progress = alive * 10 + world.tick // 10
        else:
            # Unknown goal — safe no-op
            return

        if not self.achieved and self.progress >= self.target:
            self.achieved = True
            self.achieved_tick = world.tick
            log.info("Civilization goal '%s' achieved at tick %d!", self.name, world.tick)
            self._rotate(world)

    def _rotate(self, world: "World") -> None:
        """On achievement, archive the finished goal and pick the next one."""
        self.history.append({
            "name": self.name,
            "target": self.target,
            "achieved_tick": self.achieved_tick,
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Advance: double the bar and move to the next theme
        ladder = ["produce_high_quality_code", "build_great_settlements", "survive_and_thrive"]
        try:
            nxt = ladder[(ladder.index(self.name) + 1) % len(ladder)]
        except ValueError:
            nxt = "produce_high_quality_code"
        self.name = nxt
        self.target = max(100, self.target * 2)
        self.progress = 0
        self.achieved = False
        self.achieved_tick = 0
        self.started_tick = world.tick

    def influence(self, entity: "Entity") -> None:
        """Tiny motivation nudge for behaviours that advance the goal.
        Called only for productive, non-Bug entities to keep cost O(1)."""
        if self.achieved:
            return
        if self.name == "produce_high_quality_code":
            if getattr(entity, "commits", 0) > 0 or getattr(entity, "bugs_fixed", 0) > 0:
                entity.energy = min(1.0, entity.energy + 0.002)
        elif self.name == "survive_and_thrive":
            entity.energy = min(1.0, entity.energy + 0.001)

    def to_dict(self) -> dict:
        ratio = (self.progress / self.target) if self.target else 0.0
        return {
            "name": self.name,
            "target": self.target,
            "progress": self.progress,
            "ratio": round(min(1.0, ratio), 3),
            "achieved": self.achieved,
            "started_tick": self.started_tick,
            "achieved_tick": self.achieved_tick,
            "history": list(self.history),
        }
