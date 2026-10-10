"""管理台「玩家管理」操作：资料修改、货币/资源、邮件发放、批量清空、封禁、删除（连带清理）。

- 直接修正余额：`adjust_currency`
- 发放奖励（货币/碎片/道具/武将）统一走**邮件附件**：`give_via_mail`
- 删除玩家：`remove_player` 会连带清理 军团/国战/拍卖/世界BOSS/玩家目录/封禁记录；
  被删玩家若是军团长则**解散该军团**。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from ..core import storage
from . import mail as mail_mod
from . import player as player_mod

WALLET_CURRENCIES = ("diamond", "merit", "soul", "repute", "event_ticket", "challenge", "skill_frag")
CURRENCIES = ("gold",) + WALLET_CURRENCIES + ("fragments", "stamina")
VALID_FACTIONS = ("wei", "shu", "wu", "qun", "custom", "fictional", "")
CLEAR_TARGETS = ("inventory", "custom_generals", "team")
_BANS = "bans"


def _clamp(v: Any, low: int = 0, high: int = 10 ** 9, default: int = 0) -> int:
    try:
        return max(low, min(high, int(v)))
    except (TypeError, ValueError):
        return default


def player_exists(qq: str) -> bool:
    return storage.player_exists(str(qq))


# ---------------------------------------------------------------------------
# 资料修改（直接生效）
# ---------------------------------------------------------------------------
def edit_profile(qq: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    player = player_mod.load(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    f = fields or {}
    if "name" in f and str(f["name"]).strip():
        player["name"] = str(f["name"]).strip()[:20]
    if "level" in f:
        player["level"] = _clamp(f["level"], 1, 9999, 1)
    if "exp" in f:
        player["exp"] = _clamp(f["exp"], 0, 10 ** 12)
    if "faction" in f:
        fac = str(f["faction"])
        if fac in VALID_FACTIONS:
            player["faction"] = fac
    if "win" in f:
        player["win"] = _clamp(f["win"])
    if "lose" in f:
        player["lose"] = _clamp(f["lose"])
    if "stamina" in f:
        player["stamina"] = _clamp(f["stamina"])
    if "rating" in f:
        player.setdefault("pvp", {})
        player["pvp"]["rating"] = _clamp(f["rating"], 0, 10 ** 6, 1000)
    if "dorm_capacity" in f:
        dorm = player.setdefault("buildings", {}).setdefault("dormitory", {})
        dorm["capacity"] = _clamp(f["dorm_capacity"], 1, 999, 15)
    player_mod.save(player)
    return {"ok": True}


# ---------------------------------------------------------------------------
# 货币 / 资源（add | set）
# ---------------------------------------------------------------------------
def _balance(player: Dict[str, Any], currency: str) -> int:
    if currency in ("fragments", "stamina"):
        return int(player.get(currency, 0))
    if currency == "gold":
        return int(player.get("gold", 0))
    return int(player.get("wallet", {}).get(currency, 0))


def _set_balance(player: Dict[str, Any], currency: str, value: int) -> None:
    value = max(0, int(value))
    if currency in ("fragments", "stamina"):
        player[currency] = value
    elif currency == "gold":
        player["gold"] = value
        player.setdefault("wallet", {})["gold"] = value
    else:
        player.setdefault("wallet", {})[currency] = value


def adjust_currency(qq: str, currency: str, mode: str = "add", amount: int = 0) -> Dict[str, Any]:
    if currency not in CURRENCIES:
        return {"ok": False, "reason": "bad_currency"}
    player = player_mod.load(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    amount = _clamp(amount, 0, 10 ** 12)
    if mode == "set":
        new = amount
    else:
        new = _balance(player, currency) + amount
        if mode == "sub":
            new = _balance(player, currency) - amount
    _set_balance(player, currency, new)
    player_mod.save(player)
    return {"ok": True, "currency": currency, "value": _balance(player, currency)}


# ---------------------------------------------------------------------------
# 邮件发放（货币/碎片/道具/武将 统一走附件）
# ---------------------------------------------------------------------------
def give_via_mail(qq: str, title: str, body: str = "", reward: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not player_mod.load(qq):
        return {"ok": False, "reason": "no_player"}
    reward = reward or {}
    mail = mail_mod.send(qq, str(title or "系统奖励")[:40], str(body or ""), reward)
    return {"ok": True, "mail_id": mail.get("id")}


# ---------------------------------------------------------------------------
# 批量清空
# ---------------------------------------------------------------------------
def clear(qq: str, target: str) -> Dict[str, Any]:
    if target not in CLEAR_TARGETS:
        return {"ok": False, "reason": "bad_target"}
    player = player_mod.load(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    if target == "inventory":
        player["inventory"] = {}
    elif target == "custom_generals":
        player["custom_generals"] = {}
    elif target == "team":
        player["team"] = []
        player["leader"] = ""
    player_mod.save(player)
    return {"ok": True, "target": target}


# ---------------------------------------------------------------------------
# 封禁
# ---------------------------------------------------------------------------
def _load_bans() -> Dict[str, Any]:
    data = storage.load_global(_BANS, None)
    return data if isinstance(data, dict) else {}


def is_banned(qq: str) -> bool:
    return str(qq) in _load_bans()


def ban_reason(qq: str) -> str:
    return str(_load_bans().get(str(qq), {}).get("reason", ""))


def ban(qq: str, reason: str = "") -> Dict[str, Any]:
    data = _load_bans()
    data[str(qq)] = {"reason": str(reason), "ts": int(time.time())}
    storage.save_global(_BANS, data)
    return {"ok": True}


def unban(qq: str) -> Dict[str, Any]:
    data = _load_bans()
    if str(qq) not in data:
        return {"ok": False, "reason": "not_banned"}
    data.pop(str(qq), None)
    storage.save_global(_BANS, data)
    return {"ok": True}


def list_bans() -> List[Dict[str, Any]]:
    data = _load_bans()
    return [{"qq": qq, **v} for qq, v in data.items()]


# ---------------------------------------------------------------------------
# 删除玩家（连带清理关联数据；军团长则解散军团）
# ---------------------------------------------------------------------------
def remove_player(qq: str) -> Dict[str, Any]:
    qq = str(qq)
    player = player_mod.load(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    detail = {"guild_dissolved": "", "guild_left": "", "faction": False,
              "auction_removed": 0, "auction_bids_cleared": 0, "worldboss": False}

    # 军团
    gdata = storage.load_global("guilds", None)
    if isinstance(gdata, dict) and isinstance(gdata.get("guilds"), dict):
        gid = player.get("guild")
        guild = gdata["guilds"].get(gid) if gid else None
        if guild:
            if str(guild.get("leader")) == qq:
                # 军团长 → 解散军团，其余成员清空归属
                for member in list((guild.get("members") or {}).keys()):
                    if str(member) == qq:
                        continue
                    mp = player_mod.load(member)
                    if mp:
                        mp["guild"] = ""
                        player_mod.save(mp)
                detail["guild_dissolved"] = str(guild.get("name", gid))
                gdata["guilds"].pop(gid, None)
            else:
                guild.get("members", {}).pop(qq, None)
                detail["guild_left"] = str(guild.get("name", gid))
                if not guild.get("members"):
                    gdata["guilds"].pop(gid, None)
            storage.save_global("guilds", gdata)

    # 国战势力
    fdata = storage.load_global("factions", None)
    if isinstance(fdata, dict) and isinstance(fdata.get("members"), dict):
        changed = False
        for fac, members in fdata["members"].items():
            if isinstance(members, list) and qq in [str(m) for m in members]:
                fdata["members"][fac] = [m for m in members if str(m) != qq]
                changed = True
        if changed:
            storage.save_global("factions", fdata)
            detail["faction"] = True

    # 拍卖行
    adata = storage.load_global("auction", None)
    if isinstance(adata, dict) and isinstance(adata.get("listings"), dict):
        changed = False
        for lid, listing in list(adata["listings"].items()):
            if str(listing.get("seller")) == qq:
                adata["listings"].pop(lid, None)
                detail["auction_removed"] += 1
                changed = True
            elif str(listing.get("current_bidder") or "") == qq:
                listing["current_bidder"] = None
                listing["current_bid"] = 0
                detail["auction_bids_cleared"] += 1
                changed = True
        if changed:
            storage.save_global("auction", adata)

    # 世界BOSS
    wdata = storage.load_global("worldboss", None)
    if isinstance(wdata, dict) and isinstance(wdata.get("participants"), dict) and qq in wdata["participants"]:
        wdata["participants"].pop(qq, None)
        storage.save_global("worldboss", wdata)
        detail["worldboss"] = True

    # 封禁记录
    unban(qq)

    # 玩家目录（含邮件等子数据）
    storage.delete_player_data(qq)
    detail["ok"] = True
    detail["name"] = player.get("name", qq)
    return detail
