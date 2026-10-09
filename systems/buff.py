"""限时增益 buff。"""

from __future__ import annotations

import time
from typing import Any, Dict, List

BUFF_NAME = {
    "double_gold": "金币双倍",
    "double_drop": "掉落双倍",
    "atk": "攻击加成",
    "def": "防御加成",
    "hp": "生命加成",
    "free_stamina": "免行动力",
}


def add_buff(player: Dict[str, Any], buff_type: str, value: float, duration: int) -> Dict[str, Any]:
    now = int(time.time())
    expire = now + int(duration)
    buffs: List[Dict[str, Any]] = player.setdefault("buffs", [])
    for b in buffs:
        if b.get("type") == buff_type:
            b["value"] = float(value)
            b["expire"] = max(int(b.get("expire", 0)), expire)
            return {"ok": True, "type": buff_type, "expire": b["expire"], "merged": True}
    buffs.append({"type": buff_type, "value": float(value), "expire": expire})
    return {"ok": True, "type": buff_type, "expire": expire, "merged": False}


def prune(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    now = int(time.time())
    buffs = [b for b in player.get("buffs", []) if int(b.get("expire", 0)) > now]
    player["buffs"] = buffs
    return buffs


def active(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    return prune(player)


def value(player: Dict[str, Any], buff_type: str, default: float = 0.0) -> float:
    for b in prune(player):
        if b.get("type") == buff_type:
            return float(b.get("value", default))
    return default


def has(player: Dict[str, Any], buff_type: str) -> bool:
    return value(player, buff_type, 0.0) > 0
