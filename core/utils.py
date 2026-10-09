"""通用工具：战力计算、时间、随机、文案格式化。"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List

RARITY_ORDER = ["n", "r", "sr", "ssr"]

RARITY_LABEL = {
    "n": "N",
    "r": "R",
    "sr": "SR",
    "ssr": "SSR",
    "custom": "自定义",
}

FACTION_LABEL = {
    "wei": "魏",
    "shu": "蜀",
    "wu": "吴",
    "qun": "群",
    "custom": "自定义",
    "fictional": "架空",
}

TROOP_LABEL = {
    "cavalry": "骑兵",
    "infantry": "步兵",
    "archer": "弓兵",
    "spear": "枪兵",
}

# 兵种克制：key 克制 value 列表中的兵种
TROOP_COUNTER = {
    "cavalry": ["archer"],
    "archer": ["spear"],
    "spear": ["cavalry"],
    "infantry": [],
}

# 多维能力：武力 / 智力 / 体力 / 魅力 / 口才 / 速度
ATTR_KEYS = ["force", "intellect", "vitality", "charisma", "eloquence", "speed"]
ATTR_LABEL = {
    "force": "武力",
    "intellect": "智力",
    "vitality": "体力",
    "charisma": "魅力",
    "eloquence": "口才",
    "speed": "速度",
    "lead": "统率",
}
# 战力权重
ATTR_WEIGHT = {
    "force": 2.0,
    "intellect": 1.5,
    "vitality": 1.5,
    "charisma": 1.0,
    "eloquence": 1.0,
    "speed": 1.2,
}


def base_power(general: Dict[str, Any]) -> int:
    """基础战力：多维能力加权求和。"""
    total = 0
    for key, weight in ATTR_WEIGHT.items():
        total += int(general.get(key, 0)) * weight
    return int(total)



def general_power(
    general: Dict[str, Any],
    level: int = 1,
    star: int = 1,
    equip_bonus: int = 0,
    extra_bonus: float = 0.0,
) -> int:
    """综合战力 = 基础战力 * 星级系数 + 等级成长 + 装备加成，再乘额外加成。"""
    base = base_power(general)
    star_mult = 1.0 + 0.15 * max(0, star - 1)
    level_bonus = (max(1, level) - 1) * 6
    value = base * star_mult + level_bonus + equip_bonus
    value *= 1.0 + extra_bonus
    return int(value)


def today_str() -> str:
    return time.strftime("%Y-%m-%d")


def now_ts() -> int:
    return int(time.time())


def fmt_ts(ts: int) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "-"


def fmt_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: List[str] = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes and not days:
        parts.append(f"{minutes}分")
    return "".join(parts) or "刚刚"


def weighted_choice(options: Iterable[str], weights: Iterable[float]) -> str:
    options = list(options)
    weights = [max(0.0, float(w)) for w in weights]
    total = sum(weights)
    if total <= 0:
        return random.choice(options)
    r = random.uniform(0, total)
    upto = 0.0
    for opt, w in zip(options, weights):
        upto += w
        if r <= upto:
            return opt
    return options[-1]


def roll_percent(probability: float) -> bool:
    """按概率返回 True。probability ∈ [0,1]。"""
    return random.random() < probability


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "░" * length
    filled = int(length * min(1.0, current / total))
    return "█" * filled + "░" * (length - filled)


def sep(char: str = "━", length: int = 22) -> str:
    return char * length


def rarity_rank(rarity: str) -> int:
    try:
        return RARITY_ORDER.index(rarity)
    except ValueError:
        return -1


def sort_generals_by_power(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(entries, key=lambda e: e.get("power", 0), reverse=True)
