"""配置解析。

不依赖 astrbot，便于单元测试。插件实例化时传入 AstrBotConfig（dict 子类），
这里将其与默认值递归合并，得到一份可安全读取的普通 dict。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Mapping

DEFAULT_CONFIG: Dict[str, Any] = {
    "enable": True,
    "game": {
        "initial_gold": 1000,
        "signin_min": 100,
        "signin_max": 300,
        "battle_reward_min": 50,
        "battle_reward_max": 150,
        "battle_variance": 0.1,
    },
    "gacha": {
        "fragment_exchange_cost": 15,
        "rarity_ssr": 0.05,
        "rarity_sr": 0.15,
        "rarity_r": 0.35,
        "fictional_cost": 5000,
        "fictional_fail_min": 0.25,
        "fictional_fail_max": 0.30,
        "custom_cost": 1000,
        "custom_stat_min": 30,
        "custom_stat_max": 100,
        "dorm_initial_capacity": 15,
        "dorm_upgrade_base": 1500,
        "dorm_upgrade_gain_min": 1,
        "dorm_upgrade_gain_max": 3,
    },
    "dungeon": {
        "fragment_drop_min": 0.05,
        "fragment_drop_max": 0.15,
    },
    "stamina": {
        "max": 120,
        "recover_interval": 300,
        "recover_amount": 1,
    },
    "text_image": {
        "enable": True,
        "theme": "dark_gold",
    },
    "system": {
        "enable_scheduler": True,
        "enable_push": True,
        "enable_broadcast": False,
        "maintenance": False,
        "cooldown_default": 1.5,
        "blocked_push_platforms": ["qq_official", "qqofficial_webhook"],
    },
    "admin": {
        "super_admins": [],
        "web_admins": [],
    },
    "worldboss": {
        "enable": True,
        "attack_limit": 3,
        "duration": 21600,
    },
    "battlepass": {
        "enable": True,
        "exp_per_point": 50,
    },
    "events": {
        "enable": True,
    },
    "skill": {
        "enable": True,
        "default_book_cost": 40,
        "learn_return_book": False,
        "learn_reset_level": True,
    },
}


def _deep_merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """把 override 递归合并进 base 的副本并返回。"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, Mapping)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class GameConfig:
    """配置读取封装，支持点号路径访问。"""

    def __init__(self, raw: Mapping[str, Any] | None = None):
        self._data = _deep_merge(DEFAULT_CONFIG, raw or {})

    def get(self, path: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in path.split("."):
            if isinstance(node, Mapping) and part in node:
                node = node[part]
            else:
                return default
        return node

    def section(self, name: str) -> Dict[str, Any]:
        value = self.get(name, {})
        return value if isinstance(value, dict) else {}

    def as_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    def rarity_rates(self) -> Dict[str, float]:
        """返回归一化后的稀有度概率。"""
        raw = {
            "ssr": float(self.get("gacha.rarity_ssr", 0.05)),
            "sr": float(self.get("gacha.rarity_sr", 0.15)),
            "r": float(self.get("gacha.rarity_r", 0.35)),
            "n": 0.0,
        }
        raw["n"] = max(0.0, 1.0 - raw["ssr"] - raw["sr"] - raw["r"])
        return raw
