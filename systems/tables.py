"""静态数据表加载与查询。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import storage

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
RARITIES = ("ssr", "sr", "r", "n")


def _load(name: str, default: Any) -> Any:
    path = TABLES_DIR / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def load_custom_generals() -> Dict[str, Dict]:
    """管理员自定义武将，存于插件数据目录。"""
    try:
        path = storage.data_root() / "generals_custom.json"
    except Exception:  # noqa: BLE001
        return {}
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


class Tables:
    def __init__(self) -> None:
        self.historical: Dict[str, List[Dict]] = _load(
            "generals_historical.json", {"ssr": [], "sr": [], "r": [], "n": []}
        )
        self.obscure: Dict[str, List[Dict]] = _load(
            "generals_obscure.json", {"ssr": [], "sr": [], "r": [], "n": []}
        )
        self.fictional: Dict[str, List[Dict]] = _load(
            "generals_fictional.json", {"ssr": [], "sr": [], "r": [], "n": []}
        )
        # 管理员自定义武将：按稀有度归入 custom 表
        self.custom: Dict[str, List[Dict]] = {r: [] for r in RARITIES}
        for name, g in load_custom_generals().items():
            g = dict(g)
            g.setdefault("name", name)
            g.setdefault("category", "custom")
            rarity = g.get("rarity", "n")
            if rarity not in RARITIES:
                rarity = "n"
            g["rarity"] = rarity
            self.custom[rarity].append(g)

        self.skills: Dict[str, Dict] = _load("skills.json", {})
        self.skill_effects: List[Dict] = _load("skill_effects.json", [])
        # 按技能名生成效果并合并（确定性）
        from . import skillgen

        skillgen.reload()
        self._skills_full: Dict[str, Dict] = {}
        for sid, sk in self.skills.items():
            merged = dict(sk)
            merged.update(skillgen.generate(sk.get("name", ""), sk.get("type", "active")))
            self._skills_full[sid] = merged
        self.bonds: List[Dict] = _load("bonds.json", [])
        self.equipments: Dict[str, List[Dict]] = _load("equipments.json", {})
        # 合并管理台自定义装备蓝图（数据目录 equipments_custom.json）
        try:
            cpath = storage.data_root() / "equipments_custom.json"
            custom_eq = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else {}
        except (json.JSONDecodeError, OSError):
            custom_eq = {}
        if isinstance(custom_eq, dict):
            for item in custom_eq.values():
                if isinstance(item, dict) and item.get("id"):
                    slot = item.get("slot", "weapon")
                    self.equipments.setdefault(slot, []).append(item)
        self._equip_by_id: Dict[str, Dict] = {}
        for _slot, items in self.equipments.items():
            for item in items:
                self._equip_by_id[item["id"]] = item

        self._by_name: Dict[str, Dict] = {}
        for category, table in (
            ("historical", self.historical),
            ("obscure", self.obscure),
            ("fictional", self.fictional),
            ("custom", self.custom),
        ):
            for rarity, generals in table.items():
                for g in generals:
                    g = dict(g)
                    g["rarity"] = rarity
                    g.setdefault("category", category)
                    self._by_name[g["name"]] = g

    # -- 查询 -------------------------------------------------------------
    def get(self, name: str) -> Optional[Dict]:
        return self._by_name.get(name)

    def all_names(self) -> List[str]:
        return list(self._by_name.keys())

    def by_rarity(self, rarity: str) -> List[Dict]:
        """全部类目下指定稀有度的武将（用于兑换池）。"""
        result: List[Dict] = []
        for table in (self.historical, self.obscure, self.custom):
            result.extend(table.get(rarity, []))
        return result

    def by_rarity_category(self, category: str, rarity: str) -> List[Dict]:
        table = {
            "historical": self.historical,
            "obscure": self.obscure,
            "fictional": self.fictional,
            "custom": self.custom,
        }.get(category, {})
        return table.get(rarity, [])

    def skill(self, skill_id: str) -> Optional[Dict]:
        return self._skills_full.get(skill_id) or self.skills.get(skill_id)

    def bonds_for(self, names: List[str]) -> List[Dict]:
        owned = set(names)
        return [b for b in self.bonds if sum(1 for m in b["members"] if m in owned) >= 2]

    def equipment(self, eq_id: str) -> Optional[Dict]:
        return self._equip_by_id.get(eq_id)

    def equipment_by_rarity(self, rarity: str) -> List[Dict]:
        return [e for e in self._equip_by_id.values() if e["rarity"] == rarity]

    def all_equipment(self) -> List[Dict]:
        return list(self._equip_by_id.values())


_TABLES: Optional[Tables] = None


def tables() -> Tables:
    global _TABLES
    if _TABLES is None:
        _TABLES = Tables()
    return _TABLES


def reload_tables() -> Tables:
    global _TABLES
    _TABLES = Tables()
    return _TABLES
