"""Spatial index — QuadTree O(log n) proximity queries."""

from __future__ import annotations
from typing import Optional


class QuadTree:
    """2D spatial index for fast range queries."""

    __slots__ = ("x", "y", "w", "h", "capacity", "items", "divided",
                 "ne", "nw", "se", "sw")

    def __init__(self, x: float, y: float, w: float, h: float, capacity: int = 8):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.capacity = capacity
        self.items: list[tuple[float, float, object]] = []
        self.divided = False
        self.ne: Optional[QuadTree] = None
        self.nw: Optional[QuadTree] = None
        self.se: Optional[QuadTree] = None
        self.sw: Optional[QuadTree] = None

    def contains(self, px: float, py: float) -> bool:
        return (self.x <= px < self.x + self.w and
                self.y <= py < self.y + self.h)

    def intersects(self, rx: float, ry: float, rw: float, rh: float) -> bool:
        return not (rx > self.x + self.w or rx + rw < self.x or
                    ry > self.y + self.h or ry + rh < self.y)

    def subdivide(self):
        hw, hh = self.w / 2, self.h / 2
        self.nw = QuadTree(self.x, self.y, hw, hh, self.capacity)
        self.ne = QuadTree(self.x + hw, self.y, hw, hh, self.capacity)
        self.sw = QuadTree(self.x, self.y + hh, hw, hh, self.capacity)
        self.se = QuadTree(self.x + hw, self.y + hh, hw, hh, self.capacity)
        self.divided = True

    def insert(self, px: float, py: float, data: object) -> bool:
        if not self.contains(px, py):
            return False
        if len(self.items) < self.capacity:
            self.items.append((px, py, data))
            return True
        if not self.divided:
            self.subdivide()
        return (self.ne.insert(px, py, data) or self.nw.insert(px, py, data) or
                self.se.insert(px, py, data) or self.sw.insert(px, py, data))

    def query_range(self, rx: float, ry: float, rw: float, rh: float,
                    found: Optional[list] = None) -> list:
        if found is None:
            found = []
        if not self.intersects(rx, ry, rw, rh):
            return found
        for px, py, data in self.items:
            if rx <= px < rx + rw and ry <= py < ry + rh:
                found.append(data)
        if self.divided:
            self.nw.query_range(rx, ry, rw, rh, found)
            self.ne.query_range(rx, ry, rw, rh, found)
            self.sw.query_range(rx, ry, rw, rh, found)
            self.se.query_range(rx, ry, rw, rh, found)
        return found

    def query_radius(self, cx: float, cy: float, radius: float) -> list:
        candidates = self.query_range(
            cx - radius, cy - radius, radius * 2, radius * 2
        )
        r2 = radius * radius
        return [d for d in candidates
                if hasattr(d, 'x') and hasattr(d, 'y')
                and (d.x - cx) ** 2 + (d.y - cy) ** 2 <= r2]

    def clear(self):
        self.items.clear()
        self.divided = False
        self.ne = self.nw = self.se = self.sw = None


def build_entity_tree(entities, world_w: float, world_h: float) -> QuadTree:
    tree = QuadTree(0, 0, world_w, world_h)
    for e in entities:
        if e.alive:
            tree.insert(e.x, e.y, e)
    return tree


def build_resource_tree(resources, world_w: float, world_h: float) -> QuadTree:
    tree = QuadTree(0, 0, world_w, world_h)
    for r in resources:
        if r.alive:
            tree.insert(r.x, r.y, r)
    return tree
