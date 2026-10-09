"""系统商城：购买 / 限购 / 刷新 / 锁定。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import inventory
from . import player as player_mod

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_CACHE: Optional[Dict[str, Any]] = None


def load_shops() -> Dict[str, Any]:
    global _CACHE
    path = TABLES_DIR / "shops.json"
    _CACHE = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _CACHE


def shops() -> Dict[str, Any]:
    if _CACHE is None:
        load_shops()
    return _CACHE or {}


def shop_names() -> List[str]:
    return list(shops().keys())


def _period_key(period: str) -> str:
    now = datetime.now()
    if period == "daily":
        return now.strftime("%Y-%m-%d")
    if period == "weekly":
        iso = now.isocalendar()
        return f"{iso[0]}-W{iso[1]}"
    if period == "monthly":
        return now.strftime("%Y-%m")
    return "permanent"


def _state(player: Dict[str, Any], shop: str) -> Dict[str, Any]:
    return player.setdefault("shop_state", {}).setdefault(
        shop, {"period": "", "bought": {}, "locked": []}
    )


def listings(shop: str) -> List[Dict[str, Any]]:
    return shops().get(shop, {}).get("listings", [])


def view(player: Dict[str, Any], shop: str) -> Dict[str, Any]:
    definition = shops().get(shop)
    if not definition:
        return {"ok": False, "reason": "no_shop"}
    period = definition.get("reset", "daily")
    key = _period_key(period)
    state = _state(player, shop)
    if state.get("period") != key:
        state["period"] = key
        state["bought"] = {}
    rows = []
    for item in listings(shop):
        bought = int(state["bought"].get(item["item"], 0))
        rows.append({
            "item": item["item"],
            "currency": item["currency"],
            "price": item["price"],
            "limit": item["limit"],
            "bought": bought,
            "locked": item["item"] in state.get("locked", []),
        })
    player_mod.save(player)
    return {"ok": True, "name": definition.get("name", shop), "rows": rows,
            "locked": state.get("locked", [])}


def buy(player: Dict[str, Any], shop: str, item_id: str, qty: int = 1) -> Dict[str, Any]:
    definition = shops().get(shop)
    if not definition:
        return {"ok": False, "reason": "no_shop"}
    listing = next((x for x in listings(shop) if x["item"] == item_id), None)
    if listing is None:
        return {"ok": False, "reason": "not_listed"}
    qty = max(1, min(int(qty), 99))
    state = _state(player, shop)
    key = _period_key(definition.get("reset", "daily"))
    if state.get("period") != key:
        state["period"] = key
        state["bought"] = {}
    bought = int(state["bought"].get(item_id, 0))
    limit = int(listing.get("limit", 0))
    if limit > 0:
        qty = min(qty, limit - bought)
    if qty <= 0:
        return {"ok": False, "reason": "limit"}
    currency = listing.get("currency", "gold")
    total = int(listing.get("price", 0)) * qty
    if not _can_pay(player, currency, total):
        return {"ok": False, "reason": "currency", "currency": currency,
                "need": total, "have": _balance(player, currency)}
    _pay(player, currency, total)
    inventory.add_item(player, item_id, qty)
    state["bought"][item_id] = bought + qty
    player_mod.save(player)
    return {"ok": True, "item": item_id, "qty": qty, "currency": currency,
            "total": total, "balance": _balance(player, currency)}


def lock(player: Dict[str, Any], shop: str, item_id: str) -> Dict[str, Any]:
    state = _state(player, shop)
    locked = state.setdefault("locked", [])
    if item_id in locked:
        return {"ok": False, "reason": "already"}
    if len(locked) >= 3:
        return {"ok": False, "reason": "full"}
    locked.append(item_id)
    player_mod.save(player)
    return {"ok": True, "locked": locked}


def unlock(player: Dict[str, Any], shop: str, item_id: str) -> Dict[str, Any]:
    state = _state(player, shop)
    locked = state.setdefault("locked", [])
    if item_id not in locked:
        return {"ok": False, "reason": "not_locked"}
    locked.remove(item_id)
    player_mod.save(player)
    return {"ok": True, "locked": locked}


# ---------------------------------------------------------------------------
# 货币
# ---------------------------------------------------------------------------
CURRENCIES = ["gold", "diamond", "merit", "soul", "repute", "event_ticket", "challenge"]


def _balance(player: Dict[str, Any], currency: str) -> int:
    if currency == "gold":
        return int(player.get("gold", 0))
    return int(player.get("wallet", {}).get(currency, 0))


def _can_pay(player: Dict[str, Any], currency: str, amount: int) -> bool:
    return _balance(player, currency) >= amount


def _pay(player: Dict[str, Any], currency: str, amount: int) -> None:
    if currency == "gold":
        player_mod.add_gold(player, -amount)
        return
    player.setdefault("wallet", {})
    player["wallet"][currency] = max(0, int(player["wallet"].get(currency, 0)) - amount)


def _credit(player: Dict[str, Any], currency: str, amount: int) -> None:
    if currency == "gold":
        player_mod.add_gold(player, amount)
        return
    player.setdefault("wallet", {})
    player["wallet"][currency] = int(player["wallet"].get(currency, 0)) + amount
