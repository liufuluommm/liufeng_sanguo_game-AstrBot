"""管理台「装备管理」：装备蓝图（定义）CRUD + 玩家装备发放/移除/强化/卸下。

- 蓝图：内置 `tables/equipments.json` 只读；自定义写入数据目录 `equipments_custom.json`，
  由 `tables.Tables` 合并加载（热重载）。
- 玩家装备：对指定玩家发放/移除/强化（改等级）/卸下。
"""

from __future__ import annotations

import json
import os
import time
import random
from typing import Any, Dict, List, Optional

from ..core import storage
from .tables import reload_tables, tables

SLOTS = ("weapon", "armor", "mount", "treasure")
RARITIES = ("ssr", "sr", "r", "n")
SLOT_LABEL = {"weapon": "武器", "armor": "防具", "mount": "坐骑", "treasure": "宝物"}


def _path():
    return storage.data_root() / "equipments_custom.json"


def load_custom() -> Dict[str, Dict]:
    p = _path()
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: Dict[str, Any]) -> None:
    p = _path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _clamp(v: Any, low: int = 0, high: int = 9999, default: int = 0) -> int:
    try:
        return max(low, min(high, int(v)))
    except (TypeError, ValueError):
        return default


def normalize_def(d: Dict[str, Any]) -> Dict[str, Any]:
    slot = d.get("slot", "weapon")
    rarity = d.get("rarity", "n")
    return {
        "id": str(d.get("id", "")).strip(),
        "name": str(d.get("name", "")).strip(),
        "slot": slot if slot in SLOTS else "weapon",
        "rarity": rarity if rarity in RARITIES else "n",
        "force": _clamp(d.get("force", 0)),
        "intellect": _clamp(d.get("intellect", 0)),
        "lead": _clamp(d.get("lead", 0)),
        "source": "custom",
    }


def validate_def(d: Dict[str, Any]) -> Dict[str, Any]:
    did = str(d.get("id", "")).strip()
    name = str(d.get("name", "")).strip()
    if not did or not name:
        return {"ok": False, "reason": "no_id_name"}
    if len(name) > 16:
        return {"ok": False, "reason": "name_too_long"}
    if tables().equipment(did) is not None and did not in load_custom():
        return {"ok": False, "reason": "builtin_locked"}
    return {"ok": True}


def list_defs() -> List[Dict[str, Any]]:
    custom = load_custom()
    out: List[Dict[str, Any]] = []
    for slot, items in (tables().equipments or {}).items():
        for it in items:
            row = dict(it)
            row["source"] = "custom" if it["id"] in custom else "builtin"
            out.append(row)
    return out


def save_custom_def(d: Dict[str, Any]) -> Dict[str, Any]:
    check = validate_def(d)
    if not check["ok"]:
        return check
    norm = normalize_def(d)
    norm.pop("source", None)
    data = load_custom()
    data[norm["id"]] = norm
    _write(data)
    reload_tables()
    return {"ok": True, "id": norm["id"]}


def delete_custom_def(def_id: str) -> Dict[str, Any]:
    data = load_custom()
    if def_id not in data:
        return {"ok": False, "reason": "not_found"}
    data.pop(def_id, None)
    _write(data)
    reload_tables()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 玩家装备
# ---------------------------------------------------------------------------
def _new_uid() -> str:
    return f"eq{int(time.time() * 1000) % 10_000_000}{random.randint(100, 999)}"


def list_player(qq: str) -> List[Dict[str, Any]]:
    player = _load_player(qq)
    if not player:
        return []
    rows = []
    for i, item in enumerate(player.get("equipments", [])):
        eq = tables().equipment(item["id"]) or {}
        rows.append({
            "index": i, "uid": item.get("uid", ""), "id": item["id"],
            "name": eq.get("name", item["id"]),
            "slot": eq.get("slot", "weapon"),
            "rarity": eq.get("rarity", "n"),
            "level": int(item.get("level", 1)),
            "equipped_by": item.get("equipped_by"),
        })
    return rows


def _load_player(qq: str):
    from . import player as player_mod
    return player_mod.load(qq)


def _save_player(player) -> None:
    from . import player as player_mod
    player_mod.save(player)


def give(qq: str, def_id: str, level: int = 1) -> Dict[str, Any]:
    if tables().equipment(def_id) is None:
        return {"ok": False, "reason": "def_not_found"}
    player = _load_player(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    item = {"uid": _new_uid(), "id": def_id, "level": max(1, int(level)), "equipped_by": None}
    player.setdefault("equipments", []).append(item)
    _save_player(player)
    return {"ok": True, "uid": item["uid"]}


def _find_index(player, uid: str) -> int:
    for i, item in enumerate(player.get("equipments", [])):
        if item.get("uid") == uid:
            return i
    return -1


def remove(qq: str, uid: str) -> Dict[str, Any]:
    player = _load_player(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    idx = _find_index(player, uid)
    if idx < 0:
        return {"ok": False, "reason": "not_found"}
    item = player["equipments"].pop(idx)
    worn = item.get("equipped_by")
    if worn:
        entry = (player.get("custom_generals", {}).get(worn)
                 or player.get("generals", {}).get(worn))
        if entry:
            for slot, e in list((entry.get("equip") or {}).items()):
                if e.get("uid") == uid:
                    entry["equip"].pop(slot, None)
    _save_player(player)
    return {"ok": True}


def set_level(qq: str, uid: str, level: int) -> Dict[str, Any]:
    player = _load_player(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    idx = _find_index(player, uid)
    if idx < 0:
        return {"ok": False, "reason": "not_found"}
    item = player["equipments"][idx]
    item["level"] = max(1, int(level))
    # 同步已穿戴武将记录
    worn = item.get("equipped_by")
    if worn:
        entry = (player.get("custom_generals", {}).get(worn)
                 or player.get("generals", {}).get(worn))
        if entry:
            eq = tables().equipment(item["id"]) or {}
            from .equipment import equipment_power
            for slot, e in (entry.get("equip") or {}).items():
                if e.get("uid") == uid:
                    e["level"] = item["level"]
                    e["power"] = equipment_power(eq, item["level"])
    _save_player(player)
    return {"ok": True, "level": item["level"]}


def enhance(qq: str, uid: str, delta: int = 1) -> Dict[str, Any]:
    player = _load_player(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    idx = _find_index(player, uid)
    if idx < 0:
        return {"ok": False, "reason": "not_found"}
    return set_level(qq, uid, int(player["equipments"][idx].get("level", 1)) + int(delta))


def unequip(qq: str, general: str, slot: str) -> Dict[str, Any]:
    from . import equipment as equip_sys
    player = _load_player(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    res = equip_sys.unequip(player, general, slot)
    return res
