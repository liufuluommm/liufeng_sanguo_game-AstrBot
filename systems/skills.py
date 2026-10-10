"""技能系统运行时：技能书、碎片兑换、技能变更。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import inventory, player as player_mod, skillgen
from .tables import tables

BOOK_PREFIX = "skillbook_"
COST = {
    "active": {"generic": 20, "exclusive": 60, "custom": 40},
    "passive": {"generic": 15, "exclusive": 40, "custom": 30},
}
_OPTS = {"enable": True, "default_book_cost": 40, "learn_return_book": False, "learn_reset_level": True}


def set_options(**kwargs) -> None:
    _OPTS.update({k: v for k, v in kwargs.items() if k in _OPTS})


def enabled() -> bool:
    return bool(_OPTS.get("enable", True))


def book_id(name: str) -> str:
    return BOOK_PREFIX + name


def is_book(item_id: str) -> bool:
    return isinstance(item_id, str) and item_id.startswith(BOOK_PREFIX)


def book_name(item_id: str) -> str:
    return item_id[len(BOOK_PREFIX):]


def book_cost(name: str, skill_type: str = "active", rarity: str = "generic") -> int:
    cdef = skillgen.custom_def(name)
    if cdef and cdef.get("book_cost"):
        return int(cdef["book_cost"])
    if rarity == "custom":
        return int(_OPTS.get("default_book_cost", 40))
    table = COST.get(skill_type, COST["active"])
    return int(table.get(rarity, table.get("generic", 20)))


def distinct_skills() -> List[Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    # 内置 30 技能
    for name, s in skillgen.builtin_skills().items():
        out[name] = {"name": name, "type": s.get("type", "active"),
                     "rarity": "builtin", "book_cost": s.get("book_cost", 40), "source": "builtin"}
    # 每将技能名（740）合并入池
    for _sid, sk in tables().skills.items():
        name = sk.get("name")
        if not name:
            continue
        e = out.setdefault(name, {"name": name, "type": sk.get("type", "active"),
                                  "rarity": sk.get("rarity", "generic"), "source": "builtin"})
        if sk.get("rarity") == "exclusive":
            e["rarity"] = "exclusive"
    # 管理员自定义
    for name, cdef in skillgen.custom_skills().items():
        out[name] = {"name": name, "type": cdef.get("type", "active"),
                     "rarity": "custom", "book_cost": cdef.get("book_cost"),
                     "source": "custom"}
    result = []
    for e in out.values():
        e["category"] = skillgen.classify(e["name"], e["type"])
        e["cost"] = book_cost(e["name"], e["type"], e["rarity"])
        result.append(e)
    result.sort(key=lambda x: (x["type"], x["cost"], x["name"]))
    return result


def find(name: str) -> Optional[Dict[str, Any]]:
    for e in distinct_skills():
        if e["name"] == name or e["name"].startswith(name):
            return e
    return None


def exchange(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    e = find(name)
    if not e:
        return {"ok": False, "reason": "no_skill"}
    cost = int(e["cost"])
    wallet = player.setdefault("wallet", {})
    if int(wallet.get("skill_frag", 0)) < cost:
        return {"ok": False, "reason": "frag", "need": cost, "have": wallet.get("skill_frag", 0)}
    wallet["skill_frag"] = int(wallet.get("skill_frag", 0)) - cost
    inventory.add_item(player, book_id(e["name"]), 1)
    player_mod.save(player)
    return {"ok": True, "name": e["name"], "cost": cost,
            "frag_left": wallet["skill_frag"]}


def learn(player: Dict[str, Any], general: str, name: str) -> Dict[str, Any]:
    if not player_mod.has_general(player, general):
        return {"ok": False, "reason": "not_owned"}
    e = find(name)
    if not e:
        return {"ok": False, "reason": "no_skill"}
    skill_name = e["name"]
    if inventory.count_of(player, book_id(skill_name)) < 1:
        return {"ok": False, "reason": "no_book", "need": skill_name}
    is_custom = general in player.get("custom_generals", {})
    entry = player["custom_generals"][general] if is_custom else player["generals"][general]
    slots = entry.setdefault("skills", {})
    lvs = entry.setdefault("skill_lvs", {"1": 1, "passive": 1})
    if e["type"] == "passive":
        slot = "passive"
    else:
        slot = next((s for s in ("1", "2", "3") if not slots.get(s)), "1")
    old = slots.get(slot) or ""
    inventory.remove_item(player, book_id(skill_name), 1)
    slots[slot] = skill_name
    lvs[slot] = 1
    if slot == "1":
        entry["skill_lv"] = 1
    returned = False
    if old and _OPTS.get("learn_return_book", False):
        inventory.add_item(player, book_id(old), 1)
        returned = True
    player_mod.save(player)
    return {"ok": True, "general": general, "slot": slot, "skill": skill_name,
            "old": old, "type": e["type"], "returned": returned}
