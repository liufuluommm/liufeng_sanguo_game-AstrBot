"""兵种系统单元测试：兵种库 / 兵种效果库 / 战斗附带效果 / 数据与后台。运行：pytest"""

import random

import pytest

from liufeng_sanguo_game.core import storage
from liufeng_sanguo_game.systems import gacha, generals_admin, troops, troops_admin
from liufeng_sanguo_game.systems import battle
from liufeng_sanguo_game.systems import player as pm


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    storage.set_data_root(tmp_path)
    troops.reload()
    yield
    storage.set_data_root(None)
    troops.reload()


def _entry(name, troop, **attrs):
    info = {"name": name, "troop": troop, "force": 80, "intellect": 70, "vitality": 80,
            "charisma": 70, "eloquence": 60, "speed": 70}
    info.update(attrs)
    return [{"name": name, "info": info, "level": 1, "star": 1}]


def test_builtin_troops_and_tiers():
    ts = troops.all_troops()
    assert len(ts) == 16
    by = troops.by_tier()
    assert len(by["basic"]) == 4 and len(by["elite"]) == 4 and len(by["special"]) == 8
    assert set(troops.basic_ids()) == {"infantry", "cavalry", "archer", "spear"}
    assert troops.label("hubaoqi") == "虎豹骑"
    assert troops.label("not_exist") == ""


def test_troop_effect_library():
    lib = troops.effect_library()
    assert len(lib) == 100
    assert len({e["name"] for e in lib}) == 100
    assert all(e.get("items") for e in lib)
    tags = {t for e in lib for t in e.get("tags", [])}
    assert {"stat", "mechanic", "opening"} <= tags


def test_merge_bonus_opening_mechanic():
    teng = troops.merge(troops.get("tengjia"))
    assert teng["bonus"]["reduction"] == pytest.approx(0.20)
    assert teng["mechanics"].get("magic_vuln") == pytest.approx(0.30)
    baima = troops.merge(troops.get("baima"))
    assert baima["bonus"]["speed"] == pytest.approx(0.20)
    assert len(baima["opening"]) == 1


def test_random_basic():
    for _ in range(20):
        assert troops.random_basic(random.Random()) in troops.basic_ids()


def test_custom_troop_crud_and_builtin_locked():
    # 内置不可改
    res = troops_admin.save_custom_troop({"name": "步兵", "id": "infantry", "effects": []})
    assert res["ok"] is False and res["reason"] == "builtin_locked"
    # 新建自定义
    ok = troops_admin.save_custom_troop({
        "name": "青州兵", "tier": "special", "desc": "test",
        "counter": ["archer"],
        "effects": [{"name": "死战", "items": [{"type": "stat", "attr": "atk", "value": 0.2}]}],
    })
    assert ok["ok"], ok
    assert troops.id_exists("青州兵")
    assert troops.label("青州兵") == "青州兵"
    m = troops.merge(troops.get("青州兵"))
    assert m["bonus"]["atk"] == pytest.approx(0.2)
    # 删除
    assert troops_admin.delete_custom_troop("青州兵")["ok"]
    assert not troops.id_exists("青州兵")


def test_custom_effect_crud():
    ok = troops_admin.save_custom_effect({
        "name": "龙骧", "desc": "test",
        "items": [{"type": "stat", "attr": "hp", "value": 0.3},
                  {"type": "mechanic", "key": "first_strike", "value": 1}],
    })
    assert ok["ok"], ok
    names = [e["name"] for e in troops.effect_library()]
    assert "龙骧" in names
    assert troops_admin.delete_custom_effect(ok["id"])["ok"]


def test_battle_applies_troop_bonus():
    a = _entry("A", "heavy_infantry")
    b = _entry("B", "infantry")
    ca = battle.Combatant("A", a[0]["info"])
    cb = battle.Combatant("B", b[0]["info"])
    assert ca.phys_def > cb.phys_def
    res = battle.simulate(a, b, rng=random.Random(3))
    assert res["winner"] in ("a", "b", "draw")


def test_battle_tengjia_magic_vuln_and_extra_hit():
    teng = battle.Combatant("T", {"name": "T", "troop": "tengjia", "force": 60, "intellect": 60,
                                  "vitality": 80, "charisma": 50, "eloquence": 50, "speed": 50})
    assert teng.troop_mech.get("magic_vuln") == pytest.approx(0.30)
    wudang = battle.Combatant("W", {"name": "W", "troop": "wudang"})
    assert wudang.troop_mech.get("extra_hit_chance", 0) > 0


def test_battle_opening_shield():
    baier = battle.Combatant("B", {"name": "B", "troop": "baier"})
    assert baier.troop_opening


def test_historical_troop_mapping_and_fictional_random():
    from liufeng_sanguo_game.systems.tables import tables
    t = tables()
    caochun = t.get("曹纯")
    assert caochun and caochun["troop"] == "hubaoqi"
    gongsun = t.get("公孙瓒")
    assert gongsun and gongsun["troop"] == "baima"
    gaoshun = t.get("高顺")
    assert gaoshun and gaoshun["troop"] == "xianzhen"
    # 架空武将兵种均属基础
    basics = set(troops.basic_ids())
    for lst in t.fictional.values():
        for g in lst:
            assert g["troop"] in basics


def test_recruit_custom_random_basic_troop():
    p = pm.new_player("1", "测试", initial_gold=100000, dorm_capacity=15)
    res = gacha.recruit_custom(p, "自由甲", 1000, 30, 100)
    assert res["ok"], res
    assert res["troop"] in troops.basic_ids()


def test_generals_admin_accepts_special_troop():
    out = generals_admin.normalize({"name": "测试将", "troop": "hubaoqi", "force": 80})
    assert out["troop"] == "hubaoqi"
    out2 = generals_admin.normalize({"name": "测试将2", "troop": "不存在"})
    assert out2["troop"] == troops.DEFAULT_ID
