"""Open Source sharing and Merge Conflicts (Trade & Diplomacy)."""

from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

from core.enums import DiplomacyState, TechType
from core.models import TradeRoute, War
from config import (
    SHARE_MIN_PROJECT_AGE, SHARE_MAX_DISTANCE, SHARE_RESOURCE_AMOUNT,
    SHARE_RELATION_BOOST, SHARE_TECH_SPREAD_CHANCE,
    CONFLICT_TERRITORY_OVERLAP, CONFLICT_AGGRESSION_THRESHOLD,
    CONFLICT_DURATION_TICKS, CONFLICT_CASUALTY_CHANCE,
    CONFLICT_VICTORY_LOOT, CONFLICT_COOLDOWN, DIPLOMACY_DECAY,
)

if TYPE_CHECKING:
    from core.world import World


def update_trade_routes(world: World):
    """Open source sharing route formation."""
    sett_list = list(world.settlements.values())
    existing_pairs = set()
    for tr in world.trade_routes:
        if tr.active:
            existing_pairs.add((tr.settlement_a, tr.settlement_b))
            existing_pairs.add((tr.settlement_b, tr.settlement_a))

    for i, sa in enumerate(sett_list):
        if world.tick - sa.founded_tick < SHARE_MIN_PROJECT_AGE:
            continue
        if sa.population < 3:
            continue
        for sb in sett_list[i + 1:]:
            if world.tick - sb.founded_tick < SHARE_MIN_PROJECT_AGE:
                continue
            if sb.population < 3:
                continue
            if (sa.id, sb.id) in existing_pairs:
                continue
            dist = math.hypot(sa.x - sb.x, sa.y - sb.y)
            if dist > SHARE_MAX_DISTANCE:
                continue
            diplomacy_state = sa.diplomacy.get(sb.id, DiplomacyState.NEUTRAL)
            if diplomacy_state == DiplomacyState.HOSTILE:
                continue
            if random.random() < 0.005:
                world.trade_routes.append(TradeRoute(
                    settlement_a=sa.id, settlement_b=sb.id,
                    established_tick=world.tick,
                ))
                world.total_trades += 1
                sa_name = sa.project_name or f"#{sa.id}"
                sb_name = sb.project_name or f"#{sb.id}"
                world.log_event(f"🔗 Open Source: {sa_name} ↔ {sb_name}")


def execute_trades(world: World):
    """Execute active sharing routes."""
    for tr in world.trade_routes:
        if not tr.active:
            continue
        sa = world.settlements.get(tr.settlement_a)
        sb = world.settlements.get(tr.settlement_b)
        if not sa or not sb:
            tr.active = False
            continue
        if sa.population == 0 or sb.population == 0:
            tr.active = False
            continue

        amount = SHARE_RESOURCE_AMOUNT * tr.strength
        if sa.stored_resources > amount and sb.stored_resources > amount:
            sa.stored_resources -= amount * 0.5
            sb.stored_resources -= amount * 0.5
            sa.stored_resources += amount * 0.6
            sb.stored_resources += amount * 0.6
            tr.total_traded += amount
            tr.strength = min(3.0, tr.strength + 0.01)

            sa.diplomacy[sb.id] = DiplomacyState.OPEN_SOURCE
            sb.diplomacy[sa.id] = DiplomacyState.OPEN_SOURCE

            # technology spread
            if random.random() < SHARE_TECH_SPREAD_CHANCE:
                for tech in sa.techs:
                    if tech not in sb.techs:
                        sb.techs.append(tech)
                        sb_name = sb.project_name or f"#{sb.id}"
                        world.log_event(f"🔄 Tech spread: {tech.value} → {sb_name}")
                        break
                for tech in sb.techs:
                    if tech not in sa.techs:
                        sa.techs.append(tech)
                        sa_name = sa.project_name or f"#{sa.id}"
                        world.log_event(f"🔄 Tech spread: {tech.value} → {sa_name}")
                        break


def update_diplomacy(world: World):
    """Update diplomatic connections."""
    sett_list = list(world.settlements.values())
    for i, sa in enumerate(sett_list):
        for sb in sett_list[i + 1:]:
            cd_key = sb.id
            if cd_key in sa.peace_cooldowns:
                sa.peace_cooldowns[cd_key] -= 50
                if sa.peace_cooldowns[cd_key] <= 0:
                    del sa.peace_cooldowns[cd_key]
                continue

            state = sa.diplomacy.get(sb.id, DiplomacyState.NEUTRAL)
            if state == DiplomacyState.HOSTILE:
                continue

            # territorial conflict → merge conflict
            dist = math.hypot(sa.x - sb.x, sa.y - sb.y)
            if dist < CONFLICT_TERRITORY_OVERLAP:
                ca = world.group_cultures.get(sa.group_id)
                cb = world.group_cultures.get(sb.group_id)
                agg_a = ca.aggression_norm if ca else 0.5
                agg_b = cb.aggression_norm if cb else 0.5
                if (agg_a + agg_b) / 2 > CONFLICT_AGGRESSION_THRESHOLD:
                    if random.random() < 0.02:
                        _declare_merge_conflict(world, sa, sb)
                        continue

            if state == DiplomacyState.OPEN_SOURCE:
                pass
            elif state == DiplomacyState.ALLIED:
                if random.random() < DIPLOMACY_DECAY:
                    sa.diplomacy[sb.id] = DiplomacyState.NEUTRAL
                    sb.diplomacy[sa.id] = DiplomacyState.NEUTRAL


def _declare_merge_conflict(world: World, sa, sb):
    """Declare Merge Conflict (War)."""
    wid = world.next_war_id
    world.next_war_id += 1
    war = War(
        id=wid, group_a=sa.group_id, group_b=sb.group_id,
        started_tick=world.tick,
    )
    world.wars.append(war)
    world.total_wars += 1
    sa.diplomacy[sb.id] = DiplomacyState.HOSTILE
    sb.diplomacy[sa.id] = DiplomacyState.HOSTILE
    sa_name = sa.project_name or f"#{sa.id}"
    sb_name = sb.project_name or f"#{sb.id}"
    world.log_event(f"⚔️ MERGE CONFLICT! {sa_name} vs {sb_name}")
    world.spawn_particles(
        (sa.x + sb.x) / 2, (sa.y + sb.y) / 2,
        (255, 50, 50), count=25, speed=4.0, size=3.0)

    for tr in world.trade_routes:
        if tr.active and (
            (tr.settlement_a == sa.id and tr.settlement_b == sb.id) or
            (tr.settlement_a == sb.id and tr.settlement_b == sa.id)
        ):
            tr.active = False


def update_wars(world: World):
    """Merge Conflict currency and completion."""
    for war in world.wars:
        if not war.is_active:
            continue
        war.duration += 50

        for e in world.entities:
            if not e.alive:
                continue
            if e.group_id == war.group_a and random.random() < CONFLICT_CASUALTY_CHANCE:
                e.energy -= 0.05
                if e.energy <= 0:
                    e.alive = False
                    war.casualties_a += 1
            elif e.group_id == war.group_b and random.random() < CONFLICT_CASUALTY_CHANCE:
                e.energy -= 0.05
                if e.energy <= 0:
                    e.alive = False
                    war.casualties_b += 1

        if war.duration >= CONFLICT_DURATION_TICKS:
            war.resolved = True
            if war.casualties_a < war.casualties_b:
                war.winner = war.group_a
                _resolve_conflict(world, war, war.group_a, war.group_b)
            elif war.casualties_b < war.casualties_a:
                war.winner = war.group_b
                _resolve_conflict(world, war, war.group_b, war.group_a)
            else:
                war.winner = None
                # draw → fork
                for sa in world.settlements.values():
                    for sb in world.settlements.values():
                        if sa.group_id == war.group_a and sb.group_id == war.group_b:
                            sa.diplomacy[sb.id] = DiplomacyState.FORKED
                            sb.diplomacy[sa.id] = DiplomacyState.FORKED

            world.log_event(
                f"✅ Merge resolved! team #{war.group_a} vs team #{war.group_b} "
                f"(casualties: {war.casualties_a}/{war.casualties_b})")

            for sa in world.settlements.values():
                for sb in world.settlements.values():
                    if sa.group_id == war.group_a and sb.group_id == war.group_b:
                        sa.peace_cooldowns[sb.id] = CONFLICT_COOLDOWN
                        sb.peace_cooldowns[sa.id] = CONFLICT_COOLDOWN


def _resolve_conflict(world: World, war, winner_gid, loser_gid):
    """Resolve Merge Conflict — winner takes resources."""
    winner_sett = None
    loser_sett = None
    for s in world.settlements.values():
        if s.group_id == winner_gid:
            winner_sett = s
        if s.group_id == loser_gid:
            loser_sett = s

    if winner_sett and loser_sett:
        loot = loser_sett.stored_resources * CONFLICT_VICTORY_LOOT
        loser_sett.stored_resources -= loot
        winner_sett.stored_resources += loot

        # winner takes tech stack
        for tech in loser_sett.techs:
            if tech not in winner_sett.techs:
                winner_sett.techs.append(tech)

        winner_sett.diplomacy[loser_sett.id] = DiplomacyState.MERGED
        loser_sett.diplomacy[winner_sett.id] = DiplomacyState.MERGED
