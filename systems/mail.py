"""邮件系统（系统奖励发放/补偿）。"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from ..core import storage

from . import quest as quest_mod

SUB = "mail"


def _load(qq: str) -> List[Dict[str, Any]]:
    return storage.load_player_sub(str(qq), SUB, []) or []


def _save(qq: str, mails: List[Dict[str, Any]]) -> None:
    storage.save_player_sub(str(qq), SUB, mails)


def send(qq: str, title: str, body: str = "", reward: Dict[str, Any] | None = None) -> Dict[str, Any]:
    mails = _load(qq)
    mail = {
        "id": uuid.uuid4().hex[:10],
        "title": title,
        "body": body,
        "reward": reward or {},
        "claimed": False,
        "ts": int(time.time()),
    }
    mails.append(mail)
    _save(qq, mails)
    return mail


def broadcast(qqs: List[str], title: str, body: str = "", reward: Dict[str, Any] | None = None) -> int:
    count = 0
    for qq in qqs:
        send(qq, title, body, reward)
        count += 1
    return count


def inbox(qq: str, include_claimed: bool = False) -> List[Dict[str, Any]]:
    mails = _load(qq)
    if not include_claimed:
        return [m for m in mails if not m.get("claimed")]
    return mails


def claim(qq: str, mail_id: str) -> Dict[str, Any]:
    from . import player as player_mod

    mails = _load(qq)
    mail = next((m for m in mails if m["id"] == mail_id), None)
    if mail is None:
        return {"ok": False, "reason": "not_found"}
    if mail.get("claimed"):
        return {"ok": False, "reason": "claimed"}
    player = player_mod.load(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    logs = quest_mod.grant_reward(player, mail.get("reward", {}))
    player_mod.save(player)
    mail["claimed"] = True
    _save(qq, mails)
    return {"ok": True, "title": mail["title"], "logs": logs}


def claim_all(qq: str) -> Dict[str, Any]:
    from . import player as player_mod

    mails = _load(qq)
    player = player_mod.load(qq)
    if not player:
        return {"ok": False, "reason": "no_player"}
    total_logs: List[str] = []
    count = 0
    for m in mails:
        if m.get("claimed"):
            continue
        total_logs += quest_mod.grant_reward(player, m.get("reward", {}))
        m["claimed"] = True
        count += 1
    player_mod.save(player)
    _save(qq, mails)
    return {"ok": True, "count": count, "logs": total_logs}
