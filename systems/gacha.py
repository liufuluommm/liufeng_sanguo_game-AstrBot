"""招募：碎片兑换 / 架空招募 / 自定义武将。"""

from __future__ import annotations

import random
from typing import Any, Dict

from ..core.utils import base_power, weighted_choice

from . import player as player_mod
from . import troops as troops_mod
from .tables import tables


def _pick_rarity(rates: Dict[str, float], rng: random.Random) -> str:
    keys = ["ssr", "sr", "r", "n"]
    weights = [rates.get(k, 0.0) for k in keys]
    return weighted_choice(keys, weights)


def exchange_historical(player: Dict[str, Any], cost: int, rates: Dict[str, float],
                        rng: random.Random = random) -> Dict[str, Any]:
    """消耗通用碎片随机兑换历史/冷门武将，必定成功。"""
    if int(player.get("fragments", 0)) < cost:
        return {
            "ok": False,
            "reason": "fragments",
            "fragments": int(player.get("fragments", 0)),
            "need": cost,
        }
    player["fragments"] = int(player.get("fragments", 0)) - cost
    rarity = _pick_rarity(rates, rng)
    pool = tables().by_rarity(rarity) or tables().by_rarity("n")
    if not pool:
        return {"ok": False, "reason": "empty_pool"}
    general = rng.choice(pool)
    name = general["name"]
    is_new = player_mod.add_general(player, name)
    player_mod.save(player)
    return {
        "ok": True,
        "type": "exchange",
        "general": name,
        "rarity": rarity,
        "duplicate": not is_new,
        "fragments_left": player["fragments"],
        "cost": cost,
    }


def recruit_fictional(player: Dict[str, Any], cost: int, fail_min: float,
                      fail_max: float, rates: Dict[str, float],
                      rng: random.Random = random) -> Dict[str, Any]:
    """金币招募架空武将，失败率在 [fail_min, fail_max] 内每次随机。"""
    if int(player.get("gold", 0)) < cost:
        return {"ok": False, "reason": "gold", "gold": player.get("gold", 0), "need": cost}
    player_mod.add_gold(player, -cost)
    fail_rate = rng.uniform(fail_min, fail_max)
    if rng.random() < fail_rate:
        player_mod.save(player)
        return {
            "ok": False,
            "reason": "failed",
            "fail_rate": fail_rate,
            "gold_left": player["gold"],
            "cost": cost,
        }
    rarity = _pick_rarity(rates, rng)
    pool = tables().by_rarity_category("fictional", rarity)
    if not pool:
        return {"ok": False, "reason": "empty_pool"}
    general = rng.choice(pool)
    name = general["name"]
    is_new = player_mod.add_general(player, name)
    player_mod.save(player)
    return {
        "ok": True,
        "type": "fictional",
        "general": name,
        "rarity": rarity,
        "duplicate": not is_new,
        "fail_rate": fail_rate,
        "gold_left": player["gold"],
        "cost": cost,
    }


def recruit_custom(player: Dict[str, Any], name: str, cost: int,
                   stat_min: int, stat_max: int,
                   rng: random.Random = random) -> Dict[str, Any]:
    """自定义武将：固定花费、必定成功、三维随机。"""
    name = (name or "").strip()
    if not name:
        return {"ok": False, "reason": "empty_name"}
    if len(name) > 10:
        return {"ok": False, "reason": "name_too_long"}
    if player_mod.has_general(player, name) or tables().get(name) is not None:
        return {"ok": False, "reason": "name_taken"}
    if player_mod.custom_count(player) >= player_mod.custom_capacity(player):
        return {"ok": False, "reason": "capacity",
                "capacity": player_mod.custom_capacity(player)}
    if int(player.get("gold", 0)) < cost:
        return {"ok": False, "reason": "gold", "gold": player.get("gold", 0), "need": cost}

    player_mod.add_gold(player, -cost)
    from ..core.utils import ATTR_KEYS

    stats = {key: rng.randint(stat_min, stat_max) for key in ATTR_KEYS}
    data = {
        "name": name,
        "faction": "custom",
        "rarity": "custom",
        "category": "custom",
        "title": "",
        "troop": troops_mod.random_basic(rng),
        "level": 1,
        "star": 1,
        "exp": 0,
        "skill_lv": 1,
        "talent": {},
        "equip": {},
        "desc": f"{player.get('name', '玩家')}麾下的自定义武将。",
        **stats,
    }
    player_mod.add_custom_general(player, data)
    player_mod.save(player)
    return {
        "ok": True,
        "type": "custom",
        "general": name,
        "stats": stats,
        "troop": data["troop"],
        "power": base_power(stats),
        "gold_left": player["gold"],
        "cost": cost,
        "capacity": player_mod.custom_capacity(player),
        "custom_count": player_mod.custom_count(player),
    }
