"""管理员自定义技能：增删改、热重载，并自动生成对应技能书道具。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from ..core import storage
from . import items as items_mod
from . import skillgen

VALID_TYPES = ("active", "passive", "command", "assault", "formation")
VALID_CATEGORIES = ("damage", "control", "buff", "debuff", "heal", "special")
VALID_TARGETS = ("self", "ally_single", "ally_all", "lowest_hp_ally",
                 "enemy_single", "enemy_all", "lowest_hp_enemy", "random_enemy")
VALID_TRIGGERS = ("attack", "when_attacked", "round_start", "on_kill", "hp_below", "always")


def _path():
    return storage.data_root() / "skills_custom.json"


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


def normalize(skill: Dict[str, Any]) -> Dict[str, Any]:
    name = str(skill.get("name", "")).strip()
    stype = skill.get("type", "active")
    cat = skill.get("category", "damage")
    return {
        "id": name,
        "name": name,
        "type": stype if stype in VALID_TYPES else "active",
        "category": cat if cat in VALID_CATEGORIES else "damage",
        "target": skill.get("target", "enemy_single") if skill.get("target") in VALID_TARGETS else "enemy_single",
        "trigger": skill.get("trigger", "attack") if skill.get("trigger") in VALID_TRIGGERS else "attack",
        "chance": float(skill.get("chance", 0.35)),
        "cooldown": int(skill.get("cooldown", 0)),
        "scale": skill.get("scale", {"attr": "force"}),
        "formula": skill.get("formula", {}),
        "effects": skill.get("effects", []) or [],
        "desc": str(skill.get("desc", "")),
        "book_cost": int(skill.get("book_cost", 40)),
        "rarity": "custom",
    }


def validate(skill: Dict[str, Any]) -> Dict[str, Any]:
    name = str(skill.get("name", "")).strip()
    if not name:
        return {"ok": False, "reason": "no_name"}
    if len(name) > 12:
        return {"ok": False, "reason": "name_too_long"}
    if not skill.get("effects"):
        return {"ok": False, "reason": "no_effects"}
    return {"ok": True}


def _make_book_item(skill: Dict[str, Any]) -> None:
    name = skill["name"]
    items_mod.save_custom_item({
        "id": f"skillbook_{name}",
        "name": f"{name}·技能书",
        "category": "skillbook",
        "rarity": "custom",
        "desc": f"用于学习技能【{name}】。",
        "usable": False,
        "target": "general",
        "price": {"currency": "skill_frag", "amount": int(skill.get("book_cost", 40))},
        "shops": ["event"],
        "effects": [{"type": "learn_skill", "params": {"skill": name}}],
    })


def save_custom_skill(skill: Dict[str, Any]) -> Dict[str, Any]:
    check = validate(skill)
    if not check["ok"]:
        return check
    norm = normalize(skill)
    data = load_custom()
    data[norm["name"]] = norm
    _write(data)
    skillgen.reload()
    _make_book_item(norm)
    return {"ok": True, "name": norm["name"]}


def delete_custom_skill(name: str) -> Dict[str, Any]:
    data = load_custom()
    if name not in data:
        return {"ok": False, "reason": "not_found"}
    data.pop(name, None)
    _write(data)
    skillgen.reload()
    items_mod.delete_custom_item(f"skillbook_{name}")
    return {"ok": True}


def list_custom() -> List[Dict[str, Any]]:
    return list(load_custom().values())
