"""兑换所：单向货币兑换。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import player as player_mod
from .shop import _balance, _can_pay, _credit, _pay

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_CACHE: Optional[List[Dict]] = None


def rules() -> List[Dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        path = TABLES_DIR / "exchange.json"
        _CACHE = json.loads(path.read_text(encoding="utf-8")).get("exchanges", []) if path.exists() else []
    return _CACHE


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def remaining(player: Dict[str, Any], rule: Dict[str, Any]) -> int:
    state = player.setdefault("exchange_state", {})
    if state.get("date") != _today():
        state["date"] = _today()
        state["counts"] = {}
    limit = int(rule.get("daily_limit", 0))
    if limit <= 0:
        return 999999
    used = int(state["counts"].get(rule["id"], 0))
    return max(0, limit - used)


def do_exchange(player: Dict[str, Any], ex_id: str, times: int = 1) -> Dict[str, Any]:
    rule = next((r for r in rules() if r["id"] == ex_id), None)
    if rule is None:
        return {"ok": False, "reason": "no_rule"}
    times = max(1, min(int(times), 100))
    remain = remaining(player, rule)
    times = min(times, remain)
    if times <= 0:
        return {"ok": False, "reason": "limit"}
    cost = int(rule["cost"]) * times
    if not _can_pay(player, rule["from"], cost):
        return {"ok": False, "reason": "currency", "need": cost,
                "have": _balance(player, rule["from"])}
    _pay(player, rule["from"], cost)
    gain = int(rule["gain"]) * times
    _credit(player, rule["to"], gain)
    state = player.setdefault("exchange_state", {})
    state.setdefault("counts", {})
    state["counts"][ex_id] = int(state["counts"].get(ex_id, 0)) + times
    player_mod.save(player)
    return {"ok": True, "from": rule["from"], "to": rule["to"], "cost": cost,
            "gain": gain, "times": times, "remain": remain - times}
