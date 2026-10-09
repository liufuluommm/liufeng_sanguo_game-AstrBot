"""冷却、限流与防刷。进程内内存实现，重启即清空。"""

from __future__ import annotations

import time
from typing import Dict, Tuple

_cooldowns: Dict[str, float] = {}
_daily: Dict[str, Tuple[str, int]] = {}
_counter: Dict[str, Tuple[str, int, int]] = {}


def check_cooldown(key: str, seconds: float) -> Tuple[bool, float]:
    """返回 (是否通过, 剩余秒数)。"""
    now = time.time()
    last = _cooldowns.get(key, 0.0)
    remain = seconds - (now - last)
    if remain > 0:
        return False, remain
    _cooldowns[key] = now
    return True, 0.0


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def get_daily(key: str) -> int:
    day, count = _daily.get(key, ("", 0))
    if day != _today():
        return 0
    return count


def incr_daily(key: str, amount: int = 1) -> int:
    day = _today()
    old_day, count = _daily.get(key, (day, 0))
    if old_day != day:
        count = 0
    count += amount
    _daily[key] = (day, count)
    return count


def check_daily_limit(key: str, limit: int) -> bool:
    """limit<=0 表示不限。"""
    if limit <= 0:
        return True
    return get_daily(key) < limit


def sliding_check(key: str, limit: int, window_seconds: int) -> bool:
    """滑动窗口计数，用于短时间防刷。limit<=0 不限。"""
    if limit <= 0:
        return True
    now = int(time.time())
    stamp = str(now // window_seconds)
    saved_stamp, count, _ = _counter.get(key, ("", 0, 0))
    if saved_stamp != stamp:
        count = 0
    if count >= limit:
        _counter[key] = (stamp, count, now)
        return False
    _counter[key] = (stamp, count + 1, now)
    return True
