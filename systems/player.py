"""玩家数据模型与操作。"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..core import storage
from ..core.utils import general_power

from .tables import tables


def new_player(qq: str, name: str, initial_gold: int = 1000,
               dorm_capacity: int = 15) -> Dict[str, Any]:
    return {
        "qq": str(qq),
        "name": name,
        "gold": initial_gold,
        "diamonds": 0,
        "wallet": {
            "gold": initial_gold,
            "diamond": 0,
            "merit": 0,
            "soul": 0,
            "repute": 0,
            "event_ticket": 0,
            "challenge": 0,
            "skill_frag": 0,
        },
        "level": 1,
        "exp": 0,
        "sign_date": "",
        "sign_streak": 0,
        "fragments": 0,
        "generals": {},
        "custom_generals": {},
        "buildings": {"dormitory": {"level": 1, "capacity": dorm_capacity}},
        "team": [],
        "leader": "",
        "win": 0,
        "lose": 0,
        "stamina": 120,
        "stamina_ts": int(time.time()),
        "inventory": {},
        "buffs": [],
        "shop_state": {},
        "quests": {},
        "achievements": {},
        "pvp": {"rating": 1000, "season_win": 0, "season_lose": 0},
        "create_time": int(time.time()),
    }


def _migrate_entry_skills(entry: Dict[str, Any]) -> bool:
    """把旧的 skills={active,passive} 迁移为 {1,passive} 并补 skill_lvs。"""
    changed = False
    slots = entry.get("skills")
    if isinstance(slots, dict) and "active" in slots and "1" not in slots:
        slots["1"] = slots.pop("active")
        changed = True
    if "skill_lvs" not in entry:
        entry["skill_lvs"] = {"1": int(entry.get("skill_lv", 1)), "passive": 1}
        changed = True
    return changed


def _migrate(player: Dict[str, Any]) -> Dict[str, Any]:
    """旧档迁移：自定义武将补多维；武将/自定义武将技能槽迁移为多槽。"""
    changed = False
    for entry in player.get("custom_generals", {}).values():
        if "vitality" not in entry:
            entry["vitality"] = int(entry.get("lead", 60))
            changed = True
        for key in ("charisma", "eloquence", "speed"):
            if key not in entry:
                entry[key] = 60
                changed = True
        entry.setdefault("category", "custom")
        entry.setdefault("title", "")
        changed = _migrate_entry_skills(entry) or changed
    for entry in player.get("generals", {}).values():
        changed = _migrate_entry_skills(entry) or changed
    if changed:
        save(player)
    return player


def load(qq: str) -> Optional[Dict[str, Any]]:
    player = storage.load_player(str(qq))
    if player is not None:
        player = _migrate(player)
    return player


def save(player: Dict[str, Any]) -> None:
    # gold 与 wallet.gold 保持同步
    player.setdefault("wallet", {})
    player["wallet"]["gold"] = player.get("gold", 0)
    storage.save_player(str(player["qq"]), player)


def get_or_create(qq: str, name: str, initial_gold: int = 1000,
                  dorm_capacity: int = 15) -> Dict[str, Any]:
    player = load(qq)
    if player is None:
        player = new_player(qq, name, initial_gold, dorm_capacity)
        save(player)
    return player


def add_gold(player: Dict[str, Any], amount: int) -> None:
    player["gold"] = max(0, int(player.get("gold", 0)) + int(amount))


# ---------------------------------------------------------------------------
# 武将
# ---------------------------------------------------------------------------


DEFAULT_ACTIVE_NAME = "破阵"
DEFAULT_PASSIVE_NAME = "铁骨"


def _slot_to_name(value: Any) -> str:
    if not value:
        return ""
    if value in tables().skills:
        return tables().skills[value]["name"]
    sval = str(value)
    if sval.startswith("sk_"):
        return ""
    return sval


def _attach_skills(info: Dict[str, Any]) -> None:
    from . import skillgen

    slots = info.get("skills") or {}
    tbl = info.get("skill") or {}
    # 主动：王者式 1/2/3 槽（兼容旧的 active）
    active_names: List[str] = []
    for s in ("1", "2", "3"):
        nm = _slot_to_name(slots.get(s))
        if nm:
            active_names.append(nm)
    if not active_names:
        legacy = _slot_to_name(slots.get("active")) or _slot_to_name(tbl.get("active"))
        active_names = [legacy or DEFAULT_ACTIVE_NAME]
    passive_name = _slot_to_name(slots.get("passive")) or _slot_to_name(tbl.get("passive")) or DEFAULT_PASSIVE_NAME

    info["skill_slots"] = {
        "passive": [dict(skillgen.generate(passive_name, "passive"), name=passive_name, type="passive")],
        "active": [dict(skillgen.generate(n, "active"), name=n, type="active") for n in active_names],
    }
    info["skill_name"] = active_names[0]
    info["skill_active"] = info["skill_slots"]["active"][0]
    info["skill_passive"] = info["skill_slots"]["passive"][0]
    lvs = info.get("skill_lvs")
    if isinstance(lvs, dict) and lvs:
        info["skill_lv"] = int(lvs.get("1", 1))
    else:
        info["skill_lv"] = int(info.get("skill_lv", 1))
    info["skill_lvs"] = lvs if isinstance(lvs, dict) else {"1": info["skill_lv"], "passive": 1}


def general_info(player: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """合并静态表与玩家持有信息，返回完整武将 dict。"""
    data = tables().get(name)
    if data is None:
        custom = player.get("custom_generals", {}).get(name)
        if custom is None:
            return None
        info = dict(custom, id=name, name=name, category="custom", rarity="custom")
    else:
        owned = player.get("generals", {}).get(name)
        info = dict(data)
        if owned:
            info.update(owned)
    _attach_skills(info)
    return info


def owned_names(player: Dict[str, Any]) -> List[str]:
    names = list(player.get("generals", {}).keys())
    names += list(player.get("custom_generals", {}).keys())
    return names


def has_general(player: Dict[str, Any], name: str) -> bool:
    return name in player.get("generals", {}) or name in player.get("custom_generals", {})


def add_general(player: Dict[str, Any], name: str, level: int = 1, star: int = 1) -> bool:
    """添加武将；已存在则升星(上限)。返回是否为新增。"""
    if name in player.get("generals", {}):
        entry = player["generals"][name]
        entry["star"] = min(10, entry.get("star", 1) + 1)
        return False
    player.setdefault("generals", {})[name] = {
        "level": level,
        "star": star,
        "exp": 0,
        "skill_lv": 1,
        "talent": {},
        "equip": {},
    }
    return True


def add_custom_general(player: Dict[str, Any], data: Dict[str, Any]) -> None:
    name = data["name"]
    player.setdefault("custom_generals", {})[name] = data


def custom_capacity(player: Dict[str, Any]) -> int:
    return int(player.get("buildings", {}).get("dormitory", {}).get("capacity", 15))


def custom_count(player: Dict[str, Any]) -> int:
    return len(player.get("custom_generals", {}))


def general_power_of(player: Dict[str, Any], name: str) -> int:
    info = general_info(player, name)
    if not info:
        return 0
    return general_power(
        info,
        level=info.get("level", 1),
        star=info.get("star", 1),
        equip_bonus=sum(
            int(v.get("power", 0)) for v in info.get("equip", {}).values()
        ) if isinstance(info.get("equip"), dict) else 0,
    )


def all_generals_power(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for name in owned_names(player):
        info = general_info(player, name)
        if not info:
            continue
        result.append({
            "name": name,
            "info": info,
            "power": general_power_of(player, name),
            "level": info.get("level", 1),
            "star": info.get("star", 1),
        })
    result.sort(key=lambda e: e["power"], reverse=True)
    return result


def total_power(player: Dict[str, Any]) -> int:
    return sum(e["power"] for e in all_generals_power(player))


def apply_stamina_recovery(player: Dict[str, Any], max_stamina: int,
                           interval: int, amount: int) -> int:
    """按离线时间恢复行动力，返回恢复后的行动力。"""
    if interval <= 0:
        return int(player.get("stamina", 0))
    now = int(time.time())
    last = int(player.get("stamina_ts", now))
    elapsed = max(0, now - last)
    ticks = elapsed // interval
    if ticks <= 0:
        return int(player.get("stamina", 0))
    stamina = min(max_stamina, int(player.get("stamina", 0)) + ticks * amount)
    player["stamina"] = stamina
    player["stamina_ts"] = last + ticks * interval
    return stamina
