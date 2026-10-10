"""管理台「拍卖行管理」：查看全部挂单、强制下架、强制结算、删除、手动结算。"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..core import storage

from . import auction as auction_mod
from . import player as player_mod


def list_all(status: Optional[str] = None) -> List[Dict[str, Any]]:
    data = auction_mod._load()
    rows = []
    now = int(time.time())
    for l in data.get("listings", {}).values():
        if status and l.get("status") != status:
            continue
        rows.append({
            "id": l["id"],
            "seller": l.get("seller"),
            "seller_name": l.get("seller_name", l.get("seller")),
            "kind": l.get("kind"),
            "summary": auction_mod._summary(l),
            "mode": l.get("mode"),
            "price": int(l.get("price", 0)),
            "current_bid": int(l.get("current_bid", 0)),
            "current_bidder": l.get("current_bidder", ""),
            "status": l.get("status"),
            "expire_ts": int(l.get("expire_ts", 0)),
            "left": max(0, int(l.get("expire_ts", 0)) - now),
        })
    order = {"active": 0, "sold": 1, "expired": 2, "defaulted": 3, "cancelled": 4}
    rows.sort(key=lambda r: (order.get(r["status"], 9), r["expire_ts"]))
    return rows


def force_cancel(listing_id: str) -> Dict[str, Any]:
    data = auction_mod._load()
    l = data["listings"].get(listing_id)
    if not l or l.get("status") != "active":
        return {"ok": False, "reason": "not_active"}
    # 退还当前竞拍者保证金
    bidder = l.get("current_bidder")
    if bidder:
        p = storage.load_player(bidder)
        if p:
            player_mod.add_gold(p, int(l.get("deposit", 0)))
            player_mod.save(p)
    l["status"] = "cancelled"
    auction_mod._return_to_seller(l)
    auction_mod._save(data)
    return {"ok": True}


def force_settle(listing_id: str) -> Dict[str, Any]:
    data = auction_mod._load()
    l = data["listings"].get(listing_id)
    if not l or l.get("status") != "active":
        return {"ok": False, "reason": "not_active"}
    bidder_id = l.get("current_bidder")
    if not bidder_id:
        l["status"] = "expired"
        auction_mod._return_to_seller(l)
        auction_mod._save(data)
        return {"ok": True, "result": "expired"}
    buyer = storage.load_player(bidder_id)
    amount = int(l.get("current_bid") or l.get("price", 0))
    deposit = int(l.get("deposit", 0))
    if not buyer or int(buyer.get("gold", 0)) + deposit < amount:
        l["status"] = "defaulted"
        auction_mod._return_to_seller(l)
        auction_mod._save(data)
        return {"ok": True, "result": "defaulted"}
    buyer["gold"] = int(buyer.get("gold", 0)) + deposit - amount
    auction_mod._deliver(l, buyer)
    player_mod.save(buyer)
    seller = storage.load_player(l["seller"])
    if seller:
        player_mod.add_gold(seller, int(amount * (1 - auction_mod.TAX_RATE)))
        player_mod.save(seller)
    l["status"] = "sold"
    l["winner"] = bidder_id
    auction_mod._save(data)
    return {"ok": True, "result": "sold", "price": amount}


def remove(listing_id: str) -> Dict[str, Any]:
    data = auction_mod._load()
    l = data["listings"].get(listing_id)
    if not l:
        return {"ok": False, "reason": "not_found"}
    if l.get("status") == "active":
        bidder = l.get("current_bidder")
        if bidder:
            p = storage.load_player(bidder)
            if p:
                player_mod.add_gold(p, int(l.get("deposit", 0)))
                player_mod.save(p)
        auction_mod._return_to_seller(l)
    data["listings"].pop(listing_id, None)
    auction_mod._save(data)
    return {"ok": True}


def settle_all() -> Dict[str, Any]:
    events = auction_mod.settle()
    return {"ok": True, "count": len(events), "events": events}
