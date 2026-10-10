"""技能效果「按名生成」。

给定技能名与类型，按关键词判定类别，再从 350 效果库中**确定性地**（同名稳定）
挑选模板并生成技能定义，供战斗使用。
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import storage

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_CACHE: Optional[List[Dict[str, Any]]] = None
_CUSTOM: Optional[Dict[str, Dict]] = None
_BUILTIN: Optional[Dict[str, Dict]] = None

# 关键词 -> 类别（取首个命中）
CATEGORY_KEYWORDS = [
    ("heal", ["疗", "愈", "济", "养", "复", "苏", "净", "护", "援", "仁", "命"]),
    ("control", ["定", "封", "慑", "冻", "缚", "乱", "迷", "嘲", "械", "禁", "威压", "震"]),
    ("buff", ["振", "励", "威", "勇", "固", "守", "疾", "巧", "韧", "锐", "御", "统御", "威望", "仁德", "强运"]),
    ("debuff", ["弱", "钝", "滞", "毒", "灼", "怯", "衰", "洞烛"]),
    ("special", ["连", "追", "反", "唤", "奇", "变", "势"]),
    ("damage", ["力", "斩", "破", "裂", "火", "雷", "计", "谋", "箭", "弩", "刺", "劈", "爆", "袭", "战", "阵", "突", "扫", "扇", "锋", "罡"]),
]


def _effects() -> List[Dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        path = TABLES_DIR / "skill_effects.json"
        try:
            _CACHE = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        except (json.JSONDecodeError, OSError):
            _CACHE = []
    return _CACHE


def _h(name: str) -> int:
    return zlib.crc32(name.encode("utf-8")) % 1000000


def classify(name: str, skill_type: str = "active") -> str:
    for cat, words in CATEGORY_KEYWORDS:
        for w in words:
            if w in name:
                return cat
    return "buff" if skill_type == "passive" else "damage"


def custom_skills() -> Dict[str, Dict]:
    """管理员自定义技能（数据目录 skills_custom.json，按名索引）。"""
    global _CUSTOM
    if _CUSTOM is None:
        try:
            path = storage.data_root() / "skills_custom.json"
            _CUSTOM = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (json.JSONDecodeError, OSError):
            _CUSTOM = {}
    return _CUSTOM


def custom_def(name: str) -> Optional[Dict[str, Any]]:
    return custom_skills().get(name)


def builtin_skills() -> Dict[str, Dict]:
    """内置 30 技能（tables/builtin_skills.json，按名索引）。"""
    global _BUILTIN
    if _BUILTIN is None:
        data = json.loads((TABLES_DIR / "builtin_skills.json").read_text(encoding="utf-8")) \
            if (TABLES_DIR / "builtin_skills.json").exists() else []
        _BUILTIN = {s["name"]: s for s in data} if isinstance(data, list) else {}
    return _BUILTIN


def builtin_def(name: str) -> Optional[Dict[str, Any]]:
    return builtin_skills().get(name)


def generate(name: str, skill_type: str = "active") -> Dict[str, Any]:
    """按技能名生成效果定义：自定义 > 内置 > 效果模板库（确定性）。"""
    cdef = custom_def(name)
    if cdef:
        return {
            "category": cdef.get("category", "damage"),
            "target": cdef.get("target", "enemy_single"),
            "trigger": cdef.get("trigger", "attack"),
            "chance": cdef.get("chance", 0.35),
            "cooldown": cdef.get("cooldown", 0),
            "scale": cdef.get("scale", {"attr": "force"}),
            "formula": cdef.get("formula", {}),
            "effects": cdef.get("effects", []),
            "desc": cdef.get("desc", ""),
            "custom": True,
        }
    bdef = builtin_def(name)
    if bdef:
        out = {k: bdef.get(k) for k in ("target", "trigger", "chance", "cooldown", "scale",
                                        "formula", "effects", "desc")}
        out["category"] = (bdef.get("school") or "damage")
        out["builtin"] = True
        return out
    lib = _effects()
    cat = classify(name, skill_type)
    pool = [e for e in lib if e.get("category") == cat] or lib
    if not pool:
        return {"category": cat, "target": "enemy_single", "trigger": "attack",
                "chance": 0.35, "cooldown": 0, "scale": {"attr": "force"},
                "effects": [{"type": "dmg_physical", "params": {"coef": 1.0, "hits": 1}}],
                "desc": f"{name}（默认效果）。"}
    tpl = pool[_h(name) % len(pool)]
    out = {
        "category": tpl.get("category"),
        "target": tpl.get("target"),
        "trigger": tpl.get("trigger"),
        "chance": tpl.get("chance", 0.35),
        "cooldown": tpl.get("cooldown", 0),
        "scale": tpl.get("scale", {"attr": "force"}),
        "effects": tpl.get("effects", []),
        "desc": tpl.get("desc", ""),
    }
    if skill_type == "passive":
        out["trigger"] = "always"
        out["chance"] = 1.0
    return out


def reload() -> None:
    global _CACHE, _CUSTOM, _BUILTIN
    _CACHE = None
    _CUSTOM = None
    _BUILTIN = None
