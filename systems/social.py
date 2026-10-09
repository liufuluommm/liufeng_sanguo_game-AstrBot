"""好友 / 切磋 / 赠体力。"""

from __future__ import annotations

from typing import Any, Dict, List

from . import player as player_mod


def add_friend(player: Dict[str, Any], friend_qq: str) -> Dict[str, Any]:
    friend_qq = str(friend_qq)
    if friend_qq == str(player["qq"]):
        return {"ok": False, "reason": "self"}
    friends: List[str] = player.setdefault("friends", [])
    if friend_qq in friends:
        return {"ok": False, "reason": "already"}
    if len(friends) >= 100:
        return {"ok": False, "reason": "full"}
    friends.append(friend_qq)
    player_mod.save(player)
    return {"ok": True, "count": len(friends)}


def remove_friend(player: Dict[str, Any], friend_qq: str) -> Dict[str, Any]:
    friends: List[str] = player.setdefault("friends", [])
    if str(friend_qq) not in friends:
        return {"ok": False, "reason": "not_friend"}
    friends.remove(str(friend_qq))
    player_mod.save(player)
    return {"ok": True}


def gift_stamina(player: Dict[str, Any], friend_qq: str, amount: int = 10,
                 max_stamina: int = 120) -> Dict[str, Any]:
    friend = player_mod.load(str(friend_qq))
    if not friend:
        return {"ok": False, "reason": "no_player"}
    state = player.setdefault("gift_state", {})
    import time

    today = time.strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["sent"] = []
    if str(friend_qq) in state.get("sent", []):
        return {"ok": False, "reason": "already"}
    state.setdefault("sent", []).append(str(friend_qq))
    friend["stamina"] = min(max_stamina, int(friend.get("stamina", 0)) + amount)
    player_mod.save(player)
    player_mod.save(friend)
    return {"ok": True, "amount": amount}
