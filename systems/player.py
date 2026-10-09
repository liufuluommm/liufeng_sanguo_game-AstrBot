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


def _migrate(player: Dict[str, Any]) -> Dict[str, Any]:
    """将旧档自定义武将补全为多维能力。"""
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


def general_info(player: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """合并静态表与玩家持有信息，返回完整武将 dict。"""
    data = tables().get(name)
    if data is None:
        custom = player.get("custom_generals", {}).get(name)
        if custom is None:
            return None
        info = dict(custom, id=name, name=name, category="custom", rarity="custom")
        info.setdefault("skill_name", "")
        return info
    owned = player.get("generals", {}).get(name)
    info = dict(data)
    if owned:
        info.update(owned)
    # 接入技能名：供战斗中的主动技能触发使用
    if not info.get("skill_name"):
        skill = info.get("skill") or {}
        skill_def = tables().skill(skill.get("active"))
        if skill_def:
            info["skill_name"] = skill_def.get("name", "")
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
