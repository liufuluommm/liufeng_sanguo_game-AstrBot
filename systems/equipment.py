"""装备系统：锻造 / 强化 / 穿戴 / 卸下。"""

from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional

from ..core.utils import base_power, weighted_choice

from . import player as player_mod
from .tables import tables

SLOTS = ["weapon", "armor", "mount", "treasure"]
SLOT_LABEL = {"weapon": "武器", "armor": "防具", "mount": "坐骑", "treasure": "宝物"}

FORGE_COST = 800
ENHANCE_BASE = 300


def equipment_stats(eq_def: Dict[str, Any], level: int = 1) -> Dict[str, int]:
    mult = 1.0 + 0.2 * (max(1, level) - 1)
    return {
        "force": int(eq_def.get("force", 0) * mult),
        "intellect": int(eq_def.get("intellect", 0) * mult),
        "lead": int(eq_def.get("lead", 0) * mult),
    }


def equipment_power(eq_def: Dict[str, Any], level: int = 1) -> int:
    return base_power(equipment_stats(eq_def, level))


def _new_uid() -> str:
    return f"eq{int(time.time() * 1000) % 10_000_000}{random.randint(100, 999)}"


def forge(player: Dict[str, Any], rates: Optional[Dict[str, float]] = None,
          cost: int = FORGE_COST, rng: random.Random = random) -> Dict[str, Any]:
    if int(player.get("gold", 0)) < cost:
        return {"ok": False, "reason": "gold", "need": cost, "gold": player.get("gold", 0)}
    rates = rates or {"ssr": 0.05, "sr": 0.20, "r": 0.35, "n": 0.40}
    rarity = weighted_choice(["ssr", "sr", "r", "n"], [rates.get(k, 0) for k in ("ssr", "sr", "r", "n")])
    pool = tables().equipment_by_rarity(rarity) or tables().all_equipment()
    eq = rng.choice(pool)
    player_mod.add_gold(player, -cost)
    item = {"uid": _new_uid(), "id": eq["id"], "level": 1, "equipped_by": None}
    player.setdefault("equipments", []).append(item)
    player_mod.save(player)
    return {"ok": True, "equipment": eq, "item": item, "cost": cost,
            "gold_left": player["gold"], "rarity": rarity}


def enhance(player: Dict[str, Any], index: int) -> Dict[str, Any]:
    equipments: List[Dict] = player.get("equipments", [])
    if not (0 <= index < len(equipments)):
        return {"ok": False, "reason": "not_found"}
    item = equipments[index]
    level = int(item.get("level", 1))
    cost = ENHANCE_BASE * level
    if int(player.get("gold", 0)) < cost:
        return {"ok": False, "reason": "gold", "need": cost, "gold": player.get("gold", 0)}
    player_mod.add_gold(player, -cost)
    item["level"] = level + 1
    player_mod.save(player)
    eq = tables().equipment(item["id"]) or {}
    return {"ok": True, "name": eq.get("name", "?"), "level": item["level"],
            "cost": cost, "gold_left": player["gold"]}


def equip(player: Dict[str, Any], index: int, general: str) -> Dict[str, Any]:
    equipments: List[Dict] = player.get("equipments", [])
    if not (0 <= index < len(equipments)):
        return {"ok": False, "reason": "not_found"}
    if not player_mod.has_general(player, general):
        return {"ok": False, "reason": "not_owned"}
    item = equipments[index]
    worn_by = item.get("equipped_by")
    if worn_by and worn_by != general:
        return {"ok": False, "reason": "in_use", "by": worn_by}
    eq = tables().equipment(item["id"]) or {}
    slot = eq.get("slot", "weapon")
    entry = _entry(player, general)
    if entry is None:
        return {"ok": False, "reason": "not_owned"}
    entry.setdefault("equip", {})
    old = entry["equip"].get(slot)
    if old and old.get("uid") != item["uid"]:
        for other in equipments:
            if other.get("uid") == old.get("uid"):
                other["equipped_by"] = None
    entry["equip"][slot] = {
        "uid": item["uid"],
        "id": item["id"],
        "level": item.get("level", 1),
        "power": equipment_power(eq, item.get("level", 1)),
    }
    item["equipped_by"] = general
    player_mod.save(player)
    return {"ok": True, "slot": slot, "general": general, "name": eq.get("name")}


def unequip(player: Dict[str, Any], general: str, slot: str) -> Dict[str, Any]:
    entry = _entry(player, general)
    if entry is None:
        return {"ok": False, "reason": "not_owned"}
    equip = entry.get("equip", {})
    if slot not in equip:
        return {"ok": False, "reason": "empty"}
    removed = equip.pop(slot)
    for item in player.get("equipments", []):
        if item.get("uid") == removed.get("uid"):
            item["equipped_by"] = None
    player_mod.save(player)
    return {"ok": True, "name": removed.get("id")}


def _entry(player: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    if name in player.get("custom_generals", {}):
        return player["custom_generals"][name]
    return player.get("generals", {}).get(name)


def list_equipment(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for i, item in enumerate(player.get("equipments", [])):
        eq = tables().equipment(item["id"]) or {}
        result.append({
            "index": i,
            "name": eq.get("name", "?"),
            "slot": SLOT_LABEL.get(eq.get("slot", ""), ""),
            "rarity": eq.get("rarity", "n"),
            "level": item.get("level", 1),
            "equipped_by": item.get("equipped_by"),
            "power": equipment_power(eq, item.get("level", 1)),
        })
    return result
