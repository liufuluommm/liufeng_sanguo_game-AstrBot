"""玩家拍卖行：一口价 + 竞拍（保证金、抽税、时长、流拍退件）。

全局跨群共享，数据存 global/auction.json。
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

from ..core import storage

from . import inventory
from . import player as player_mod

TAX_RATE = 0.05
DEPOSIT_RATE = 0.10
DURATIONS = [1, 6, 12, 24]  # 小时
GLOBAL_NAME = "auction"


def _load() -> Dict[str, Any]:
    data = storage.load_global(GLOBAL_NAME, None)
    if data is None:
        data = {"counter": 0, "listings": {}}
        storage.save_global(GLOBAL_NAME, data)
    return data


def _save(data: Dict[str, Any]) -> None:
    storage.save_global(GLOBAL_NAME, data)


def _next_id(data: Dict[str, Any]) -> str:
    data["counter"] = int(data.get("counter", 0)) + 1
    return f"A{data['counter']:05d}"


def _active_listings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    now = int(time.time())
    return [l for l in data["listings"].values() if l.get("status") == "active" and l["expire_ts"] > now]


def list_active(limit: int = 20) -> List[Dict[str, Any]]:
    data = _load()
    rows = sorted(_active_listings(data), key=lambda l: l["expire_ts"])
    return rows[:limit]


def get(listing_id: str) -> Optional[Dict[str, Any]]:
    return _load()["listings"].get(listing_id)


def _summary(listing: Dict[str, Any]) -> str:
    payload = listing.get("payload", {})
    if listing["kind"] == "equipment":
        return f"装备 {payload.get('name', payload.get('id'))} +{payload.get('level', 1)}"
    if listing["kind"] == "item":
        from . import items as items_mod

        item = items_mod.get_item(payload.get("item_id", "")) or {}
        return f"道具 {item.get('name', payload.get('item_id'))} x{payload.get('count', 1)}"
    if listing["kind"] == "fragment":
        return f"武将碎片 x{payload.get('count', 0)}"
    return listing["kind"]


def _create(data: Dict[str, Any], player: Dict[str, Any], kind: str, payload: Dict,
            mode: str, price: int, step: int, hours: int) -> Dict[str, Any]:
    if mode not in ("buyout", "bid"):
        return {"ok": False, "reason": "bad_mode"}
    if hours not in DURATIONS:
        return {"ok": False, "reason": "bad_duration"}
    if price <= 0:
        return {"ok": False, "reason": "bad_price"}
    listing_id = _next_id(data)
    now = int(time.time())
    listing = {
        "id": listing_id,
        "seller": str(player["qq"]),
        "seller_name": player.get("name", player["qq"]),
        "kind": kind,
        "payload": payload,
        "mode": mode,
        "price": int(price),
        "step": max(1, int(step)),
        "current_bid": 0,
        "current_bidder": "",
        "deposit": 0,
        "created_ts": now,
        "expire_ts": now + hours * 3600,
        "status": "active",
    }
    data["listings"][listing_id] = listing
    return {"ok": True, "listing": listing}


def _validate(mode: str, price: int, hours: int) -> Optional[str]:
    if mode not in ("buyout", "bid"):
        return "bad_mode"
    if int(hours) not in DURATIONS:
        return "bad_duration"
    if int(price) <= 0:
        return "bad_price"
    return None


def create_equipment(player: Dict[str, Any], index: int, mode: str, price: int,
                     step: int = 50, hours: int = 6) -> Dict[str, Any]:
    err = _validate(mode, price, hours)
    if err:
        return {"ok": False, "reason": err}
    equipments = player.get("equipments", [])
    if not (0 <= index < len(equipments)):
        return {"ok": False, "reason": "not_found"}
    item = equipments[index]
    if item.get("equipped_by"):
        return {"ok": False, "reason": "equipped"}
    from . import equipment as equip_sys
    from .tables import tables

    eq = tables().equipment(item["id"]) or {}
    equipments.pop(index)
    player_mod.save(player)
    payload = {"uid": item["uid"], "id": item["id"], "level": item.get("level", 1),
               "name": eq.get("name"), "rarity": eq.get("rarity")}
    data = _load()
    res = _create(data, player, "equipment", payload, mode, price, step, hours)
    _save(data)
    return res


def create_item(player: Dict[str, Any], item_id: str, count: int, mode: str, price: int,
                step: int = 50, hours: int = 6) -> Dict[str, Any]:
    err = _validate(mode, price, hours)
    if err:
        return {"ok": False, "reason": err}
    count = int(count)
    if count <= 0 or inventory.count_of(player, item_id) < count:
        return {"ok": False, "reason": "not_enough"}
    inventory.remove_item(player, item_id, count)
    player_mod.save(player)
    data = _load()
    res = _create(data, player, "item", {"item_id": item_id, "count": count},
                  mode, price, step, hours)
    _save(data)
    return res


def create_fragment(player: Dict[str, Any], count: int, mode: str, price: int,
                    step: int = 50, hours: int = 6) -> Dict[str, Any]:
    err = _validate(mode, price, hours)
    if err:
        return {"ok": False, "reason": err}
    count = int(count)
    if count <= 0 or int(player.get("fragments", 0)) < count:
        return {"ok": False, "reason": "not_enough"}
    player["fragments"] = int(player.get("fragments", 0)) - count
    player_mod.save(player)
    data = _load()
    res = _create(data, player, "fragment", {"count": count}, mode, price, step, hours)
    _save(data)
    return res


def cancel(player: Dict[str, Any], listing_id: str) -> Dict[str, Any]:
    data = _load()
    listing = data["listings"].get(listing_id)
    if not listing or listing["status"] != "active":
        return {"ok": False, "reason": "not_found"}
    if listing["seller"] != str(player["qq"]):
        return {"ok": False, "reason": "not_owner"}
    if listing.get("current_bidder"):
        return {"ok": False, "reason": "has_bid"}
    listing["status"] = "cancelled"
    _return_to_seller(listing)
    _save(data)
    return {"ok": True}


def _return_to_seller(listing: Dict[str, Any]) -> None:
    seller = storage.load_player(listing["seller"])
    if not seller:
        return
    payload = listing["payload"]
    if listing["kind"] == "equipment":
        seller.setdefault("equipments", []).append(
            {"uid": payload.get("uid"), "id": payload.get("id"),
             "level": payload.get("level", 1), "equipped_by": None}
        )
    elif listing["kind"] == "item":
        inventory.add_item(seller, payload["item_id"], payload.get("count", 1))
    elif listing["kind"] == "fragment":
        seller["fragments"] = int(seller.get("fragments", 0)) + payload.get("count", 0)
    player_mod.save(seller)


def _deliver(listing: Dict[str, Any], buyer: Dict[str, Any]) -> None:
    payload = listing["payload"]
    if listing["kind"] == "equipment":
        buyer.setdefault("equipments", []).append(
            {"uid": payload.get("uid"), "id": payload.get("id"),
             "level": payload.get("level", 1), "equipped_by": None}
        )
    elif listing["kind"] == "item":
        inventory.add_item(buyer, payload["item_id"], payload.get("count", 1))
    elif listing["kind"] == "fragment":
        buyer["fragments"] = int(buyer.get("fragments", 0)) + payload.get("count", 0)


def buyout(player: Dict[str, Any], listing_id: str) -> Dict[str, Any]:
    data = _load()
    listing = data["listings"].get(listing_id)
    if not listing or listing["status"] != "active":
        return {"ok": False, "reason": "not_found"}
    if listing.get("mode") == "bid":
        return {"ok": False, "reason": "bid_only"}
    if int(listing["expire_ts"]) <= int(time.time()):
        return {"ok": False, "reason": "expired"}
    if listing["seller"] == str(player["qq"]):
        return {"ok": False, "reason": "self"}
    price = int(listing["price"])
    if int(player.get("gold", 0)) < price:
        return {"ok": False, "reason": "gold", "need": price, "have": player.get("gold", 0)}
    # 退还已有竞拍者保证金
    if listing.get("current_bidder"):
        prev = storage.load_player(listing["current_bidder"])
        if prev:
            player_mod.add_gold(prev, int(listing.get("deposit", 0)))
            player_mod.save(prev)
    player_mod.add_gold(player, -price)
    _deliver(listing, player)
    player_mod.save(player)
    seller = storage.load_player(listing["seller"])
    if seller:
        player_mod.add_gold(seller, int(price * (1 - TAX_RATE)))
        player_mod.save(seller)
    listing["status"] = "sold"
    listing["winner"] = str(player["qq"])
    _save(data)
    return {"ok": True, "price": price, "tax": int(price * TAX_RATE)}


def bid(player: Dict[str, Any], listing_id: str, amount: int) -> Dict[str, Any]:
    data = _load()
    listing = data["listings"].get(listing_id)
    if not listing or listing["status"] != "active" or listing.get("mode") != "bid":
        return {"ok": False, "reason": "not_biddable"}
    if int(listing["expire_ts"]) <= int(time.time()):
        return {"ok": False, "reason": "expired"}
    if listing["seller"] == str(player["qq"]):
        return {"ok": False, "reason": "self"}
    amount = int(amount)
    min_amount = int(listing.get("price", 0)) if not listing.get("current_bid") else int(listing["current_bid"]) + int(listing["step"])
    if amount < min_amount:
        return {"ok": False, "reason": "too_low", "min": min_amount}
    deposit = max(1, math.ceil(amount * DEPOSIT_RATE))
    if int(player.get("gold", 0)) < deposit:
        return {"ok": False, "reason": "gold", "need": deposit, "have": player.get("gold", 0)}
    # 退还上一竞拍者保证金
    if listing.get("current_bidder"):
        prev = storage.load_player(listing["current_bidder"])
        if prev:
            player_mod.add_gold(prev, int(listing.get("deposit", 0)))
            player_mod.save(prev)
    player_mod.add_gold(player, -deposit)
    player_mod.save(player)
    listing["current_bid"] = amount
    listing["current_bidder"] = str(player["qq"])
    listing["deposit"] = deposit
    _save(data)
    return {"ok": True, "amount": amount, "deposit": deposit}


def settle(now: Optional[int] = None) -> List[Dict[str, Any]]:
    """结算到期拍卖：有竞拍者则成交，否则退件。返回事件列表。"""
    data = _load()
    if now is None:
        now = int(time.time())
    else:
        now = int(now)
    events: List[Dict[str, Any]] = []
    for listing in list(data["listings"].values()):
        if listing.get("status") != "active" or int(listing["expire_ts"]) > now:
            continue
        bidder_id = listing.get("current_bidder")
        if not bidder_id:
            listing["status"] = "expired"
            _return_to_seller(listing)
            events.append({"id": listing["id"], "result": "expired"})
            continue
        buyer = storage.load_player(bidder_id)
        amount = int(listing["current_bid"])
        deposit = int(listing.get("deposit", 0))
        if not buyer or int(buyer.get("gold", 0)) + deposit < amount:
            # 违约：没收保证金，退件给卖家
            listing["status"] = "defaulted"
            _return_to_seller(listing)
            events.append({"id": listing["id"], "result": "defaulted", "buyer": bidder_id})
            continue
        buyer["gold"] = int(buyer.get("gold", 0)) + deposit - amount
        _deliver(listing, buyer)
        player_mod.save(buyer)
        seller = storage.load_player(listing["seller"])
        if seller:
            player_mod.add_gold(seller, int(amount * (1 - TAX_RATE)))
            player_mod.save(seller)
        listing["status"] = "sold"
        events.append({"id": listing["id"], "result": "sold", "buyer": bidder_id, "price": amount})
    _save(data)
    return events


def my_listings(qq: str) -> List[Dict[str, Any]]:
    data = _load()
    return [l for l in data["listings"].values() if l["seller"] == str(qq)]


def describe(listing: Dict[str, Any]) -> str:
    if listing["mode"] == "buyout":
        price = f"一口价 {listing['price']}"
    else:
        price = f"起拍 {listing['price']} 加价 {listing['step']}"
        if listing.get("current_bid"):
            price += f" 当前 {listing['current_bid']}({listing['current_bidder']})"
    left = max(0, int(listing["expire_ts"]) - int(time.time()))
    return f"[{listing['id']}] {_summary(listing)} | {price} | 剩{left // 3600}时{left % 3600 // 60}分"
