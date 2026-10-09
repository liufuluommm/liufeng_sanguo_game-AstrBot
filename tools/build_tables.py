"""生成三国武将 / 技能 / 羁绊数据表。

运行：python tools/build_tables.py
输出：tables/generals_historical.json、generals_obscure.json、
      generals_fictional.json、skills.json、bonds.json
"""

from __future__ import annotations

import json
import random
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 角色 -> SSR 基准多维能力
# 维度顺序：(武力 force, 智力 intellect, 体力 vitality, 魅力 charisma, 口才 eloquence, 速度 speed)
# ---------------------------------------------------------------------------
ROLE_BASE = {
    "w": (98, 52, 88, 58, 40, 82),   # 猛将
    "s": (55, 98, 62, 72, 88, 70),   # 谋士
    "l": (72, 80, 78, 94, 90, 66),   # 君主
    "b": (84, 84, 82, 80, 78, 80),   # 均衡
}
RARITY_SCALE = {"ssr": 1.00, "sr": 0.90, "r": 0.82, "n": 0.74}
ATTR_KEYS = ["force", "intellect", "vitality", "charisma", "eloquence", "speed"]
# 历史名将史实化多维数值（覆盖角色模板）
OVERRIDES6 = {
    # 魏
    "曹操": (78, 96, 82, 97, 95, 72), "司马懿": (60, 97, 78, 88, 90, 66),
    "郭嘉": (34, 98, 52, 80, 92, 70), "张辽": (90, 80, 88, 78, 62, 86),
    "张郃": (88, 82, 86, 72, 58, 84), "许褚": (95, 28, 96, 50, 30, 70),
    "夏侯惇": (90, 54, 90, 60, 42, 74), "夏侯渊": (89, 60, 86, 58, 44, 88),
    "曹仁": (86, 66, 88, 66, 50, 76), "典韦": (96, 24, 98, 45, 28, 72),
    "荀彧": (40, 96, 58, 86, 88, 62), "荀攸": (38, 94, 56, 80, 86, 64),
    "庞德": (92, 56, 88, 62, 40, 80), "徐晃": (88, 74, 86, 68, 52, 80),
    "于禁": (82, 70, 84, 66, 55, 74), "曹洪": (80, 52, 86, 58, 40, 76),
    # 蜀
    "关羽": (98, 72, 92, 86, 60, 84), "赵云": (97, 76, 90, 82, 55, 90),
    "诸葛亮": (40, 100, 60, 92, 96, 60), "张飞": (98, 36, 94, 60, 30, 80),
    "马超": (96, 50, 90, 70, 45, 92), "黄忠": (93, 62, 82, 66, 50, 72),
    "姜维": (86, 90, 84, 80, 72, 82), "魏延": (90, 68, 86, 60, 44, 82),
    "庞统": (46, 97, 60, 80, 86, 62), "法正": (50, 95, 62, 78, 84, 64),
    "黄月英": (42, 96, 58, 78, 80, 70), "关平": (88, 70, 86, 70, 50, 82),
    "马岱": (86, 66, 84, 66, 48, 82), "徐庶": (52, 95, 66, 82, 88, 70),
    "王平": (78, 74, 84, 70, 58, 72),
    # 吴
    "周瑜": (70, 96, 74, 90, 88, 80), "陆逊": (64, 95, 72, 86, 90, 78),
    "孙策": (94, 74, 90, 86, 70, 92), "孙坚": (90, 72, 90, 82, 66, 86),
    "甘宁": (93, 54, 86, 60, 42, 94), "太史慈": (92, 64, 88, 66, 48, 86),
    "吕蒙": (80, 86, 80, 74, 66, 78), "鲁肃": (58, 90, 72, 86, 90, 64),
    "黄盖": (86, 72, 86, 72, 58, 76), "孙尚香": (82, 68, 84, 80, 66, 88),
    "周泰": (88, 48, 92, 56, 38, 78), "程普": (84, 72, 88, 72, 58, 74),
    "凌统": (87, 60, 86, 64, 46, 86), "韩当": (84, 66, 86, 68, 54, 80),
    # 群
    "吕布": (100, 32, 95, 55, 35, 96), "董卓": (82, 70, 86, 50, 55, 60),
    "张角": (46, 93, 66, 85, 90, 58), "华雄": (90, 40, 88, 48, 32, 78),
    "颜良": (91, 44, 88, 52, 34, 80), "文丑": (90, 42, 88, 50, 32, 82),
    "高顺": (88, 66, 88, 62, 46, 74), "陈宫": (48, 92, 64, 78, 86, 62),
    "公孙瓒": (85, 62, 84, 70, 60, 88),
}
ROLE_TROOP = {
    "w": ["cavalry", "spear"],
    "s": ["archer"],
    "l": ["infantry"],
    "b": ["cavalry", "infantry", "spear", "archer"],
}
ROLE_ACTIVE = {
    "w": ["力战", "破军", "突袭", "斩将", "横扫", "陷阵"],
    "s": ["火计", "锦囊", "连环", "妙算", "扇舞", "筹谋"],
    "l": ["号令", "援军", "激励", "威压", "统御", "御敌"],
    "b": ["奇策", "应变", "先守", "疾风", "均衡"],
}
ROLE_PASSIVE = {
    "w": ["骁勇", "铁骨", "武略", "悍勇"],
    "s": ["洞察", "神算", "明哲", "洞烛"],
    "l": ["威望", "仁德", "御众", "守成"],
    "b": ["强运", "韧性", "稳健"],
}
FACTION_TITLE = {
    "wei": "魏", "shu": "蜀", "wu": "吴", "qun": "群",
}

def h(*parts: str) -> int:
    return zlib.crc32("|".join(parts).encode("utf-8")) % 1000000


def roll_stats(name: str, role: str, rarity: str, randomize: bool = False):
    if name in OVERRIDES6:
        return OVERRIDES6[name]
    base = ROLE_BASE[role]
    scale = RARITY_SCALE[rarity]
    out = []
    for i, b in enumerate(base):
        if randomize:
            jitter = random.randint(-12, 12)
        else:
            jitter = (h(name, str(i)) % 9) - 4
        v = int(b * scale) + jitter
        out.append(max(8, min(100, v)))
    return tuple(out)


def build_general(name, faction, role, rarity, category, exclusive=False, randomize=False):
    stats = roll_stats(name, role, rarity, randomize=randomize)
    troop = ROLE_TROOP[role][h(name, "troop") % len(ROLE_TROOP[role])]
    active_name = ROLE_ACTIVE[role][h(name, "act") % len(ROLE_ACTIVE[role])]
    passive_name = ROLE_PASSIVE[role][h(name, "pasv") % len(ROLE_PASSIVE[role])]
    skill = {
        "active": f"sk_act_{name}",
        "passive": f"sk_pas_{name}",
    }
    g = {
        "id": name,
        "name": name,
        "faction": faction,
        "rarity": rarity,
        "troop": troop,
        "title": "",
        "category": category,
        "desc": f"{FACTION_TITLE.get(faction, '群')}势力·{'专属' if exclusive else '通用'}技能武将。",
        "skill": skill,
        "_active_name": active_name,
        "_passive_name": passive_name,
    }
    for k, v in zip(ATTR_KEYS, stats):
        g[k] = v
    return g


# ---------------------------------------------------------------------------
# 历史武将 150
# ---------------------------------------------------------------------------
HISTORICAL = {
    "ssr": [
        "曹操|wei|l", "司马懿|wei|s", "郭嘉|wei|s", "张辽|wei|w", "张郃|wei|w", "许褚|wei|w",
        "关羽|shu|w", "赵云|shu|w", "诸葛亮|shu|s", "张飞|shu|w", "马超|shu|w", "黄忠|shu|w",
        "周瑜|wu|s", "陆逊|wu|s", "孙策|wu|w", "孙坚|wu|w", "甘宁|wu|w",
        "吕布|qun|w", "董卓|qun|l", "张角|qun|s",
    ],
    "sr": [
        "夏侯惇|wei|w", "夏侯渊|wei|w", "曹仁|wei|w", "典韦|wei|w", "荀彧|wei|s",
        "荀攸|wei|s", "庞德|wei|w", "徐晃|wei|w", "于禁|wei|w", "曹洪|wei|w",
        "姜维|shu|b", "魏延|shu|w", "庞统|shu|s", "法正|shu|s", "黄月英|shu|s",
        "关平|shu|w", "马岱|shu|w", "徐庶|shu|s", "王平|shu|l",
        "太史慈|wu|w", "吕蒙|wu|b", "鲁肃|wu|s", "黄盖|wu|w", "孙尚香|wu|w",
        "周泰|wu|w", "程普|wu|l", "凌统|wu|w", "韩当|wu|w",
        "华雄|qun|w", "颜良|qun|w", "文丑|qun|w", "高顺|qun|w", "陈宫|qun|s", "公孙瓒|qun|w",
    ],
    "r": [
        "乐进|wei|w", "李典|wei|l", "程昱|wei|s", "满宠|wei|s", "文聘|wei|w",
        "曹纯|wei|w", "邓艾|wei|l", "钟会|wei|s", "蔡瑁|wei|l", "曹丕|wei|l",
        "曹彰|wei|w", "郭淮|wei|l",
        "关兴|shu|w", "张苞|shu|w", "廖化|shu|w", "严颜|shu|w", "周仓|shu|w",
        "马良|shu|s", "蒋琬|shu|l", "费祎|shu|s", "黄权|shu|s", "刘封|shu|w", "糜竺|shu|l",
        "徐盛|wu|w", "丁奉|wu|w", "张昭|wu|s", "诸葛瑾|wu|s", "小乔|wu|s", "大乔|wu|s",
        "朱然|wu|w", "朱桓|wu|w", "全琮|wu|w", "潘璋|wu|w", "马忠|wu|w", "顾雍|wu|s",
        "袁术|qun|l", "刘表|qun|l", "刘璋|qun|l", "张绣|qun|w", "马腾|qun|w",
        "韩遂|qun|w", "刘繇|qun|l", "张鲁|qun|l", "刘岱|qun|l", "孔融|qun|s", "陶谦|qun|l",
    ],
    "n": [
        "曹植|wei|s", "夏侯尚|wei|w", "郝昭|wei|w", "王双|wei|w", "许攸|wei|s",
        "曹真|wei|l", "曹休|wei|w", "陈群|wei|s", "司马朗|wei|s", "卞夫人|wei|s",
        "毛玠|wei|s", "李通|wei|w",
        "简雍|shu|s", "孙乾|shu|s", "马谡|shu|s", "刘巴|shu|s", "董允|shu|s",
        "伊籍|shu|s", "向朗|shu|s", "张翼|shu|w", "张嶷|shu|w", "傅肜|shu|w",
        "关索|shu|w", "鲍三娘|shu|w", "黄皓|shu|s",
        "陆抗|wu|l", "步练师|wu|s", "朱治|wu|s", "吕范|wu|s", "贺齐|wu|w",
        "董袭|wu|w", "陈武|wu|w", "蒋钦|wu|w", "孙翊|wu|w", "吴国太|wu|s",
        "徐氏|wu|s", "孙鲁育|wu|s", "朱据|wu|w",
        "张任|qun|w", "李儒|qun|s", "李傕|qun|w", "郭汜|qun|w", "樊稠|qun|w",
        "张济|qun|w", "纪灵|qun|w", "淳于琼|qun|w", "审配|qun|s", "逢纪|qun|s",
        "田丰|qun|s", "沮授|qun|s",
    ],
}

# ---------------------------------------------------------------------------
# 冷门武将 100 (R 30 / N 70)
# ---------------------------------------------------------------------------
OBSCURE = {
    "r": [
        "陈到|shu|w", "霍峻|shu|w", "张燕|qun|w", "臧霸|wei|w", "田豫|wei|l",
        "牵招|wei|w", "贾逵|wei|s", "刘晔|wei|s", "蒋济|wei|s", "董昭|wei|s",
        "孙礼|wei|w", "王凌|wei|l", "毌丘俭|wei|l", "文钦|wei|w", "诸葛诞|wei|l",
        "夏侯霸|wei|w", "罗宪|shu|w", "霍弋|shu|w", "句扶|shu|w", "杨仪|shu|s",
        "王嗣|shu|w", "张南|shu|w", "冯习|shu|w", "吕凯|shu|s", "李恢|shu|l",
        "留赞|wu|w", "吕岱|wu|l", "陶濬|wu|w", "钟离牧|wu|w", "吾粲|wu|s",
    ],
    "n": [
        "乐綝|wei|w", "石苞|wei|s", "陈泰|wei|l", "王基|wei|l", "州泰|wei|w",
        "邓忠|wei|w", "师纂|wei|w", "胡烈|wei|w", "胡渊|wei|w", "田续|wei|w",
        "卫瓘|wei|s", "羊祜|wei|l", "杜预|wei|s", "王濬|wei|l", "唐咨|wei|w",
        "诸葛绪|wei|w", "王颀|wei|w", "丘本|wei|w", "荀恺|wei|w", "李辅|wei|w",
        "张虎|wei|w", "乐方|wei|w", "蔡和|wei|w", "蔡中|wei|w", "蔡勋|wei|w",
        "关统|shu|w", "关彝|shu|w", "赵广|shu|w", "赵统|shu|w", "张绍|shu|s",
        "诸葛瞻|shu|l", "诸葛尚|shu|w", "黄崇|shu|w", "李球|shu|w", "张遵|shu|w",
        "董厥|shu|s", "樊建|shu|s", "胡济|shu|w", "阎宇|shu|w", "马勖|shu|w",
        "孙峻|wu|l", "孙綝|wu|l", "孙休|wu|l", "孙皓|wu|l", "张悌|wu|l",
        "沈莹|wu|w", "孙震|wu|w", "陆凯|wu|s", "陆胤|wu|s", "范疆|wu|w",
        "朱异|wu|w", "丁封|wu|w", "孙冀|wu|w", "滕胤|wu|s", "吕据|wu|w",
        "留平|wu|w", "陆景|wu|w", "盛曼|wu|w", "施绩|wu|l", "徐详|wu|s",
        "袁谭|qun|w", "袁尚|qun|w", "袁熙|qun|w", "高干|qun|w", "郭图|qun|s",
        "辛评|qun|s", "苏由|qun|w", "岑璧|qun|w", "张卫|qun|w", "杨昂|qun|w",
    ],
}

# ---------------------------------------------------------------------------
# 架空武将 120 (SSR 10 / SR 25 / R 40 / N 45)
# ---------------------------------------------------------------------------
FICTIONAL_SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
FICTIONAL_GIVEN = [
    "凌云", "破阵", "无双", "孤城", "青锋", "寒江", "天罡", "逐日", "惊雷", "踏雪",
    "焚天", "裂地", "追风", "断岳", "星河", "墨羽", "苍岚", "赤霄", "玄冰", "紫电",
    "枪神", "刀圣", "剑仙", "策士", "鬼谋", "虎啸", "龙吟", "鹰扬", "豹骑", "狼牙",
    "铁衣", "银甲", "锦帆", "白袍", "青囊", "北望", "南征", "东渡", "西凉", "中军",
]
FICTIONAL_SPEC = {
    "ssr": 10, "sr": 25, "r": 40, "n": 45,
}
ROLE_WEIGHT_FICTIONAL = ["w", "w", "w", "s", "s", "l", "b"]
FACTIONS_FICTIONAL = ["wei", "shu", "wu", "qun"]


def gen_fictional():
    used = set()
    out = {r: [] for r in FICTIONAL_SPEC}
    idx = 0
    for rarity, count in FICTIONAL_SPEC.items():
        made = 0
        while made < count:
            idx += 1
            sn = FICTIONAL_SURNAMES[idx % len(FICTIONAL_SURNAMES)]
            gn = FICTIONAL_GIVEN[(idx * 7) % len(FICTIONAL_GIVEN)]
            name = f"{sn}{gn}"
            if name in used:
                name = f"{name}{idx % 10}"
            if name in used:
                continue
            used.add(name)
            role = ROLE_WEIGHT_FICTIONAL[(idx * 3) % len(ROLE_WEIGHT_FICTIONAL)]
            faction = FACTIONS_FICTIONAL[(idx * 5) % len(FACTIONS_FICTIONAL)]
            out[rarity].append(f"{name}|{faction}|{role}")
            made += 1
    return out


def parse(entries):
    result = []
    for raw in entries:
        parts = raw.split("|")
        name, faction, role = parts[0], parts[1], parts[2]
        result.append((name, faction, role))
    return result


def main():
    random.seed(20260101)
    skills = {}
    all_generals = []

    rules = [
        ("historical", HISTORICAL, True),
        ("obscure", OBSCURE, False),
    ]
    for category, table, exclusive in rules:
        entries = []
        for rarity, raw_list in table.items():
            for name, faction, role in parse(raw_list):
                g = build_general(name, faction, role, rarity, category, exclusive)
                entries.append(g)
                all_generals.append(g)
                for stype, key in (("active", "active"), ("passive", "passive")):
                    sid = g["skill"][stype]
                    skills[sid] = {
                        "id": sid,
                        "name": g.pop("_active_name" if stype == "active" else "_passive_name"),
                        "type": stype,
                        "owner": name,
                        "rarity": "exclusive" if (exclusive and rarity in ("ssr", "sr")) else "generic",
                        "desc": f"{name}的{stype}技能。",
                    }
        out = {r: [] for r in ("ssr", "sr", "r", "n")}
        for g in entries:
            out[g["rarity"]].append(g)
        path = TABLES / f"generals_{category}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        total = sum(len(v) for v in out.values())
        print(f"{path.name}: {total}")

    fictions = gen_fictional()
    f_entries = {r: [] for r in ("ssr", "sr", "r", "n")}
    for rarity, raw_list in fictions.items():
        for name, faction, role in parse(raw_list):
            g = build_general(name, faction, role, rarity, "fictional", rarity in ("ssr", "sr"), randomize=True)
            all_generals.append(g)
            for stype in ("active", "passive"):
                sid = g["skill"][stype]
                skills[sid] = {
                    "id": sid,
                    "name": g.pop("_active_name" if stype == "active" else "_passive_name"),
                    "type": stype,
                    "owner": name,
                    "rarity": "exclusive" if rarity in ("ssr", "sr") else "generic",
                    "desc": f"{name}的{stype}技能。",
                }
            f_entries[rarity].append(g)
    fpath = TABLES / "generals_fictional.json"
    fpath.write_text(json.dumps(f_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{fpath.name}: {sum(len(v) for v in f_entries.values())}")

    # 兜底：清理残留私有字段
    for p in TABLES.glob("generals_*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        for lst in data.values():
            for g in lst:
                for k in ("_active_name", "_passive_name"):
                    g.pop(k, None)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 技能表
    (TABLES / "skills.json").write_text(
        json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"skills.json: {len(skills)}")

    # 羁绊表
    bond_defs = [
        ("五虎上将", ["关羽", "张飞", "赵云", "马超", "黄忠"], 0.08, "全队战力+8%"),
        ("桃园结义", ["刘备", "关羽", "张飞"], 0.05, "全队战力+5%"),
        ("卧龙凤雏", ["诸葛亮", "庞统"], 0.06, "智谋类战力+6%"),
        ("五子良将", ["张辽", "乐进", "于禁", "张郃", "徐晃"], 0.06, "全队战力+6%"),
        ("八虎骑", ["夏侯惇", "夏侯渊", "曹仁", "曹洪", "曹纯", "曹真", "曹休"], 0.05, "全队战力+5%"),
        ("江东双璧", ["孙策", "周瑜"], 0.05, "全队战力+5%"),
        ("十二虎臣", ["程普", "黄盖", "韩当", "周泰", "陈武", "董袭", "甘宁", "凌统", "徐盛", "潘璋", "丁奉"], 0.06, "全队战力+6%"),
        ("曹魏谋士", ["荀彧", "荀攸", "郭嘉", "程昱", "贾诩"], 0.05, "智谋类战力+5%"),
        ("西凉铁骑", ["马超", "马岱", "庞德", "马腾", "韩遂"], 0.05, "骑兵战力+5%"),
        ("虎痴恶来", ["许褚", "典韦"], 0.04, "全队战力+4%"),
        ("河北双雄", ["颜良", "文丑"], 0.04, "全队战力+4%"),
        ("顾曲周郎", ["周瑜", "小乔"], 0.03, "全队战力+3%"),
    ]
    name_set = {g["name"] for g in all_generals}
    bonds = []
    for i, (bname, members, bonus, desc) in enumerate(bond_defs):
        valid = [m for m in members if m in name_set]
        if len(valid) < 2:
            continue
        bonds.append({
            "id": f"bond_{i}",
            "name": bname,
            "members": valid,
            "bonus": bonus,
            "desc": desc,
        })
    (TABLES / "bonds.json").write_text(
        json.dumps(bonds, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"bonds.json: {len(bonds)}")
    print(f"总武将: {len(all_generals)}")


if __name__ == "__main__":
    main()
