"""武将养成：升级 / 升星 / 技能 / 天赋。"""

from __future__ import annotations

from typing import Any, Dict

from . import player as player_mod

MAX_LEVEL = 80
MAX_STAR = 10
MAX_SKILL = 10


def level_up_cost(level: int) -> int:
    return int(80 * level * (1 + 0.08 * level))


def star_up_cost(star: int) -> int:
    """升星消耗通用碎片。"""
    return max(5, star * 5)


def skill_up_cost(skill_lv: int) -> int:
    return 150 * skill_lv


def cultivate(player: Dict[str, Any], name: str, times: int = 1) -> Dict[str, Any]:
    entry = player.get("generals", {}).get(name)
    is_custom = name in player.get("custom_generals", {})
    if entry is None and is_custom:
        entry = player["custom_generals"][name]
        entry.setdefault("level", 1)
    if entry is None:
        return {"ok": False, "reason": "not_owned"}

    times = max(1, min(times, 50))
    done = 0
    spent = 0
    for _ in range(times):
        level = int(entry.get("level", 1))
        if level >= MAX_LEVEL:
            break
        cost = level_up_cost(level)
        if int(player.get("gold", 0)) < cost:
            break
        player_mod.add_gold(player, -cost)
        spent += cost
        entry["level"] = level + 1
        done += 1
    if done == 0:
        return {
            "ok": False,
            "reason": "max_or_gold",
            "level": int(entry.get("level", 1)),
            "gold": player.get("gold", 0),
        }
    if is_custom:
        player_mod.save(player)
    else:
        player_mod.save(player)
    try:
        from . import quest as quest_mod

        quest_mod.sync_max(player, "general_level", int(entry["level"]))
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "name": name, "times": done, "level": entry["level"],
            "spent": spent, "gold_left": player["gold"]}


def star_up(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    if not player_mod.has_general(player, name):
        return {"ok": False, "reason": "not_owned"}
    is_custom = name in player.get("custom_generals", {})
    entry = player["custom_generals"][name] if is_custom else player["generals"][name]
    star = int(entry.get("star", 1))
    if star >= MAX_STAR:
        return {"ok": False, "reason": "max", "star": star}
    cost = star_up_cost(star)
    if int(player.get("fragments", 0)) < cost:
        return {"ok": False, "reason": "fragments", "need": cost,
                "fragments": player.get("fragments", 0)}
    player["fragments"] = int(player.get("fragments", 0)) - cost
    entry["star"] = star + 1
    player_mod.save(player)
    return {"ok": True, "name": name, "star": entry["star"], "cost": cost,
            "fragments_left": player["fragments"]}


def skill_up(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    if not player_mod.has_general(player, name):
        return {"ok": False, "reason": "not_owned"}
    is_custom = name in player.get("custom_generals", {})
    entry = player["custom_generals"][name] if is_custom else player["generals"][name]
    lv = int(entry.get("skill_lv", 1))
    if lv >= MAX_SKILL:
        return {"ok": False, "reason": "max", "skill_lv": lv}
    cost = skill_up_cost(lv)
    if int(player.get("gold", 0)) < cost:
        return {"ok": False, "reason": "gold", "need": cost, "gold": player.get("gold", 0)}
    player_mod.add_gold(player, -cost)
    entry["skill_lv"] = lv + 1
    player_mod.save(player)
    return {"ok": True, "name": name, "skill_lv": entry["skill_lv"],
            "cost": cost, "gold_left": player["gold"]}
