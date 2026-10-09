"""军团（公会）系统（全局跨群）。"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from ..core import storage

from . import player as player_mod

_GLOBAL = "guilds"
CREATE_COST = 5000


def _load() -> Dict[str, Any]:
    data = storage.load_global(_GLOBAL, None)
    if data is None:
        data = {"counter": 0, "guilds": {}}
        storage.save_global(_GLOBAL, data)
    data.setdefault("guilds", {})
    return data


def _save(data: Dict[str, Any]) -> None:
    storage.save_global(_GLOBAL, data)


def create(player: Dict[str, Any], name: str, cost: int = CREATE_COST) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name or len(name) > 12:
        return {"ok": False, "reason": "bad_name"}
    if player.get("guild"):
        return {"ok": False, "reason": "in_guild"}
    if int(player.get("gold", 0)) < cost:
        return {"ok": False, "reason": "gold", "need": cost, "have": player.get("gold", 0)}
    data = _load()
    if any(g["name"] == name for g in data["guilds"].values()):
        return {"ok": False, "reason": "name_taken"}
    player_mod.add_gold(player, -cost)
    data["counter"] = int(data.get("counter", 0)) + 1
    gid = f"G{data['counter']:04d}"
    data["guilds"][gid] = {
        "id": gid, "name": name, "leader": str(player["qq"]),
        "members": {str(player["qq"]): "leader"}, "level": 1, "fund": 0,
        "exp": 0, "created": int(time.time()),
    }
    player["guild"] = gid
    player_mod.save(player)
    _save(data)
    return {"ok": True, "guild": data["guilds"][gid]}


def join(player: Dict[str, Any], gid: str) -> Dict[str, Any]:
    if player.get("guild"):
        return {"ok": False, "reason": "in_guild"}
    data = _load()
    guild = data["guilds"].get(gid)
    if not guild:
        return {"ok": False, "reason": "not_found"}
    if len(guild["members"]) >= 50:
        return {"ok": False, "reason": "full"}
    guild["members"][str(player["qq"])] = "member"
    player["guild"] = gid
    player_mod.save(player)
    _save(data)
    return {"ok": True, "guild": guild}


def leave(player: Dict[str, Any]) -> Dict[str, Any]:
    gid = player.get("guild")
    if not gid:
        return {"ok": False, "reason": "no_guild"}
    data = _load()
    guild = data["guilds"].get(gid)
    if guild:
        guild["members"].pop(str(player["qq"]), None)
        if guild.get("leader") == str(player["qq"]):
            if guild["members"]:
                guild["leader"] = next(iter(guild["members"]))
                guild["members"][guild["leader"]] = "leader"
            else:
                data["guilds"].pop(gid, None)
    player["guild"] = ""
    player_mod.save(player)
    _save(data)
    return {"ok": True}


def donate(player: Dict[str, Any], gold: int) -> Dict[str, Any]:
    gid = player.get("guild")
    if not gid:
        return {"ok": False, "reason": "no_guild"}
    gold = max(1, int(gold))
    if int(player.get("gold", 0)) < gold:
        return {"ok": False, "reason": "gold", "have": player.get("gold", 0)}
    player_mod.add_gold(player, -gold)
    player_mod.save(player)
    data = _load()
    guild = data["guilds"].get(gid)
    if guild:
        guild["fund"] = int(guild.get("fund", 0)) + gold
        guild["exp"] = int(guild.get("exp", 0)) + gold // 10
        # 每 1000 经验升 1 级
        guild["level"] = 1 + int(guild["exp"]) // 1000
    _save(data)
    return {"ok": True, "fund": gold, "guild_level": guild["level"] if guild else 1}


def info(player: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    gid = player.get("guild")
    guild = data["guilds"].get(gid) if gid else None
    return {"guild": guild, "total": len(data["guilds"])}


def top(limit: int = 10) -> List[Dict[str, Any]]:
    data = _load()
    rows = list(data["guilds"].values())
    rows.sort(key=lambda g: (int(g.get("level", 1)), int(g.get("fund", 0))), reverse=True)
    return rows[:limit]
