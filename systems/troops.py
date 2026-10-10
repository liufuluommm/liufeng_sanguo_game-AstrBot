"""兵种与「携带兵种效果」数据载入、查询与运行时合并。

- 内置兵种：`tables/troops.json`（只读，不可修改）
- 自定义兵种：数据目录 `troops_custom.json`（管理员后台新建）
- 内置兵种效果库：`tables/troop_effects.json`（100 个）
- 自定义兵种效果：数据目录 `troop_effects_custom.json`

兵种「附带效果」由三类原子组成（见 `troop_effect_schema.json`）：
  stat / mechanic / opening
`merge(troop)` 把某兵种的全部效果合并为运行时结构 `{bonus, opening, mechanics}`。
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import storage
from .tables import TABLES_DIR

TIERS = ("basic", "elite", "special")
TIER_LABEL = {"basic": "基础兵种", "elite": "精锐兵种", "special": "特殊兵种"}
STAT_ATTRS = ["atk", "def", "mag_def", "hp", "speed", "crit", "crit_dmg", "dodge",
              "lifesteal", "spellvamp", "reduction", "tenacity", "reflect",
              "cdr", "atkspeed", "pen_flat", "mana"]
MECHANIC_KEYS = ["magic_vuln", "extra_hit_chance", "knockup_chance", "first_strike", "low_hp_atk"]
DEFAULT_ID = "infantry"
TIER_RANDOM_POOL = {"basic": 4}

_BUILTIN: Dict[str, Dict] = {}
_CUSTOM: Dict[str, Dict] = {}
_EFFECTS: List[Dict] = []
_EFFECTS_CUSTOM: Dict[str, Dict] = {}
_LOADED = False


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _tables_path(name: str) -> Path:
    return Path(TABLES_DIR) / name


def _custom_path(name: str) -> Path:
    try:
        return storage.data_root() / name
    except Exception:  # noqa: BLE001
        return Path(name)


def _normalize_troop(troop: Dict[str, Any]) -> Dict[str, Any]:
    tid = str(troop.get("id") or troop.get("name") or "").strip()
    tier = troop.get("tier", "basic")
    effects = troop.get("effects") or []
    out = {
        "id": tid,
        "name": str(troop.get("name") or tid),
        "tier": tier if tier in TIERS else "basic",
        "desc": str(troop.get("desc", "")),
        "counter": [str(c) for c in (troop.get("counter") or [])],
        "effects": [e for e in effects if isinstance(e, dict)],
        "source": troop.get("source", "custom"),
    }
    return out


def _normalize_effect(eff: Dict[str, Any]) -> Dict[str, Any]:
    items = eff.get("items") or []
    return {
        "id": str(eff.get("id", "")),
        "name": str(eff.get("name", "")),
        "desc": str(eff.get("desc", "")),
        "tags": [str(t) for t in (eff.get("tags") or [])],
        "items": [i for i in items if isinstance(i, dict)],
        "source": eff.get("source", "builtin"),
    }


def _load() -> None:
    global _BUILTIN, _CUSTOM, _EFFECTS, _EFFECTS_CUSTOM, _LOADED
    builtin = _read_json(_tables_path("troops.json"), {})
    _BUILTIN = {}
    if isinstance(builtin, dict):
        for tid, t in builtin.items():
            if isinstance(t, dict):
                t = dict(t)
                t.setdefault("id", tid)
                t["source"] = "builtin"
                _BUILTIN[t["id"]] = _normalize_troop(t)

    custom = _read_json(_custom_path("troops_custom.json"), {})
    _CUSTOM = {}
    if isinstance(custom, dict):
        for tid, t in custom.items():
            if isinstance(t, dict):
                t = dict(t)
                t.setdefault("id", tid)
                t["source"] = "custom"
                _CUSTOM[t["id"]] = _normalize_troop(t)

    effects = _read_json(_tables_path("troop_effects.json"), [])
    _EFFECTS = []
    if isinstance(effects, list):
        for e in effects:
            if isinstance(e, dict):
                e = dict(e)
                e["source"] = "builtin"
                _EFFECTS.append(_normalize_effect(e))

    ceff = _read_json(_custom_path("troop_effects_custom.json"), {})
    _EFFECTS_CUSTOM = {}
    if isinstance(ceff, dict):
        for eid, e in ceff.items():
            if isinstance(e, dict):
                e = dict(e)
                e.setdefault("id", eid)
                e["source"] = "custom"
                _EFFECTS_CUSTOM[e["id"]] = _normalize_effect(e)

    _LOADED = True


def reload() -> None:
    _load()


def _ensure() -> None:
    if not _LOADED:
        _load()


# ---------------------------------------------------------------------------
# 兵种查询
# ---------------------------------------------------------------------------
def all_troops() -> List[Dict[str, Any]]:
    _ensure()
    return list(_BUILTIN.values()) + list(_CUSTOM.values())


def builtin_troops() -> List[Dict[str, Any]]:
    _ensure()
    return list(_BUILTIN.values())


def custom_troops() -> List[Dict[str, Any]]:
    _ensure()
    return list(_CUSTOM.values())


def get(troop_id: Optional[str]) -> Dict[str, Any]:
    _ensure()
    tid = troop_id or DEFAULT_ID
    return _BUILTIN.get(tid) or _CUSTOM.get(tid) or _BUILTIN.get(DEFAULT_ID) or {
        "id": DEFAULT_ID, "name": "步兵", "tier": "basic", "counter": [], "effects": []
    }


def id_exists(troop_id: str) -> bool:
    _ensure()
    return troop_id in _BUILTIN or troop_id in _CUSTOM


def is_builtin(troop_id: str) -> bool:
    _ensure()
    return troop_id in _BUILTIN


def name(troop_id: Optional[str]) -> str:
    return get(troop_id).get("name", troop_id or "")


def label(troop_id: Optional[str]) -> str:
    _ensure()
    if not troop_id:
        return ""
    t = _BUILTIN.get(troop_id) or _CUSTOM.get(troop_id)
    return t["name"] if t else ""


def all_ids() -> List[str]:
    _ensure()
    return list(_BUILTIN.keys()) + list(_CUSTOM.keys())


def tiers() -> List[Dict[str, str]]:
    return [{"key": t, "label": TIER_LABEL[t]} for t in TIERS]


def by_tier() -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {t: [] for t in TIERS}
    for t in all_troops():
        out.setdefault(t.get("tier", "basic"), []).append(t)
    return out


def basic_ids() -> List[str]:
    _ensure()
    ids = [t["id"] for t in _BUILTIN.values() if t.get("tier") == "basic"]
    return ids or [DEFAULT_ID]


def random_basic(rng: Optional[random.Random] = None) -> str:
    r = rng or random
    pool = basic_ids()
    return r.choice(pool) if pool else DEFAULT_ID


# ---------------------------------------------------------------------------
# 兵种效果库
# ---------------------------------------------------------------------------
def effect_library() -> List[Dict[str, Any]]:
    _ensure()
    return list(_EFFECTS) + list(_EFFECTS_CUSTOM.values())


def custom_effects() -> List[Dict[str, Any]]:
    _ensure()
    return list(_EFFECTS_CUSTOM.values())


def get_effect(effect_id: str) -> Optional[Dict[str, Any]]:
    _ensure()
    for e in _EFFECTS:
        if e["id"] == effect_id:
            return e
    return _EFFECTS_CUSTOM.get(effect_id)


# ---------------------------------------------------------------------------
# 运行时合并：把兵种携带效果合并为 {bonus, opening, mechanics}
# ---------------------------------------------------------------------------
def _effect_items(eff: Dict[str, Any]) -> List[Dict[str, Any]]:
    if eff.get("items"):
        return [i for i in eff["items"] if isinstance(i, dict)]
    ref = eff.get("ref")
    if ref:
        src = get_effect(ref)
        if src:
            return list(src.get("items") or [])
    return []


def merge(troop: Dict[str, Any]) -> Dict[str, Any]:
    bonus: Dict[str, float] = {a: 0.0 for a in STAT_ATTRS}
    opening: List[Dict[str, Any]] = []
    mechanics: Dict[str, float] = {}
    for eff in troop.get("effects") or []:
        for item in _effect_items(eff):
            it = item.get("type")
            if it == "stat":
                attr = item.get("attr")
                if attr in bonus:
                    try:
                        bonus[attr] += float(item.get("value", 0))
                    except (TypeError, ValueError):
                        pass
            elif it == "mechanic":
                key = item.get("key")
                if key in MECHANIC_KEYS:
                    try:
                        mechanics[key] = float(item.get("value", 0))
                    except (TypeError, ValueError):
                        pass
            elif it == "opening":
                atom = item.get("atom")
                if isinstance(atom, dict) and atom.get("type"):
                    opening.append(atom)
    return {"bonus": bonus, "opening": opening, "mechanics": mechanics}


_load()
