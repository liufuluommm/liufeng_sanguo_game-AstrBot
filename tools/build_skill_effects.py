"""生成 350 个技能效果模板 -> tables/skill_effects.json。

类别分布：伤害 80 / 控制 50 / 增益 70 / 减益 60 / 治疗 40 / 特殊 50。
每项：{id,name,category,target,trigger,chance,cooldown,scale,effects,desc}
"""
from __future__ import annotations

import json
from pathlib import Path

TABLES = Path(__file__).resolve().parent.parent / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

P = ["烈", "破", "斩", "崩", "穿", "疾", "狂", "绝", "重", "青"]
S = ["击", "斩", "刃", "刺", "劈", "爆", "袭", "军", "阵", "命"]


def combos(pre, suf, n):
    out = []
    for a in pre:
        for b in suf:
            out.append(a + b)
    # 去重后取前 n
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
        if len(res) >= n:
            break
    return res


entries = []
counter = {"n": 0}


def add(name, category, target, trigger, scale_attr, effects, desc,
        chance=0.35, cooldown=0):
    counter["n"] += 1
    entries.append({
        "id": f"se_{counter['n']:03d}",
        "name": name,
        "category": category,
        "target": target,
        "trigger": trigger,
        "chance": chance,
        "cooldown": cooldown,
        "scale": {"attr": scale_attr},
        "effects": effects,
        "desc": desc,
    })


# ---- 伤害 80 ----
dmg_names = combos(P, S, 80)
for i, nm in enumerate(dmg_names):
    kind = ["physical", "magic", "true"][i % 3]
    group = i % 3 == 1
    attr = {"physical": "force", "magic": "intellect", "true": "speed"}[kind]
    target = "enemy_all" if group else "enemy_single"
    coef = round(0.9 + (i % 8) * 0.15, 2)
    hits = 2 if i % 7 == 0 else 1
    add(nm, "damage", target, "attack", attr,
        [{"type": f"dmg_{kind}", "params": {"coef": coef, "hits": hits}}],
        f"对{'全体' if group else '单体'}敌人造成{'兵刃' if kind=='physical' else '谋略' if kind=='magic' else '真实'}伤害。")

# ---- 控制 50 ----
ctl_names = combos(["定", "封", "慑", "冻", "缚", "乱", "迷", "嘲", "械", "禁"], S, 50)
kinds = ["stun", "silence", "freeze", "taunt", "disarm"]
for i, nm in enumerate(ctl_names):
    kind = kinds[i % len(kinds)]
    r = 1 + (i % 2)
    add(nm, "control", "enemy_single", "attack", "charisma",
        [{"type": "control", "params": {"kind": kind, "rounds": r, "chance": round(0.3 + (i % 4) * 0.05, 2)}}],
        f"有概率使目标进入{ {'stun':'眩晕','silence':'沉默','freeze':'冻结','taunt':'嘲讽','disarm':'缴械'}[kind] }状态 {r} 回合。")

# ---- 增益 70 ----
buff_attrs = ["atk", "def", "hp", "speed", "crit", "dodge", "lifesteal", "shield", "reflect", "tenacity"]
buff_names = combos(["振", "励", "威", "勇", "固", "守", "疾", "巧", "韧", "锐"], ["军", "身", "阵", "心", "势", "威", "勇", "谋", "守", "烈"], 70)
for i, nm in enumerate(buff_names):
    attr = buff_attrs[i % len(buff_attrs)]
    r = 2 + (i % 3)
    v = round(0.1 + (i % 5) * 0.05, 2)
    add(nm, "buff", "ally_all" if i % 4 == 0 else "self", "round_start", "charisma",
        [{"type": "buff", "params": {"attr": attr, "value": v, "rounds": r}}],
        f"提升己方{attr}（{int(v*100)}%）持续 {r} 回合。",
        chance=1.0, cooldown=3)

# ---- 减益 60 ----
deb_names = combos(["弱", "钝", "滞", "毒", "灼", "血", "破", "怯", "衰", "乱"], ["身", "甲", "速", "心", "势", "魂", "武", "谋", "阵", "军"], 60)
deb_attrs = ["atk", "def", "speed", "armor"]
dots = ["poison", "burn", "bleed"]
for i, nm in enumerate(deb_names):
    if i % 3 == 2:
        kind = dots[i % 3]
        v = round(0.05 + (i % 5) * 0.01, 3)
        add(nm, "debuff", "enemy_single", "attack", "eloquence",
            [{"type": "dot", "params": {"kind": kind, "value": v, "rounds": 3}}],
            f"使目标持续受到{ {'poison':'中毒','burn':'灼烧','bleed':'流血'}[kind] }伤害 3 回合。")
    else:
        attr = deb_attrs[i % len(deb_attrs)]
        v = round(0.1 + (i % 4) * 0.05, 2)
        r = 2 + (i % 2)
        add(nm, "debuff", "enemy_all" if i % 5 == 0 else "enemy_single", "attack", "eloquence",
            [{"type": "debuff", "params": {"attr": attr, "value": v, "rounds": r}}],
            f"降低敌方{attr}（{int(v*100)}%）持续 {r} 回合。")

# ---- 治疗 40 ----
heal_names = combos(["疗", "愈", "济", "养", "复", "苏", "净", "护", "生", "援"], ["心", "军", "体", "魂", "阵", "阵", "生", "命", "盾", "援"], 40)
for i, nm in enumerate(heal_names):
    if i % 5 == 0:
        add(nm, "heal", "ally_all", "attack", "charisma",
            [{"type": "regen", "params": {"value": 0.05 + (i % 3) * 0.01, "rounds": 3}}],
            "为友军附加持续回复。")
    elif i % 5 == 1:
        add(nm, "heal", "ally_single", "attack", "intellect",
            [{"type": "cleanse", "params": {}}, {"type": "heal", "params": {"coef": 1.0}}],
            "净化一名友军并治疗。")
    elif i % 5 == 2:
        add(nm, "heal", "ally_single", "on_kill", "charisma",
            [{"type": "revive", "params": {"hp": 0.3}}],
            "友军阵亡时概率复活（30% 生命）。", chance=0.35)
    else:
        add(nm, "heal", "ally_single", "attack", "intellect",
            [{"type": "heal", "params": {"coef": round(0.8 + (i % 4) * 0.2, 2)}}],
            "治疗一名友军。")

# ---- 特殊 50 ----
sp_names = combos(["连", "追", "反", "斩", "唤", "骁", "巧", "势", "袭", "御"], ["击", "锋", "势", "阵", "军", "心", "技", "命", "威", "烈"], 50)
sp_types = ["combo", "pursuit", "counter", "execute", "summon"]
for i, nm in enumerate(sp_names):
    t = sp_types[i % len(sp_types)]
    if t == "combo":
        eff = [{"type": "combo", "params": {"chance": round(0.15 + (i % 4) * 0.05, 2)}}]
        d = "普攻后有概率再次攻击。"
    elif t == "pursuit":
        eff = [{"type": "pursuit", "params": {"coef": 0.8}}]
        d = "击杀后追击下一个敌人。"
    elif t == "counter":
        eff = [{"type": "counter", "params": {"coef": 0.7}}]
        d = "受到攻击时概率反击。"
    elif t == "execute":
        eff = [{"type": "execute", "params": {"threshold": 0.25}}]
        d = "对生命低于 25% 的敌人伤害提升/斩杀。"
    else:
        eff = [{"type": "summon", "params": {"count": 1, "hp": 0.2}}]
        d = "召唤援军助战。"
    add(nm, "special", "enemy_single", "attack", "intellect", eff, d, chance=0.3)

assert len(entries) == 350, len(entries)
(TABLES / "skill_effects.json").write_text(
    json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
print("skill_effects.json:", len(entries))
from collections import Counter
print(Counter(e["category"] for e in entries))
