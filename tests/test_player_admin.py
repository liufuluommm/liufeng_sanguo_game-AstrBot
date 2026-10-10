"""玩家管理（管理台操作）单元测试：资料/货币/邮件发放/清空/封禁/删除连带清理。运行：pytest"""

import time

import pytest

from liufeng_sanguo_game.core import storage
from liufeng_sanguo_game.systems import (faction, guild, mail, player as pm,
                                         player_admin as pa)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    storage.set_data_root(tmp_path)
    yield
    storage.set_data_root(None)


def make_player(qq="10001", name="甲", gold=1000):
    p = pm.new_player(qq, name, initial_gold=gold, dorm_capacity=15)
    pm.save(p)
    return p


def test_edit_profile():
    make_player()
    assert pa.edit_profile("10001", {"name": "乙", "level": 7, "rating": 1500,
                                     "stamina": 99, "dorm_capacity": 30})["ok"]
    p = pm.load("10001")
    assert p["name"] == "乙" and p["level"] == 7
    assert p["pvp"]["rating"] == 1500 and p["stamina"] == 99
    assert p["buildings"]["dormitory"]["capacity"] == 30


def test_adjust_currency_add_sub_set():
    make_player()
    assert pa.adjust_currency("10001", "gold", "add", 500)["value"] == 1500
    assert pa.adjust_currency("10001", "gold", "sub", 200)["value"] == 1300
    assert pa.adjust_currency("10001", "gold", "set", 10)["value"] == 10
    pa.adjust_currency("10001", "skill_frag", "add", 20)
    pa.adjust_currency("10001", "stamina", "set", 60)
    p = pm.load("10001")
    assert p["wallet"]["skill_frag"] == 20 and p["stamina"] == 60
    assert p["wallet"]["gold"] == p["gold"] == 10
    assert pa.adjust_currency("10001", "bad", "add", 1)["ok"] is False


def test_give_via_mail_and_claim():
    make_player()
    res = pa.give_via_mail("10001", "补偿", "致歉", {
        "gold": 100, "skill_frag": 5, "generals": ["吕布"], "items": {"item_gold_bag": 2}})
    assert res["ok"]
    inbox = mail.inbox("10001")
    assert len(inbox) == 1
    claim = mail.claim("10001", inbox[0]["id"])
    assert claim["ok"]
    p = pm.load("10001")
    assert p["gold"] >= 1100
    assert p["wallet"]["skill_frag"] == 5
    assert pm.has_general(p, "吕布")
    from liufeng_sanguo_game.systems import inventory
    assert inventory.count_of(p, "item_gold_bag") == 2


def test_clear_targets():
    p = make_player()
    pm.add_general(p, "关羽")
    pm.save(p)
    from liufeng_sanguo_game.systems import inventory
    inventory.add_item(p, "item_gold_bag", 3)
    pm.save(p)
    assert pa.clear("10001", "inventory")["ok"]
    assert pm.load("10001")["inventory"] == {}
    assert pa.clear("10001", "team")["ok"]
    assert pm.load("10001")["team"] == []
    assert pa.clear("10001", "bad")["ok"] is False


def test_ban_and_unban():
    make_player()
    assert not pa.is_banned("10001")
    pa.ban("10001", "刷分")
    assert pa.is_banned("10001") and pa.ban_reason("10001") == "刷分"
    assert pa.unban("10001")["ok"]
    assert not pa.is_banned("10001")


def test_remove_player_dissolves_guild_for_leader():
    leader = make_player("1", "团长", gold=100000)
    mem = make_player("2", "成员")
    guild.create(leader, "测试团")
    guild.join(mem, leader["guild"])
    assert len(guild.top(10 ** 9)) == 1
    res = pa.remove_player("1")
    assert res["ok"] and res["guild_dissolved"] == "测试团"
    assert len(guild.top(10 ** 9)) == 0
    assert pm.load("2")["guild"] == ""
    assert not storage.player_exists("1")


def test_remove_player_cleans_associations():
    make_player("1", "甲")
    # 国战
    p = pm.load("1")
    faction.join(p, "wei")
    pm.save(p)
    # 拍卖：作为卖家 + 作为买家
    storage.save_global("auction", {"counter": 0, "listings": {
        "L1": {"seller": "1", "expire_ts": int(time.time()) + 3600, "status": "active"},
        "L2": {"seller": "9", "current_bidder": "1", "current_bid": 500,
               "expire_ts": int(time.time()) + 3600, "status": "active"},
    }})
    # 世界BOSS
    storage.save_global("worldboss", {"active": True, "participants": {"1": {"damage": 10}}})
    pa.ban("1", "test")
    res = pa.remove_player("1")
    assert res["ok"] and res["auction_removed"] == 1 and res["auction_bids_cleared"] == 1
    adata = storage.load_global("auction", {})
    assert "L1" not in adata["listings"]
    assert adata["listings"]["L2"]["current_bidder"] is None and adata["listings"]["L2"]["current_bid"] == 0
    assert "1" not in storage.load_global("worldboss", {}).get("participants", {})
    fac = storage.load_global("factions", {})
    assert all("1" not in (members or []) for members in fac.get("members", {}).values())
    assert not pa.is_banned("1")
    assert not pm.load("1")
