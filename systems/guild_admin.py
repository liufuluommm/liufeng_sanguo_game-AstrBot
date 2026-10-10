"""管理台「军团管理」：查看、改名、改等级/资金/经验、解散、踢人、转让军团长。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core import storage

from . import player as player_mod

_GLOBAL = "guilds"


def _load() -> Dict[str, Any]:
    data = storage.load_global(_GLOBAL, None)
    if not isinstance(data, dict):
        data = {"counter": 0, "guilds": {}}
    data.setdefault("guilds", {})
    return data


def _save(data: Dict[str, Any]) -> None:
    storage.save_global(_GLOBAL, data)


def _name_of(qq: str) -> str:
    p = player_mod.load(qq)
    return p.get("name", qq) if p else qq


def list_guilds() -> List[Dict[str, Any]]:
    data = _load()
    rows = []
    for gid, g in data["guilds"].items():
        members = g.get("members") or {}
        rows.append({
            "id": gid,
            "name": g.get("name", gid),
            "leader": str(g.get("leader", "")),
            "leader_name": _name_of(str(g.get("leader", ""))),
            "members": len(members),
            "level": int(g.get("level", 1)),
            "fund": int(g.get("fund", 0)),
            "exp": int(g.get("exp", 0)),
            "created": int(g.get("created", 0)),
        })
    rows.sort(key=lambda r: (r["level"], r["fund"]), reverse=True)
    return rows


def detail(gid: str) -> Dict[str, Any]:
    data = _load()
    g = data["guilds"].get(gid)
    if not g:
        return {"ok": False, "reason": "not_found"}
    members = []
    for qq, role in (g.get("members") or {}).items():
        members.append({"qq": qq, "role": role, "name": _name_of(qq)})
    out = dict(g)
    out["members"] = members
    return {"ok": True, "guild": out}


def rename(gid: str, name: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name or len(name) > 12:
        return {"ok": False, "reason": "bad_name"}
    data = _load()
    g = data["guilds"].get(gid)
    if not g:
        return {"ok": False, "reason": "not_found"}
    g["name"] = name
    _save(data)
    return {"ok": True}


def set_stats(gid: str, level: Optional[Any] = None, fund: Optional[Any] = None,
              exp: Optional[Any] = None) -> Dict[str, Any]:
    data = _load()
    g = data["guilds"].get(gid)
    if not g:
        return {"ok": False, "reason": "not_found"}
    if level is not None:
        try:
            g["level"] = max(1, int(level))
        except (TypeError, ValueError):
            pass
    if fund is not None:
        try:
            g["fund"] = max(0, int(fund))
        except (TypeError, ValueError):
            pass
    if exp is not None:
        try:
            g["exp"] = max(0, int(exp))
        except (TypeError, ValueError):
            pass
    _save(data)
    return {"ok": True}


def dissolve(gid: str) -> Dict[str, Any]:
    data = _load()
    g = data["guilds"].get(gid)
    if not g:
        return {"ok": False, "reason": "not_found"}
    for qq in list((g.get("members") or {}).keys()):
        p = player_mod.load(qq)
        if p:
            p["guild"] = ""
            player_mod.save(p)
    data["guilds"].pop(gid, None)
    _save(data)
    return {"ok": True, "name": g.get("name", gid)}


def remove_member(gid: str, qq: str) -> Dict[str, Any]:
    data = _load()
    g = data["guilds"].get(gid)
    if not g:
        return {"ok": False, "reason": "not_found"}
    if str(g.get("leader")) == str(qq):
        return {"ok": False, "reason": "is_leader"}
    if str(qq) not in (g.get("members") or {}):
        return {"ok": False, "reason": "not_member"}
    g["members"].pop(str(qq), None)
    p = player_mod.load(qq)
    if p:
        p["guild"] = ""
        player_mod.save(p)
    _save(data)
    return {"ok": True}


def set_leader(gid: str, qq: str) -> Dict[str, Any]:
    data = _load()
    g = data["guilds"].get(gid)
    if not g:
        return {"ok": False, "reason": "not_found"}
    if str(qq) not in (g.get("members") or {}):
        return {"ok": False, "reason": "not_member"}
    old = str(g.get("leader"))
    if old in (g["members"] or {}):
        g["members"][old] = "member"
    g["leader"] = str(qq)
    g["members"][str(qq)] = "leader"
    _save(data)
    return {"ok": True}
