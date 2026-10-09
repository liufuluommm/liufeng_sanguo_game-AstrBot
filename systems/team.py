"""阵容管理：上阵 / 下阵 / 羁绊加成。"""

from __future__ import annotations

from typing import Any, Dict, List

from . import player as player_mod
from .tables import tables

MAX_TEAM = 3


def current_team(player: Dict[str, Any]) -> List[str]:
    return [n for n in player.get("team", []) if player_mod.has_general(player, n)]


def add(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    if not player_mod.has_general(player, name):
        return {"ok": False, "reason": "not_owned"}
    team = current_team(player)
    if name in team:
        return {"ok": False, "reason": "already"}
    if len(team) >= MAX_TEAM:
        return {"ok": False, "reason": "full", "team": team}
    player.setdefault("team", [])
    player["team"] = team + [name]
    player_mod.save(player)
    return {"ok": True, "team": player["team"]}


def remove(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    team = current_team(player)
    if name not in team:
        return {"ok": False, "reason": "not_in_team"}
    team.remove(name)
    player["team"] = team
    player_mod.save(player)
    return {"ok": True, "team": team}


def bonus(player: Dict[str, Any]) -> Dict[str, Any]:
    """计算当前上阵武将的羁绊加成。"""
    names = current_team(player)
    if not current_team(player):
        names = [e["name"] for e in player_mod.all_generals_power(player)[:MAX_TEAM]]
    active: List[Dict[str, Any]] = []
    total = 0.0
    for bond in tables().bonds_for(names):
        members_in = [m for m in bond["members"] if m in names]
        if len(members_in) >= 2:
            total += float(bond.get("bonus", 0.0))
            active.append({"name": bond["name"], "members": members_in, "desc": bond["desc"]})
    return {"bonus": total, "active": active}


def set_leader(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    """设置出战主将（1v1）。"""
    if not player_mod.has_general(player, name):
        return {"ok": False, "reason": "not_owned"}
    player["leader"] = name
    player_mod.save(player)
    return {"ok": True, "leader": name}


def leader_name(player: Dict[str, Any]) -> str:
    """返回有效主将名；未设置或已不拥有则返回空串。"""
    name = player.get("leader") or ""
    if name and player_mod.has_general(player, name):
        return name
    return ""


def _entry(player: Dict[str, Any], name: str) -> Dict[str, Any]:
    info = player_mod.general_info(player, name)
    return {
        "name": name,
        "info": info,
        "level": info.get("level", 1),
        "star": info.get("star", 1),
    }


def duel_entry(player: Dict[str, Any]) -> Dict[str, Any] | None:
    """1v1 出战单将：主将 → 阵容首位 → 战力最高。"""
    leader = leader_name(player)
    if leader:
        return _entry(player, leader)
    team = current_team(player)
    if team:
        return _entry(player, team[0])
    ranked = player_mod.all_generals_power(player)
    if ranked:
        return _entry(player, ranked[0]["name"])
    return None
