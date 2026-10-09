"""建筑：武将宿舍。"""

from __future__ import annotations

import random
from typing import Any, Dict

from . import player as player_mod

DORM = "dormitory"
DORM_NAME = "武将宿舍"


def _dorm(player: Dict[str, Any]) -> Dict[str, Any]:
    buildings = player.setdefault("buildings", {})
    dorm = buildings.setdefault(DORM, {"level": 1, "capacity": player_mod.custom_capacity(player)})
    return dorm


def upgrade_cost(player: Dict[str, Any], base: int) -> int:
    dorm = _dorm(player)
    level = int(dorm.get("level", 1))
    return int(base * (2 ** (level - 1)))


def upgrade(player: Dict[str, Any], base_cost: int, gain_min: int, gain_max: int,
            rng: random.Random = random) -> Dict[str, Any]:
    dorm = _dorm(player)
    cost = upgrade_cost(player, base_cost)
    if int(player.get("gold", 0)) < cost:
        return {
            "ok": False,
            "reason": "gold",
            "gold": player.get("gold", 0),
            "need": cost,
        }
    player_mod.add_gold(player, -cost)
    gain = rng.randint(gain_min, gain_max)
    dorm["level"] = int(dorm.get("level", 1)) + 1
    dorm["capacity"] = int(dorm.get("capacity", 0)) + gain
    player_mod.save(player)
    return {
        "ok": True,
        "level": dorm["level"],
        "capacity": dorm["capacity"],
        "gain": gain,
        "cost": cost,
        "next_cost": upgrade_cost(player, base_cost),
        "gold_left": player["gold"],
    }


def status(player: Dict[str, Any], base_cost: int) -> Dict[str, Any]:
    dorm = _dorm(player)
    return {
        "level": int(dorm.get("level", 1)),
        "capacity": int(dorm.get("capacity", 0)),
        "used": player_mod.custom_count(player),
        "next_cost": upgrade_cost(player, base_cost),
    }
