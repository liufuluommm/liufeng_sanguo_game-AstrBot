"""玩家背包。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import items as items_mod
from . import player as player_mod


def count_of(player: Dict[str, Any], item_id: str) -> int:
    return int(player.get("inventory", {}).get(item_id, 0))


def add_item(player: Dict[str, Any], item_id: str, count: int = 1) -> None:
    inv = player.setdefault("inventory", {})
    inv[item_id] = int(inv.get(item_id, 0)) + int(count)


def remove_item(player: Dict[str, Any], item_id: str, count: int = 1) -> bool:
    inv = player.setdefault("inventory", {})
    if int(inv.get(item_id, 0)) < count:
        return False
    inv[item_id] = int(inv.get(item_id, 0)) - count
    if inv[item_id] <= 0:
        inv.pop(item_id, None)
    return True


def list_items(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for item_id, count in player.get("inventory", {}).items():
        item = items_mod.get_item(item_id)
        if item:
            result.append({"item": item, "count": int(count)})
    return result


def use_item(player: Dict[str, Any], item_id: str,
             target: Optional[str] = None) -> Dict[str, Any]:
    item = items_mod.get_item(item_id)
    if item is None:
        return {"ok": False, "reason": "no_item"}
    if not item.get("usable", True):
        return {"ok": False, "reason": "unusable"}
    if count_of(player, item_id) < 1:
        return {"ok": False, "reason": "none_owned"}
    if item.get("target") == "general" and not target:
        return {"ok": False, "reason": "need_target"}
    remove_item(player, item_id, 1)
    res = items_mod.execute_item(player, item, target)
    if res.get("pending"):
        player["pending_choice"] = res["pending"]
        player_mod.save(player)
    return {"ok": True, "item": item, "logs": res["logs"], "pending": res.get("pending")}
