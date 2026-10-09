"""任务 / 成就 / 战令进度与领取。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import inventory
from . import player as player_mod

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"


def _load(name: str, default: Any) -> Any:
    path = TABLES_DIR / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _quests() -> Dict[str, List[Dict]]:
    return _load("quests.json", {"daily": [], "weekly": [], "growth": []})


def _achievements() -> List[Dict]:
    return _load("achievements.json", [])


def _period_key(period: str) -> str:
    from datetime import datetime

    now = datetime.now()
    if period == "daily":
        return now.strftime("%Y-%m-%d")
    if period == "weekly":
        iso = now.isocalendar()
        return f"{iso[0]}-W{iso[1]}"
    return "permanent"


def grant_reward(player: Dict[str, Any], reward: Dict[str, Any]) -> List[str]:
    logs = []
    for key, value in reward.items():
        if key == "gold":
            player_mod.add_gold(player, value)
            logs.append(f"金币+{value}")
        elif key == "fragment":
            player["fragments"] = int(player.get("fragments", 0)) + value
            logs.append(f"碎片+{value}")
        elif key == "stamina":
            player["stamina"] = int(player.get("stamina", 0)) + value
            logs.append(f"行动力+{value}")
        elif key in ("diamond", "merit", "soul", "repute", "event_ticket", "challenge"):
            player.setdefault("wallet", {})
            player["wallet"][key] = int(player["wallet"].get(key, 0)) + value
            logs.append(f"{key}+{value}")
        elif key == "title":
            titles = player.setdefault("titles", [])
            if value not in titles:
                titles.append(value)
            logs.append(f"称号【{value}】")
        elif key == "items" and isinstance(value, dict):
            for item_id, count in value.items():
                inventory.add_item(player, item_id, int(count))
                logs.append(f"道具{item_id}x{count}")
    return logs


def progress_event(player: Dict[str, Any], event: str, amount: int = 1) -> None:
    """行为钩子：推进任务与成就进度。"""
    qstate = player.setdefault("quests", {})
    for period, quests in _quests().items():
        key = _period_key(period)
        for q in quests:
            if q.get("event") != event:
                continue
            st = qstate.setdefault(q["id"], {"progress": 0, "claimed": False, "period": key})
            if st.get("period") != key:
                st["period"] = key
                st["progress"] = 0
                st["claimed"] = False
            if not st.get("claimed"):
                st["progress"] = min(int(q["target"]), int(st.get("progress", 0)) + amount)

    astate = player.setdefault("achievements", {})
    for a in _achievements():
        if a.get("event") != event:
            continue
        st = astate.setdefault(a["id"], {"progress": 0, "claimed": False})
        if not st.get("claimed"):
            st["progress"] = min(int(a["target"]), int(st.get("progress", 0)) + amount)
    player_mod.save(player)


def sync_max(player: Dict[str, Any], event: str, value: int) -> None:
    """将匹配事件的进度提升为 max(当前, value)（用于“达到某等级”类目标）。"""
    value = int(value)
    qstate = player.setdefault("quests", {})
    for period, quests in _quests().items():
        key = _period_key(period)
        for q in quests:
            if q.get("event") != event:
                continue
            st = qstate.setdefault(q["id"], {"progress": 0, "claimed": False, "period": key})
            if st.get("period") != key:
                st["period"] = key
                st["progress"] = 0
                st["claimed"] = False
            if not st.get("claimed"):
                st["progress"] = min(int(q["target"]), max(int(st.get("progress", 0)), value))
    astate = player.setdefault("achievements", {})
    for a in _achievements():
        if a.get("event") != event:
            continue
        st = astate.setdefault(a["id"], {"progress": 0, "claimed": False})
        if not st.get("claimed"):
            st["progress"] = min(int(a["target"]), max(int(st.get("progress", 0)), value))
    player_mod.save(player)


def quest_list(player: Dict[str, Any]) -> Dict[str, List[Dict]]:
    qstate = player.get("quests", {})
    result: Dict[str, List[Dict]] = {"daily": [], "weekly": [], "growth": []}
    for period, quests in _quests().items():
        key = _period_key(period)
        for q in quests:
            st = qstate.get(q["id"], {})
            progress = 0 if st.get("period") != key and period in ("daily", "weekly") else int(st.get("progress", 0))
            result[period].append({
                "id": q["id"], "name": q["name"], "target": q["target"],
                "progress": progress,
                "claimed": bool(st.get("claimed")) if st.get("period") == key or period == "growth" else False,
                "reward": q.get("reward", {}),
            })
    return result


def claim_quest(player: Dict[str, Any], quest_id: str) -> Dict[str, Any]:
    qstate = player.get("quests", {})
    st = qstate.get(quest_id)
    if not st:
        return {"ok": False, "reason": "not_found"}
    quest = _find_quest(quest_id)
    if quest is None:
        return {"ok": False, "reason": "not_found"}
    period = _find_quest_period(quest_id)
    if period in ("daily", "weekly") and st.get("period") != _period_key(period):
        return {"ok": False, "reason": "expired"}
    if st.get("claimed"):
        return {"ok": False, "reason": "claimed"}
    if int(st.get("progress", 0)) < int(quest["target"]):
        return {"ok": False, "reason": "incomplete", "progress": st.get("progress", 0),
                "target": quest["target"]}
    st["claimed"] = True
    logs = grant_reward(player, quest.get("reward", {}))
    player_mod.save(player)
    return {"ok": True, "name": quest["name"], "logs": logs}


def achievement_list(player: Dict[str, Any]) -> List[Dict]:
    astate = player.get("achievements", {})
    rows = []
    for a in _achievements():
        st = astate.get(a["id"], {})
        rows.append({
            "id": a["id"], "name": a["name"], "desc": a["desc"], "target": a["target"],
            "progress": int(st.get("progress", 0)), "claimed": bool(st.get("claimed")),
            "reward": a.get("reward", {}),
        })
    return rows


def claim_achievement(player: Dict[str, Any], ach_id: str) -> Dict[str, Any]:
    a = next((x for x in _achievements() if x["id"] == ach_id), None)
    if a is None:
        return {"ok": False, "reason": "not_found"}
    st = player.setdefault("achievements", {}).setdefault(ach_id, {"progress": 0, "claimed": False})
    if st.get("claimed"):
        return {"ok": False, "reason": "claimed"}
    if int(st.get("progress", 0)) < int(a["target"]):
        return {"ok": False, "reason": "incomplete"}
    st["claimed"] = True
    logs = grant_reward(player, a.get("reward", {}))
    player_mod.save(player)
    return {"ok": True, "name": a["name"], "logs": logs}


def _find_quest(quest_id: str) -> Optional[Dict]:
    for quests in _quests().values():
        for q in quests:
            if q["id"] == quest_id:
                return q
    return None


def _find_quest_period(quest_id: str) -> str:
    for period, quests in _quests().items():
        for q in quests:
            if q["id"] == quest_id:
                return period
    return "permanent"
