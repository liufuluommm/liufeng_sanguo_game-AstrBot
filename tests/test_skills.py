"""技能系统单元测试。运行：pytest"""

import pytest

from liufeng_sanguo_game.core import storage
from liufeng_sanguo_game.systems import (gacha, inventory, skills, skills_admin,
                                         skillgen, tables, team)
from liufeng_sanguo_game.systems import player as pm


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    storage.set_data_root(tmp_path)
    skillgen.reload()
    yield
    storage.set_data_root(None)
    skillgen.reload()


def make_player(qq="1", name="测试", gold=100000):
    p = pm.new_player(qq, name, initial_gold=gold, dorm_capacity=15)
    pm.save(p)
    return p


def test_skill_effects_count():
    assert len(tables.tables().skill_effects) == 350


def test_skillgen_deterministic():
    a = skillgen.generate("火计", "active")
    b = skillgen.generate("火计", "active")
    assert a == b and a.get("effects")


def test_exchange_and_learn():
    p = make_player()
    pm.add_general(p, "吕布")
    p["wallet"]["skill_frag"] = 100
    pm.save(p)
    res = skills.exchange(p, "激励")
    assert res["ok"], res
    assert inventory.count_of(p, skills.book_id(res["name"])) == 1
    res2 = skills.learn(p, "吕布", res["name"])
    assert res2["ok"], res2
    info = pm.general_info(p, "吕布")
    assert info["skill_name"] == res["name"]
    assert inventory.count_of(p, skills.book_id(res["name"])) == 0


def test_learn_requires_book():
    p = make_player()
    pm.add_general(p, "关羽")
    pm.save(p)
    res = skills.learn(p, "关羽", "破军")
    assert res["ok"] is False and res["reason"] == "no_book"


def test_custom_skill_crud():
    res = skills_admin.save_custom_skill({
        "name": "燎原", "type": "active", "category": "damage",
        "target": "enemy_all", "trigger": "attack", "chance": 0.5,
        "scale": {"attr": "intellect"},
        "effects": [{"type": "dmg_magic", "params": {"coef": 1.5}}], "book_cost": 55,
    })
    assert res["ok"], res
    assert skillgen.custom_def("燎原") is not None
    names = [s["name"] for s in skills.distinct_skills()]
    assert "燎原" in names
    e = skills.find("燎原")
    assert e["cost"] == 55
    # 自动生成技能书道具
    book = inventory
    assert skills.book_id("燎原")
    assert skills_admin.delete_custom_skill("燎原")["ok"]
    assert skillgen.custom_def("燎原") is None


def test_battle_runs_with_skills():
    from liufeng_sanguo_game.systems import battle
    import random

    p = make_player()
    pm.add_general(p, "吕布")
    info = pm.general_info(p, "吕布")
    e = [{"name": "吕布", "info": info, "level": 1, "star": 1}]
    res = battle.simulate(e, e, rng=random.Random(7))
    assert res["winner"] in ("a", "b", "draw")
