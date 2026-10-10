"""管理员自定义兵种 / 兵种效果：增删改与热重载（存于插件数据目录）。

- 内置兵种（`tables/troops.json`）**不可修改**，自定义兵种禁止与内置 id 冲突。
- 自定义兵种存 `troops_custom.json`；自定义兵种效果存 `troop_effects_custom.json`。
"""

from __future__ import annotations

import json
import os
import zlib
from typing import Any, Dict, List

from ..core import storage
from . import troops as troops_mod
from .troops import MECHANIC_KEYS, STAT_ATTRS, TIERS

_ITEM_TYPES = ("stat", "mechanic", "opening")


def _custom_troops_path():
    return storage.data_root() / "troops_custom.json"


def _custom_effects_path():
    return storage.data_root() / "troop_effects_custom.json"


def _read(path, default):
    if not path.exists():
        return default
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else default
    except (json.JSONDecodeError, OSError):
        return default


def _write(path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _slug(name: str) -> str:
    return "tce_" + format(zlib.crc32(name.encode("utf-8")) % 0xFFFFFF, "06x")


# ---------------------------------------------------------------------------
# 兵种
# ---------------------------------------------------------------------------
def load_custom_troops() -> Dict[str, Dict]:
    return _read(_custom_troops_path(), {})


def _norm_item(item: Dict[str, Any]) -> Dict[str, Any]:
    it = item.get("type")
    if it == "stat":
        attr = item.get("attr")
        return {"type": "stat",
                "attr": attr if attr in STAT_ATTRS else "def",
                "value": _num(item.get("value"), 0.1)}
    if it == "mechanic":
        key = item.get("key")
        return {"type": "mechanic",
                "key": key if key in MECHANIC_KEYS else "first_strike",
                "value": _num(item.get("value"), 1)}
    if it == "opening" and isinstance(item.get("atom"), dict):
        return {"type": "opening", "atom": item["atom"]}
    return {}


def _num(v: Any, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def normalize_troop(troop: Dict[str, Any]) -> Dict[str, Any]:
    name = str(troop.get("name", "")).strip()
    tid = str(troop.get("id") or name).strip()
    tier = troop.get("tier", "basic")
    effects = []
    for eff in troop.get("effects") or []:
        if not isinstance(eff, dict):
            continue
        items = []
        for item in eff.get("items") or []:
            if isinstance(item, dict):
                n = _norm_item(item)
                if n:
                    items.append(n)
        if items:
            effects.append({"name": str(eff.get("name", "")).strip() or "效果", "items": items})
    return {
        "id": tid,
        "name": name or tid,
        "tier": tier if tier in TIERS else "basic",
        "desc": str(troop.get("desc", "")),
        "counter": [str(c) for c in (troop.get("counter") or []) if str(c).strip()],
        "effects": effects,
        "source": "custom",
    }


def validate_troop(troop: Dict[str, Any]) -> Dict[str, Any]:
    name = str(troop.get("name", "")).strip()
    tid = str(troop.get("id") or name).strip()
    if not name:
        return {"ok": False, "reason": "no_name"}
    if len(name) > 12:
        return {"ok": False, "reason": "name_too_long"}
    if troops_mod.is_builtin(tid):
        return {"ok": False, "reason": "builtin_locked"}
    return {"ok": True}


def save_custom_troop(troop: Dict[str, Any]) -> Dict[str, Any]:
    check = validate_troop(troop)
    if not check["ok"]:
        return check
    norm = normalize_troop(troop)
    data = load_custom_troops()
    data[norm["id"]] = norm
    _write(_custom_troops_path(), data)
    troops_mod.reload()
    return {"ok": True, "id": norm["id"], "name": norm["name"]}


def delete_custom_troop(troop_id: str) -> Dict[str, Any]:
    data = load_custom_troops()
    if troop_id not in data:
        return {"ok": False, "reason": "not_found"}
    data.pop(troop_id, None)
    _write(_custom_troops_path(), data)
    troops_mod.reload()
    return {"ok": True}


def list_custom_troops() -> List[Dict[str, Any]]:
    return list(load_custom_troops().values())


# ---------------------------------------------------------------------------
# 兵种效果
# ---------------------------------------------------------------------------
def load_custom_effects() -> Dict[str, Dict]:
    return _read(_custom_effects_path(), {})


def normalize_effect(eff: Dict[str, Any]) -> Dict[str, Any]:
    name = str(eff.get("name", "")).strip()
    items = []
    tags = set()
    for item in eff.get("items") or []:
        if isinstance(item, dict):
            n = _norm_item(item)
            if n:
                items.append(n)
                tags.add(n["type"])
    eid = str(eff.get("id") or "").strip() or _slug(name or "effect")
    return {
        "id": eid,
        "name": name,
        "desc": str(eff.get("desc", "")),
        "tags": sorted(tags),
        "items": items,
        "source": "custom",
    }


def validate_effect(eff: Dict[str, Any]) -> Dict[str, Any]:
    name = str(eff.get("name", "")).strip()
    if not name:
        return {"ok": False, "reason": "no_name"}
    if len(name) > 12:
        return {"ok": False, "reason": "name_too_long"}
    if not [i for i in (eff.get("items") or []) if isinstance(i, dict)]:
        return {"ok": False, "reason": "no_items"}
    return {"ok": True}


def save_custom_effect(eff: Dict[str, Any]) -> Dict[str, Any]:
    check = validate_effect(eff)
    if not check["ok"]:
        return check
    norm = normalize_effect(eff)
    data = load_custom_effects()
    data[norm["id"]] = norm
    _write(_custom_effects_path(), data)
    troops_mod.reload()
    return {"ok": True, "id": norm["id"], "name": norm["name"]}


def delete_custom_effect(effect_id: str) -> Dict[str, Any]:
    data = load_custom_effects()
    if effect_id not in data:
        return {"ok": False, "reason": "not_found"}
    data.pop(effect_id, None)
    _write(_custom_effects_path(), data)
    troops_mod.reload()
    return {"ok": True}


def list_custom_effects() -> List[Dict[str, Any]]:
    return list(load_custom_effects().values())
