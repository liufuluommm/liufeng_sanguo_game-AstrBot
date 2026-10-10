"""文转图卡牌：加载模板并组装渲染数据。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..core.utils import (
    ATTR_KEYS,
    ATTR_LABEL,
    FACTION_LABEL,
    RARITY_LABEL,
    TROOP_LABEL,
)
from . import troops as troops_mod

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_GLYPH = {
    "ssr": "★", "sr": "◆", "r": "▲", "n": "●", "custom": "✦",
}


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def _skill_text(info: Dict[str, Any]) -> str:
    skill = info.get("skill") or {}
    return f"主动 {skill.get('active', '-')} / 被动 {skill.get('passive', '-')}"


def general_card_data(player: Dict[str, Any], name: str,
                      info: Dict[str, Any], power: int,
                      level: int, star: int) -> Dict[str, Any]:
    rarity = info.get("rarity", "n")
    attrs = [
        {"label": ATTR_LABEL[key], "value": info.get(key, 0)}
        for key in ATTR_KEYS
    ]
    return {
        "glyph": _GLYPH.get(rarity, "●"),
        "name": name,
        "title": info.get("title", ""),
        "rarity_class": rarity if rarity in ("ssr", "sr", "r", "n", "custom") else "n",
        "rarity_label": RARITY_LABEL.get(rarity, rarity.upper()),
        "faction_label": FACTION_LABEL.get(info.get("faction", ""), ""),
        "troop_label": troops_mod.label(info.get("troop", "")) or TROOP_LABEL.get(info.get("troop", ""), ""),
        "level": level,
        "star": star,
        "attrs": attrs,
        "power": power,
        "skill": _skill_text(info),
        "desc": info.get("desc", ""),
    }


def battle_report_data(a_name: str, a_team: str, b_name: str, b_team: str,
                       log: list, outcome: str) -> Dict[str, Any]:
    return {
        "a_name": a_name,
        "a_team": a_team,
        "b_name": b_name,
        "b_team": b_team,
        "log": log,
        "outcome": outcome,
    }
