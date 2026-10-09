"""势力 / 国战（全局跨群）。"""

from __future__ import annotations

from typing import Any, Dict

from ..core import storage

from . import player as player_mod

FACTIONS = {
    "wei": {"name": "魏", "color": "蓝", "desc": "挟天子以令诸侯，兵强马壮。"},
    "shu": {"name": "蜀", "color": "红", "desc": "汉室正统，仁义之师。"},
    "wu": {"name": "吴", "color": "绿", "desc": "据江东之地，水军无敌。"},
    "qun": {"name": "群", "color": "灰", "desc": "群雄并起，逐鹿中原。"},
}
_GLOBAL = "factions"


def _load() -> Dict[str, Any]:
    data = storage.load_global(_GLOBAL, None)
    if data is None:
        data = {"members": {f: [] for f in FACTIONS}, "war_points": {f: 0 for f in FACTIONS}}
        storage.save_global(_GLOBAL, data)
    for f in FACTIONS:
        data.setdefault("members", {}).setdefault(f, [])
        data.setdefault("war_points", {}).setdefault(f, 0)
    return data


def join(player: Dict[str, Any], faction: str) -> Dict[str, Any]:
    if faction not in FACTIONS:
        return {"ok": False, "reason": "bad_faction"}
    if player.get("faction"):
        return {"ok": False, "reason": "already", "faction": player["faction"]}
    data = _load()
    members = data["members"][faction]
    if str(player["qq"]) not in members:
        members.append(str(player["qq"]))
    player["faction"] = faction
    player.setdefault("faction_contrib", 0)
    player_mod.save(player)
    storage.save_global(_GLOBAL, data)
    return {"ok": True, "faction": faction, "name": FACTIONS[faction]["name"]}


def donate(player: Dict[str, Any], gold: int) -> Dict[str, Any]:
    if not player.get("faction"):
        return {"ok": False, "reason": "no_faction"}
    gold = max(1, int(gold))
    if int(player.get("gold", 0)) < gold:
        return {"ok": False, "reason": "gold", "have": player.get("gold", 0)}
    player_mod.add_gold(player, -gold)
    contrib = max(1, gold // 100)
    player["faction_contrib"] = int(player.get("faction_contrib", 0)) + contrib
    player.setdefault("wallet", {})
    player["wallet"]["merit"] = int(player["wallet"].get("merit", 0)) + contrib
    player_mod.save(player)
    data = _load()
    data["war_points"][player["faction"]] = data["war_points"].get(player["faction"], 0) + contrib
    storage.save_global(_GLOBAL, data)
    return {"ok": True, "contrib": contrib, "merit": contrib, "total": player["faction_contrib"]}


def info(player: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    result = {"faction": player.get("faction"), "contrib": int(player.get("faction_contrib", 0)),
              "list": []}
    for f, meta in FACTIONS.items():
        members = data["members"].get(f, [])
        power = 0
        for qq in members:
            p = storage.load_player(qq)
            if p:
                power += player_mod.total_power(p)
        result["list"].append({
            "id": f, "name": meta["name"], "members": len(members),
            "power": power, "war_points": data["war_points"].get(f, 0),
        })
    result["list"].sort(key=lambda x: x["war_points"], reverse=True)
    return result
