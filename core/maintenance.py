"""维护模式。"""

from __future__ import annotations

from typing import Any, Dict

from . import storage

_FLAG = "maintenance"


def is_on() -> bool:
    data: Dict[str, Any] = storage.load_global(_FLAG, {}) or {}
    return bool(data.get("on", False))


def set_on(on: bool, reason: str = "") -> None:
    import time

    storage.save_global(_FLAG, {"on": bool(on), "reason": reason, "ts": int(time.time())})


def reason() -> str:
    data: Dict[str, Any] = storage.load_global(_FLAG, {}) or {}
    return str(data.get("reason", ""))


def message() -> str:
    r = reason()
    base = "🛠️ 服务器维护中，请稍后再试。"
    return f"{base}\n原因：{r}" if r else base
