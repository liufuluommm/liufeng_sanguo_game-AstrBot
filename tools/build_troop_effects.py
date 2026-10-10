"""生成 100 个「携带兵种效果」模板 -> tables/troop_effects.json。

每项：{id, name, desc, tags, items}
items 由三类原子组成：
  - stat    {type:"stat",    attr:枚举, value:数值}   属性加成（全场）
  - mechanic{type:"mechanic",key:枚举,  value:数值}   特殊机制
  - opening {type:"opening", atom:{type,params}}      开局对自身释放的效果原子

名字随机化 / 架空化（专用词库 + 固定 seed，保证 100 个唯一）。
分布：属性 68 / 特殊机制 14 / 开局 18。
"""
from __future__ import annotations

import json
from pathlib import Path

TABLES = Path(__file__).resolve().parent.parent / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

PRE = ["玄", "铁", "苍", "赤", "青", "烈", "疾", "镇", "御", "狮", "虎", "狼",
       "鹰", "龙", "幽", "寒", "金", "银", "霜", "雷", "风", "山", "锦", "白"]
MID = ["甲", "壁", "锋", "骑", "弩", "盾", "阵", "军", "卫", "啸", "牙", "翼",
       "翎", "铠", "旌", "戈", "戟", "辕", "辔", "旗"]

STAT_POOL = [
    ("atk", 0.06, 0.18),
    ("def", 0.08, 0.25),
    ("mag_def", 0.08, 0.25),
    ("hp", 0.08, 0.28),
    ("speed", 0.05, 0.20),
    ("crit", 0.04, 0.12),
    ("crit_dmg", 0.10, 0.40),
    ("dodge", 0.03, 0.10),
    ("lifesteal", 0.05, 0.15),
    ("spellvamp", 0.05, 0.15),
    ("reduction", 0.03, 0.12),
    ("tenacity", 0.05, 0.20),
    ("reflect", 0.05, 0.15),
    ("cdr", 0.05, 0.20),
    ("atkspeed", 0.05, 0.18),
    ("pen_flat", 20, 60),
    ("mana", 10, 40),
]
STAT_LABEL = {
    "atk": "攻击", "def": "物防", "mag_def": "法防", "hp": "生命", "speed": "速度",
    "crit": "暴击", "crit_dmg": "暴伤", "dodge": "闪避", "lifesteal": "吸血",
    "spellvamp": "法术吸血", "reduction": "免伤", "tenacity": "韧性", "reflect": "反伤",
    "cdr": "冷却缩减", "atkspeed": "攻速", "pen_flat": "固定穿透", "mana": "法力",
}

MECHANICS = [
    ("magic_vuln", "受谋略伤害提升"),
    ("extra_hit_chance", "普攻概率追加一击"),
    ("knockup_chance", "普攻概率击飞"),
    ("first_strike", "首回合先手"),
    ("low_hp_atk", "生命越低攻击越高"),
]
MECH_LABEL = dict(MECHANICS)

OPENINGS = [
    ("shield", "开局获得护盾"),
    ("regen", "开局持续回复"),
    ("buff", "开局提升属性"),
]


def gen_names(n: int):
    seen, res = set(), []
    for a in PRE:
        for b in MID:
            nm = a + b
            if nm in seen:
                continue
            seen.add(nm)
            res.append(nm)
            if len(res) >= n:
                return res
    return res


def stat_value(attr: str, lo: float, hi: float, i: int):
    if attr in ("pen_flat", "mana"):
        return int(lo + (i % 5) * ((hi - lo) / 4))
    return round(lo + (i % 5) * ((hi - lo) / 4), 3)


def main() -> None:
    names = gen_names(100)
    assert len(names) >= 100, len(names)

    entries = []
    idx = 0

    # ---- 属性 68 ----
    for k in range(68):
        attr, lo, hi = STAT_POOL[(k * 3 + k // len(STAT_POOL)) % len(STAT_POOL)]
        v1 = stat_value(attr, lo, hi, k)
        items = [{"type": "stat", "attr": attr, "value": v1}]
        # 约 1/3 附带第二条属性
        if k % 3 == 0:
            a2, lo2, hi2 = STAT_POOL[(k * 5 + 7) % len(STAT_POOL)]
            if a2 != attr:
                items.append({"type": "stat", "attr": a2, "value": stat_value(a2, lo2, hi2, k)})
        desc = "、".join(
            f"{STAT_LABEL[i['attr']]}+{int(i['value'] * 100)}%" if i["attr"] not in ("pen_flat", "mana")
            else f"{STAT_LABEL[i['attr']]}+{i['value']}"
            for i in items
        )
        idx += 1
        entries.append({
            "id": f"te_{idx:03d}", "name": names[idx - 1],
            "tags": ["stat"], "items": items, "desc": desc,
        })

    # ---- 特殊机制 14 ----
    mech_seq = (MECHANICS * 3)[:14]
    for k, (key, label) in enumerate(mech_seq):
        if key == "magic_vuln":
            val = round(0.15 + (k % 4) * 0.05, 2)
        elif key == "extra_hit_chance":
            val = round(0.20 + (k % 3) * 0.05, 2)
        elif key == "knockup_chance":
            val = round(0.15 + (k % 4) * 0.05, 2)
        elif key == "low_hp_atk":
            val = round(0.30 + (k % 4) * 0.10, 2)
        else:
            val = 1
        item = {"type": "mechanic", "key": key, "value": val}
        items = [item]
        # 部分附带属性
        if k % 2 == 1:
            a2, lo2, hi2 = STAT_POOL[(k * 4 + 2) % len(STAT_POOL)]
            items.append({"type": "stat", "attr": a2, "value": stat_value(a2, lo2, hi2, k)})
        extra = "、" + f"{STAT_LABEL[a2]}+{int(items[-1]['value'] * 100)}%" if len(items) > 1 and items[-1]["attr"] not in ("pen_flat", "mana") else ""
        idx += 1
        entries.append({
            "id": f"te_{idx:03d}", "name": names[idx - 1],
            "tags": ["mechanic"], "items": items, "desc": label + extra,
        })

    # ---- 开局 18 ----
    for k in range(18):
        kind, label = OPENINGS[k % len(OPENINGS)]
        if kind == "shield":
            atom = {"type": "shield", "params": {"value": round(0.1 + (k % 4) * 0.05, 2), "rounds": 2}}
            d = f"开局获得 {int(atom['params']['value'] * 100)}% 生命护盾。"
        elif kind == "regen":
            atom = {"type": "regen", "params": {"value": round(0.04 + (k % 3) * 0.02, 3), "rounds": 3}}
            d = f"开局持续回复（每回合 {int(atom['params']['value'] * 100)}% 生命，3 回合）。"
        else:
            a2, lo2, hi2 = STAT_POOL[(k * 2) % len(STAT_POOL)]
            val = stat_value(a2, lo2, hi2, k)
            atom = {"type": "buff", "params": {"attr": a2, "value": val, "rounds": 2}}
            d = f"开局提升{STAT_LABEL[a2]}（{int(val * 100)}%，2 回合）。"
        idx += 1
        entries.append({
            "id": f"te_{idx:03d}", "name": names[idx - 1],
            "tags": ["opening"], "items": [{"type": "opening", "atom": atom}], "desc": d,
        })

    assert len(entries) == 100, len(entries)
    assert len({e["name"] for e in entries}) == 100
    (TABLES / "troop_effects.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    print("troop_effects.json:", len(entries), Counter(t for e in entries for t in e["tags"]))


if __name__ == "__main__":
    main()
