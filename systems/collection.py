"""图鉴 / 合成 / 遣散。"""

from __future__ import annotations

from typing import Any, Dict, List

from ..core.utils import RARITY_ORDER

from . import player as player_mod
from .tables import tables

CATEGORY_NAME = {
    "historical": "历史武将",
    "obscure": "冷门武将",
    "fictional": "架空武将",
    "custom": "自定义武将",
}


def pokedex(player: Dict[str, Any]) -> Dict[str, Any]:
    t = tables()
    owned = set(player_mod.owned_names(player))
    result: Dict[str, Any] = {"categories": {}, "total": 0, "owned_total": 0}
    for category in ("historical", "obscure", "fictional"):
        names = [
            g["name"]
            for table in [getattr(t, category)]
            for lst in table.values() for g in lst
        ]
        have = sum(1 for n in names if n in owned)
        result["categories"][category] = {
            "label": CATEGORY_NAME[category], "have": have, "total": len(names)
        }
        result["total"] += len(names)
        result["owned_total"] += have
    custom = len(player.get("custom_generals", {}))
    result["categories"]["custom"] = {
        "label": CATEGORY_NAME["custom"], "have": custom, "total": custom
    }
    result["total"] += custom
    result["owned_total"] += custom
    return result


def _next_rarity(rarity: str) -> str:
    if rarity not in RARITY_ORDER:
        return rarity
    idx = RARITY_ORDER.index(rarity)
    return RARITY_ORDER[min(idx + 1, len(RARITY_ORDER) - 1)]


def synthesize(player: Dict[str, Any], rarity: str, count: int = 3) -> Dict[str, Any]:
    """低稀有度合成：消耗 3 名同稀有度武将，获得 1 名更高稀有度随机武将。"""
    if rarity not in RARITY_ORDER:
        return {"ok": False, "reason": "bad_rarity"}
    if rarity == "ssr":
        return {"ok": False, "reason": "max_rarity"}
    team = set(player.get("team", []))
    leader = player.get("leader")
    if leader:
        team.add(leader)
    candidates: List[str] = []
    for name, entry in player.get("generals", {}).items():
        info = tables().get(name)
        if info and info.get("rarity") == rarity and name not in team:
            candidates.append(name)
    if len(candidates) < count:
        return {"ok": False, "reason": "not_enough", "have": len(candidates),
                "need": count, "rarity": rarity}
    # 消耗战力最低的 count 名
    candidates.sort(key=lambda n: player_mod.general_power_of(player, n))
    consumed = candidates[:count]
    for name in consumed:
        player["generals"].pop(name, None)
    next_rarity = _next_rarity(rarity)
    pool = tables().by_rarity(next_rarity)
    import random

    general = random.choice(pool)
    is_new = player_mod.add_general(player, general["name"])
    player_mod.save(player)
    return {
        "ok": True,
        "consumed": consumed,
        "general": general["name"],
        "rarity": next_rarity,
        "duplicate": not is_new,
    }


def dismiss_custom(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    if name not in player.get("custom_generals", {}):
        return {"ok": False, "reason": "not_custom"}
    player["custom_generals"].pop(name, None)
    if name in player.get("team", []):
        player["team"].remove(name)
    if player.get("leader") == name:
        player["leader"] = ""
    player_mod.save(player)
    return {"ok": True, "name": name,
            "capacity": player_mod.custom_capacity(player),
            "used": player_mod.custom_count(player)}


def dismantle(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    """分解武将换取将魂。"""
    if name in player.get("team", []) or player.get("leader") == name:
        return {"ok": False, "reason": "in_team"}
    if name in player.get("generals", {}):
        info = tables().get(name)
        rarity = info.get("rarity", "n") if info else "n"
        player["generals"].pop(name, None)
    elif name in player.get("custom_generals", {}):
        custom = player["custom_generals"].pop(name, {})
        from ..core.utils import base_power

        rarity = "r" if base_power(custom) > 200 else "n"
    else:
        return {"ok": False, "reason": "not_owned"}
    if player.get("leader") == name:
        player["leader"] = ""
    soul_gain = {"n": 5, "r": 10, "sr": 25, "ssr": 60}.get(rarity, 5)
    player.setdefault("wallet", {})
    player["wallet"]["soul"] = int(player["wallet"].get("soul", 0)) + soul_gain
    player_mod.save(player)
    return {"ok": True, "name": name, "soul": soul_gain,
            "soul_total": player["wallet"]["soul"]}
