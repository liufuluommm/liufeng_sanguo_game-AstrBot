"""世界BOSS（全服共战，伤害排行发奖）。"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List

from ..core import storage

from . import mail
from . import player as player_mod

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_GLOBAL = "worldboss"
MAX_ATTACKS = 3
DURATION = 6 * 3600


def _bosses() -> List[Dict[str, Any]]:
    path = TABLES_DIR / "bosses.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _load() -> Dict[str, Any]:
    data = storage.load_global(_GLOBAL, None)
    if data is None:
        data = {"active": False}
        storage.save_global(_GLOBAL, data)
    return data


def _save(data: Dict[str, Any]) -> None:
    storage.save_global(_GLOBAL, data)


def spawn(boss_id: str | None = None) -> Dict[str, Any]:
    bosses = _bosses()
    if not bosses:
        return {"ok": False, "reason": "no_boss"}
    if boss_id:
        boss = next((b for b in bosses if b["id"] == boss_id), None)
    else:
        boss = random.choice(bosses)
    if boss is None:
        return {"ok": False, "reason": "no_boss"}
    now = int(time.time())
    data = {
        "active": True,
        "boss": boss,
        "hp": int(boss["hp"]),
        "max_hp": int(boss["hp"]),
        "start_ts": now,
        "end_ts": now + DURATION,
        "participants": {},
        "spawn_seq": int(_load().get("spawn_seq", 0)) + 1,
    }
    _save(data)
    return {"ok": True, "boss": data}


def current() -> Dict[str, Any]:
    data = _load()
    if data.get("active") and int(data.get("end_ts", 0)) <= int(time.time()):
        settle()
        return _load()
    return data


def attack(player: Dict[str, Any], team_power: int, limit: int = MAX_ATTACKS,
           rng: random.Random = random) -> Dict[str, Any]:
    data = _load()
    if not data.get("active"):
        return {"ok": False, "reason": "inactive"}
    qq = str(player["qq"])
    part = data["participants"].setdefault(qq, {"damage": 0, "count": 0, "name": player.get("name", qq)})
    if part["count"] >= limit:
        return {"ok": False, "reason": "limit", "max": limit}
    boss = data["boss"]
    raw = team_power * rng.uniform(1.0, 1.6)
    damage = max(1, int(raw - boss.get("def", 0)))
    part["count"] += 1
    part["damage"] += damage
    part["name"] = player.get("name", qq)
    data["hp"] = max(0, int(data["hp"]) - damage)
    player_mod.save(player)
    defeated = data["hp"] <= 0
    _save(data)
    result = {
        "ok": True, "damage": damage, "hp": data["hp"], "max_hp": data["max_hp"],
        "attacks_left": MAX_ATTACKS - part["count"], "defeated": defeated,
    }
    if defeated:
        result["settle"] = settle()
    return result


def ranking(limit: int = 10) -> List[Dict[str, Any]]:
    data = _load()
    rows = []
    for qq, p in data.get("participants", {}).items():
        rows.append({"qq": qq, "name": p.get("name", qq), "damage": p.get("damage", 0),
                     "count": p.get("count", 0)})
    rows.sort(key=lambda r: r["damage"], reverse=True)
    return rows[:limit]


def settle() -> Dict[str, Any]:
    data = _load()
    if not data.get("active"):
        return {"ok": False, "reason": "inactive"}
    rows = []
    for qq, p in data.get("participants", {}).items():
        rows.append((qq, p.get("damage", 0)))
    rows.sort(key=lambda r: r[1], reverse=True)
    rewards = [
        {"gold": 5000, "diamond": 50, "fragment": 10},
        {"gold": 3000, "diamond": 30, "fragment": 6},
        {"gold": 2000, "diamond": 15, "fragment": 4},
    ]
    for i, (qq, dmg) in enumerate(rows):
        if dmg <= 0:
            continue
        if i < 3:
            reward = rewards[i]
        else:
            reward = {"gold": 800, "fragment": 1}
        mail.send(qq, "世界BOSS奖励", f"讨伐 {data['boss']['name']}，伤害 {dmg}", reward)
    data["active"] = False
    data["last_result"] = {"boss": data["boss"]["name"], "participants": len(rows),
                           "ts": int(time.time())}
    _save(data)
    return {"ok": True, "participants": len(rows)}


def status() -> str:
    data = current()
    if not data.get("active"):
        return "世界BOSS未开启。"
    left = max(0, int(data["end_ts"]) - int(time.time()))
    return f"{data['boss']['name']} HP {data['hp']}/{data['max_hp']} 剩余{left // 3600}时{left % 3600 // 60}分"
