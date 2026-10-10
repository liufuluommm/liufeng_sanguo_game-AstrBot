"""道具定义与效果执行引擎（schema 驱动）。"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import storage
from ..core.utils import weighted_choice

from . import buff as buff_mod
from . import player as player_mod
from .tables import tables

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_CACHE: Optional[Dict[str, Dict]] = None


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def reload_items() -> Dict[str, Dict]:
    global _CACHE
    items: Dict[str, Dict] = {}
    items.update(_load_json(TABLES_DIR / "items.json", {}))
    items.update(load_custom())
    _CACHE = items
    return items


def all_items() -> Dict[str, Dict]:
    if _CACHE is None:
        reload_items()
    return _CACHE or {}


def get_item(item_id: str) -> Optional[Dict]:
    it = all_items().get(item_id)
    if it is not None:
        return it
    # 技能书：动态道具（skillbook_<技能名>）
    if isinstance(item_id, str) and item_id.startswith("skillbook_"):
        name = item_id[len("skillbook_"):]
        return {
            "id": item_id,
            "name": f"{name}·技能书",
            "category": "skillbook",
            "rarity": "custom",
            "desc": f"用于学习技能【{name}】。",
            "usable": False,
            "target": "general",
            "effects": [{"type": "learn_skill", "params": {"skill": name}}],
        }
    return None


def effect_schema() -> Dict[str, Any]:
    return _load_json(TABLES_DIR / "effects_schema.json", {})


def _custom_path() -> Path:
    # 持久化数据放入插件数据目录（官方规范），避免插件更新被覆盖
    return storage.data_root() / "items_custom.json"


def _legacy_custom_path() -> Path:
    return TABLES_DIR / "items_custom.json"


def load_custom() -> Dict[str, Dict]:
    p = _custom_path()
    if p.exists():
        return _load_json(p, {})
    return _load_json(_legacy_custom_path(), {})


def save_custom_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """校验并写入插件数据目录的 items_custom.json（管理台道具工坊）。"""
    item_id = str(item.get("id", "")).strip()
    if not item_id:
        return {"ok": False, "reason": "no_id"}
    schema = effect_schema()
    effects = item.get("effects", [])
    if not isinstance(effects, list) or not effects:
        return {"ok": False, "reason": "no_effects"}
    for effect in effects:
        etype = effect.get("type")
        if etype not in schema:
            return {"ok": False, "reason": f"unknown_effect:{etype}"}
    custom = _load_json(_custom_path(), {})
    custom[item_id] = item
    custom_path = _custom_path()
    tmp = custom_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(custom, ensure_ascii=False, indent=2), encoding="utf-8")
    import os

    os.replace(tmp, custom_path)
    reload_items()
    return {"ok": True, "item": item}


def delete_custom_item(item_id: str) -> Dict[str, Any]:
    custom = _load_json(_custom_path(), {})
    if item_id not in custom:
        return {"ok": False, "reason": "not_found"}
    custom.pop(item_id, None)
    _custom_path().write_text(json.dumps(custom, ensure_ascii=False, indent=2), encoding="utf-8")
    reload_items()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 效果执行
# ---------------------------------------------------------------------------

RARITIES = ["ssr", "sr", "r", "n"]


def _grant_general(player: Dict[str, Any], params: Dict, rng: random.Random) -> str:
    rarity = params.get("rarity", "sr")
    category = params.get("category", "any")
    count = max(1, int(params.get("count", 1)))
    pool: List[Dict] = []
    if category == "any":
        for r in ([rarity] if rarity != "any" else RARITIES):
            pool += tables().by_rarity(r)
    else:
        for r in ([rarity] if rarity != "any" else RARITIES):
            pool += tables().by_rarity_category(category, r)
    if not pool:
        return "（无可用武将）"
    got = []
    for _ in range(count):
        g = rng.choice(pool)
        player_mod.add_general(player, g["name"])
        got.append(g["name"])
    if got:
        try:
            from . import quest as quest_mod

            quest_mod.progress_event(player, "general_obtain", len(got))
        except Exception:  # noqa: BLE001
            pass
    return "获得武将 " + "、".join(got)


def _grant_equipment(player: Dict[str, Any], params: Dict, rng: random.Random) -> str:
    from . import equipment as equip_sys

    rarity = params.get("rarity", "r")
    count = max(1, int(params.get("count", 1)))
    pool = tables().equipment_by_rarity(rarity) if rarity != "any" else tables().all_equipment()
    if not pool:
        return "（无可用装备）"
    names = []
    for _ in range(count):
        eq = rng.choice(pool)
        player.setdefault("equipments", []).append(
            {"uid": equip_sys._new_uid(), "id": eq["id"], "level": 1, "equipped_by": None}
        )
        names.append(eq["name"])
    return "获得装备 " + "、".join(names)


def _execute_effect(player: Dict[str, Any], effect: Dict, ctx: Dict[str, Any],
                    rng: random.Random) -> Dict[str, Any]:
    etype = effect.get("type")
    params = effect.get("params", {}) or {}

    if etype == "grant_gold":
        amount = int(params.get("amount", 0))
        player_mod.add_gold(player, amount)
        return {"log": f"金币 +{amount}"}
    if etype == "grant_fragment":
        amount = int(params.get("amount", 0))
        player["fragments"] = int(player.get("fragments", 0)) + amount
        return {"log": f"碎片 +{amount}"}
    if etype == "grant_stamina":
        amount = int(params.get("amount", 0))
        player["stamina"] = int(player.get("stamina", 0)) + amount
        return {"log": f"行动力 +{amount}"}
    if etype == "grant_currency":
        cur = params.get("currency", "diamond")
        amount = int(params.get("amount", 0))
        player.setdefault("wallet", {})
        player["wallet"][cur] = int(player["wallet"].get(cur, 0)) + amount
        return {"log": f"{cur} +{amount}"}
    if etype == "grant_general":
        return {"log": _grant_general(player, params, rng)}
    if etype == "grant_equipment":
        return {"log": _grant_equipment(player, params, rng)}
    if etype in ("general_level_up", "general_star_up"):
        target = ctx.get("target")
        if not target:
            return {"log": "（需要指定武将，效果未生效）"}
        entry = player.get("generals", {}).get(target) or player.get("custom_generals", {}).get(target)
        if not entry:
            return {"log": f"（未拥有 {target}）"}
        count = max(1, int(params.get("count", 1)))
        if etype == "general_level_up":
            entry["level"] = int(entry.get("level", 1)) + count
            return {"log": f"{target} 等级 +{count}"}
        entry["star"] = int(entry.get("star", 1)) + count
        return {"log": f"{target} 星级 +{count}"}
    if etype == "buff":
        bt = params.get("buff_type", "double_gold")
        value = float(params.get("value", 2.0))
        duration = int(params.get("duration", 3600))
        buff_mod.add_buff(player, bt, value, duration)
        return {"log": f"获得增益 {buff_mod.BUFF_NAME.get(bt, bt)} x{value}"}
    if etype == "loot_box":
        entries = params.get("entries", [])
        if not entries:
            return {"log": "（空礼盒）"}
        weights = [float(e.get("weight", 1)) for e in entries]
        idx = weighted_choice([str(i) for i in range(len(entries))], weights)
        chosen = entries[int(idx)]
        nested = chosen.get("effect", {})
        sub = _execute_effect(player, nested, ctx, rng)
        return {"log": "开箱：" + sub["log"]}
    if etype == "choice_box":
        options = params.get("options", [])
        if not options:
            return {"log": "（空自选礼盒）"}
        return {"log": "请选择奖励", "pending": {"options": options, "item_id": ctx.get("item_id")}}
    return {"log": f"（未知效果 {etype}）"}


def execute_item(player: Dict[str, Any], item: Dict, target: Optional[str] = None,
                 rng: random.Random = random) -> Dict[str, Any]:
    ctx = {"target": target, "item_id": item.get("id")}
    logs: List[str] = []
    pending = None
    for effect in item.get("effects", []):
        res = _execute_effect(player, effect, ctx, rng)
        logs.append(res.get("log", ""))
        if res.get("pending"):
            pending = res["pending"]
    player_mod.save(player)
    return {"logs": logs, "pending": pending}


def resolve_choice(player: Dict[str, Any], index: int, rng: random.Random = random) -> Dict[str, Any]:
    pending = player.get("pending_choice")
    if not pending:
        return {"ok": False, "reason": "no_pending"}
    options = pending.get("options", [])
    if not (0 <= index < len(options)):
        return {"ok": False, "reason": "bad_index"}
    option = options[index]
    effect = option.get("effect", {})
    res = _execute_effect(player, effect, {"item_id": pending.get("item_id")}, rng)
    player["pending_choice"] = None
    player_mod.save(player)
    return {"ok": True, "log": res.get("log", ""), "label": option.get("label")}
