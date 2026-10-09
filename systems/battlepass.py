"""赛季战令：经验、等级、免费/进阶双轨奖励。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from ..core import storage

from . import player as player_mod

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_STATE = "battlepass_state"
_ENABLED = True


def set_enabled(flag: bool) -> None:
    global _ENABLED
    _ENABLED = bool(flag)


def enabled() -> bool:
    return _ENABLED


def config() -> Dict[str, Any]:
    path = TABLES_DIR / "battlepass.json"
    if not path.exists():
        return {"max_level": 50, "duration_days": 30, "premium_cost": 50, "levels": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _season_state() -> Dict[str, Any]:
    data = storage.load_global(_STATE, None)
    cfg = config()
    now = int(time.time())
    if data is None:
        data = {"season": 1, "start_ts": now}
        storage.save_global(_STATE, data)
    if now - int(data.get("start_ts", now)) > int(cfg.get("duration_days", 30)) * 86400:
        data["season"] = int(data.get("season", 1)) + 1
        data["start_ts"] = now
        storage.save_global(_STATE, data)
    return data


def current_season() -> int:
    return int(_season_state().get("season", 1))


def _entry(player: Dict[str, Any]) -> Dict[str, Any]:
    season = current_season()
    bp = player.setdefault("battlepass", {})
    if bp.get("season") != season:
        bp.clear()
        bp.update({"season": season, "exp": 0, "premium": False,
                   "claimed_free": [], "claimed_premium": []})
    bp.setdefault("exp", 0)
    bp.setdefault("premium", False)
    bp.setdefault("claimed_free", [])
    bp.setdefault("claimed_premium", [])
    return bp


def level_from_exp(exp: int) -> Dict[str, Any]:
    cfg = config()
    levels = cfg.get("levels", [])
    max_level = int(cfg.get("max_level", 50))
    level = 1
    remaining = max(0, int(exp))
    for row in levels:
        if level >= max_level:
            break
        need = int(row.get("exp", 0))
        if remaining >= need and need > 0:
            remaining -= need
            level += 1
        else:
            break
    need_next = 0
    if level < max_level and level - 1 < len(levels):
        need_next = int(levels[level - 1].get("exp", 0)) - remaining
    return {"level": level, "exp_in_level": remaining, "need_next": max(0, need_next)}


def add_exp(player: Dict[str, Any], amount: int) -> Dict[str, Any]:
    if not _ENABLED:
        return level_from_exp(0)
    bp = _entry(player)
    bp["exp"] = int(bp.get("exp", 0)) + max(0, int(amount))
    player_mod.save(player)
    return level_from_exp(bp["exp"])


def progress(player: Dict[str, Any]) -> Dict[str, Any]:
    bp = _entry(player)
    cfg = config()
    lv = level_from_exp(bp["exp"])
    rows = []
    for row in cfg.get("levels", []):
        level = int(row["level"])
        rows.append({
            "level": level,
            "free": row.get("free", {}),
            "premium": row.get("premium", {}),
            "reached": level <= lv["level"],
            "claimed_free": level in bp["claimed_free"],
            "claimed_premium": level in bp["claimed_premium"],
        })
    return {
        "season": bp["season"],
        "season_name": cfg.get("season_name", ""),
        "max_level": cfg.get("max_level", 50),
        "premium": bp["premium"],
        "premium_cost": cfg.get("premium_cost", 50),
        "exp": bp["exp"],
        "level": lv["level"],
        "exp_in_level": lv["exp_in_level"],
        "need_next": lv["need_next"],
        "rows": rows,
    }


def unlock_premium(player: Dict[str, Any]) -> Dict[str, Any]:
    bp = _entry(player)
    if bp["premium"]:
        return {"ok": False, "reason": "already"}
    cost = int(config().get("premium_cost", 50))
    player.setdefault("wallet", {})
    if int(player["wallet"].get("diamond", 0)) < cost:
        return {"ok": False, "reason": "diamond", "need": cost,
                "have": player["wallet"].get("diamond", 0)}
    player["wallet"]["diamond"] = int(player["wallet"]["diamond"]) - cost
    bp["premium"] = True
    player_mod.save(player)
    return {"ok": True, "cost": cost}


def claim(player: Dict[str, Any], level: int, track: str) -> Dict[str, Any]:
    from .quest import grant_reward

    bp = _entry(player)
    cur = level_from_exp(bp["exp"])["level"]
    if level > cur:
        return {"ok": False, "reason": "not_reached", "level": cur}
    cfg = config()
    row = next((r for r in cfg.get("levels", []) if int(r["level"]) == level), None)
    if row is None:
        return {"ok": False, "reason": "no_level"}
    if track == "免费":
        if level in bp["claimed_free"]:
            return {"ok": False, "reason": "claimed"}
        bp["claimed_free"].append(level)
        logs = grant_reward(player, row.get("free", {}))
    elif track == "进阶":
        if not bp["premium"]:
            return {"ok": False, "reason": "no_premium"}
        if level in bp["claimed_premium"]:
            return {"ok": False, "reason": "claimed"}
        bp["claimed_premium"].append(level)
        logs = grant_reward(player, row.get("premium", {}))
    else:
        return {"ok": False, "reason": "bad_track"}
    player_mod.save(player)
    return {"ok": True, "level": level, "track": track, "logs": logs}
