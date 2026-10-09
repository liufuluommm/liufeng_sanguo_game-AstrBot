"""极简事件总线：驱动任务 / 成就 / 战令等跨系统进度钩子。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

Handler = Callable[..., Any]

_subscribers: DefaultDict[str, List[Handler]] = defaultdict(list)


def subscribe(event: str, handler: Handler) -> None:
    _subscribers[event].append(handler)


def unsubscribe(event: str, handler: Handler) -> None:
    if handler in _subscribers.get(event, []):
        _subscribers[event].remove(handler)


def emit(event: str, **payload: Any) -> None:
    """同步触发事件；单个订阅者异常不影响其它订阅者。"""
    for handler in list(_subscribers.get(event, [])):
        try:
            handler(event=event, **payload)
        except Exception:  # noqa: BLE001 - 钩子失败不应影响主流程
            continue


def clear() -> None:
    _subscribers.clear()
