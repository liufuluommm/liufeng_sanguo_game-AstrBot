"""管理员自定义武将：增删改与热重载（存于插件数据目录）。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from ..core import storage
from ..core.utils import ATTR_KEYS
from .tables import RARITIES, reload_tables


def _path():
    return storage.data_root() / "generals_custom.json"


def load_custom() -> Dict[str, Dict]:
    path = _path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: Dict[str, Any]) -> None:
    path = _path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _clamp(v: Any, low: int = 1, high: int = 200) -> int:
    try:
        return max(low, min(high, int(v)))
    except (TypeError, ValueError):
        return low


def normalize(general: Dict[str, Any]) -> Dict[str, Any]:
    name = str(general.get("name", "")).strip()
    rarity = general.get("rarity", "n")
    faction = general.get("faction", "custom")
    troop = general.get("troop", "infantry")
    out: Dict[str, Any] = {
        "id": name,
        "name": name,
        "title": str(general.get("title", "")).strip(),
        "rarity": rarity if rarity in RARITIES else "n",
        "faction": faction if faction in ("wei", "shu", "wu", "qun", "custom") else "custom",
        "troop": troop if troop in ("cavalry", "infantry", "archer", "spear") else "infantry",
        "category": "custom",
        "desc": str(general.get("desc", "")),
        "skill": {
            "active": str((general.get("skill") or {}).get("active", "")) or f"sk_act_{name}",
            "passive": str((general.get("skill") or {}).get("passive", "")) or f"sk_pas_{name}",
        },
    }
    for key in ATTR_KEYS:
        out[key] = _clamp(general.get(key, 50))
    return out


def validate(general: Dict[str, Any]) -> Dict[str, Any]:
    name = str(general.get("name", "")).strip()
    if not name:
        return {"ok": False, "reason": "no_name"}
    if len(name) > 12:
        return {"ok": False, "reason": "name_too_long"}
    return {"ok": True}


def save_custom_general(general: Dict[str, Any]) -> Dict[str, Any]:
    check = validate(general)
    if not check["ok"]:
        return check
    data = load_custom()
    data[str(general["name"]).strip()] = normalize(general)
    _write(data)
    reload_tables()
    return {"ok": True, "name": str(general["name"]).strip()}


def delete_custom_general(name: str) -> Dict[str, Any]:
    data = load_custom()
    if name not in data:
        return {"ok": False, "reason": "not_found"}
    data.pop(name, None)
    _write(data)
    reload_tables()
    return {"ok": True}


def list_custom() -> List[Dict[str, Any]]:
    return list(load_custom().values())
