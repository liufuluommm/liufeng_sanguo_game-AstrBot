"""副本 PVE：章节关卡、行动力、碎片掉落、扫荡。"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from . import battle as battle_sys
from . import events as events_mod
from . import player as player_mod
from .tables import tables

_DATA: Optional[Dict[str, Any]] = None
_DROP_MIN = 0.05
_DROP_MAX = 0.15


def set_drop_bounds(low: float, high: float) -> None:
    global _DROP_MIN, _DROP_MAX
    try:
        low = max(0.0, float(low))
        high = max(low, float(high))
        _DROP_MIN, _DROP_MAX = low, high
    except (TypeError, ValueError):
        _DROP_MIN, _DROP_MAX = 0.05, 0.15


def _drop_rate(stage: Dict[str, Any]) -> float:
    rate = float(stage.get("drop", _DROP_MIN))
    return max(_DROP_MIN, min(_DROP_MAX, rate))


def _load() -> Dict[str, Any]:
    global _DATA
    if _DATA is None:
        from .tables import TABLES_DIR
        import json

        path = TABLES_DIR / "dungeons.json"
        _DATA = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"chapters": []}
    return _DATA


def chapters() -> List[Dict[str, Any]]:
    return _load().get("chapters", [])


def all_stages() -> List[Dict[str, Any]]:
    result = []
    for ch in chapters():
        for st in ch["stages"]:
            st = dict(st)
            st["chapter"] = ch["id"]
            st["chapter_name"] = ch["name"]
            result.append(st)
    return result


def get_stage(stage_id: str) -> Optional[Dict[str, Any]]:
    for st in all_stages():
        if st["id"] == stage_id:
            return st
    return None


def _prev_stage_id(stage_id: str) -> Optional[str]:
    stages = all_stages()
    ids = [s["id"] for s in stages]
    if stage_id not in ids:
        return None
    idx = ids.index(stage_id)
    return ids[idx - 1] if idx > 0 else None


def is_cleared(player: Dict[str, Any], stage_id: str) -> bool:
    return bool(player.get("dungeon", {}).get(stage_id, {}).get("cleared"))


def is_unlocked(player: Dict[str, Any], stage_id: str) -> bool:
    prev = _prev_stage_id(stage_id)
    if prev is None:
        return True
    return is_cleared(player, prev)


def _enemy_team(stage: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = []
    for name in stage.get("enemy", [])[:3]:
        info = tables().get(name)
        if info is None:
            continue
        entries.append({"name": name, "info": info, "level": int(stage.get("level", 1)), "star": 1})
    return entries


def challenge(player: Dict[str, Any], stage_id: str, team_entries: List[Dict[str, Any]],
              rng: random.Random = random) -> Dict[str, Any]:
    stage = get_stage(stage_id)
    if stage is None:
        return {"ok": False, "reason": "no_stage"}
    if not is_unlocked(player, stage_id):
        return {"ok": False, "reason": "locked"}
    cost = int(stage.get("stamina", 6))
    if events_mod.free_stamina():
        cost = 0
    if int(player.get("stamina", 0)) < cost:
        return {"ok": False, "reason": "stamina", "stamina": player.get("stamina", 0), "need": cost}
    if not team_entries:
        return {"ok": False, "reason": "no_team"}

    player["stamina"] = int(player.get("stamina", 0)) - cost
    enemy = _enemy_team(stage)
    result = battle_sys.simulate(team_entries, enemy, rng=rng)
    won = result["winner"] == "a"

    rewards: Dict[str, Any] = {"gold": 0, "fragment": 0}
    if won:
        gold = int(stage.get("gold", 0) * events_mod.multiplier("double_gold"))
        player_mod.add_gold(player, gold)
        rewards["gold"] = gold
        drop = _drop_rate(stage)
        if rng.random() < drop:
            gain = 2 if events_mod.is_active("double_drop") else 1
            player["fragments"] = int(player.get("fragments", 0)) + gain
            rewards["fragment"] = gain
        dg = player.setdefault("dungeon", {})
        rec = dg.setdefault(stage_id, {"cleared": False, "stars": 0})
        rec["cleared"] = True
        alive = len(result.get("a_alive", []))
        rec["stars"] = max(rec.get("stars", 0), min(3, alive + 1))
    player_mod.save(player)
    return {
        "ok": True,
        "won": won,
        "stage": stage,
        "result": result,
        "rewards": rewards,
        "stamina_left": player["stamina"],
    }


def sweep(player: Dict[str, Any], stage_id: str, times: int = 1,
          rng: random.Random = random) -> Dict[str, Any]:
    stage = get_stage(stage_id)
    if stage is None:
        return {"ok": False, "reason": "no_stage"}
    if not is_cleared(player, stage_id):
        return {"ok": False, "reason": "not_cleared"}
    times = max(1, min(int(times), 20))
    free = events_mod.free_stamina()
    cost_each = 0 if free else int(stage.get("stamina", 6))
    if cost_each > 0:
        can = int(player.get("stamina", 0)) // cost_each
        times = min(times, can)
    if times <= 0:
        return {"ok": False, "reason": "stamina", "stamina": player.get("stamina", 0)}
    gold = 0
    frag = 0
    gold_mult = events_mod.multiplier("double_gold")
    drop_double = events_mod.is_active("double_drop")
    for _ in range(times):
        player["stamina"] = int(player.get("stamina", 0)) - cost_each
        gold += int(stage.get("gold", 0) * gold_mult)
        if rng.random() < _drop_rate(stage):
            frag += 2 if drop_double else 1
    player_mod.add_gold(player, gold)
    player["fragments"] = int(player.get("fragments", 0)) + frag
    player_mod.save(player)
    return {"ok": True, "times": times, "gold": gold, "fragment": frag,
            "stamina_left": player["stamina"], "stage": stage}


def progress(player: Dict[str, Any]) -> Dict[str, Any]:
    total = len(all_stages())
    cleared = sum(1 for s in all_stages() if is_cleared(player, s["id"]))
    stars = sum(player.get("dungeon", {}).get(s["id"], {}).get("stars", 0) for s in all_stages())
    return {"cleared": cleared, "total": total, "stars": stars, "max_stars": total * 3}
