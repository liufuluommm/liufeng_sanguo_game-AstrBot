"""管理台运营页面单测：军团 / 装备 / 拍卖行 / 活动 / 定时任务 / 世界BOSS。运行：pytest"""

import asyncio

import pytest

from liufeng_sanguo_game.core import storage
from liufeng_sanguo_game.core.scheduler import Scheduler
from liufeng_sanguo_game.systems import (auction_admin as aa, equipment_admin as ea,
                                         events, guild, guild_admin as ga,
                                         player as pm, worldboss)
from liufeng_sanguo_game.systems.tables import tables


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    storage.set_data_root(tmp_path)
    yield
    storage.set_data_root(None)


def make_player(qq="1", name="甲", gold=1000):
    p = pm.new_player(qq, name, initial_gold=gold, dorm_capacity=15)
    pm.save(p)
    return p


def test_guild_admin_ops():
    leader = make_player("1", "团长", 100000)
    mem = make_player("2", "成员")
    guild.create(leader, "测试团")
    gid = leader["guild"]
    guild.join(mem, gid)
    assert ga.list_guilds()[0]["members"] == 2
    assert ga.rename(gid, "新团")["ok"]
    assert ga.set_stats(gid, level=3, fund=500, exp=2000)["ok"]
    assert ga.set_leader(gid, "2")["ok"]
    assert ga.remove_member(gid, "1")["ok"]
    assert ga.remove_member(gid, "2")["ok"] is False  # leader cannot be kicked
    res = ga.dissolve(gid)
    assert res["ok"] and ga.list_guilds() == []
    assert not pm.load("2").get("guild")


def test_equipment_admin_defs_and_player():
    assert ea.save_custom_def({"id": "wp_test", "name": "测试剑", "slot": "weapon",
                               "rarity": "sr", "force": 50, "intellect": 1, "lead": 5})["ok"]
    assert tables().equipment("wp_test") is not None
    # 内置不可改
    assert ea.save_custom_def({"id": "wp_iron", "name": "x", "slot": "weapon"})["ok"] is False
    make_player("1")
    assert ea.give("1", "wp_test", 2)["ok"]
    uid = ea.list_player("1")[0]["uid"]
    assert ea.enhance("1", uid, 3)["ok"]
    assert ea.list_player("1")[0]["level"] == 5
    assert ea.set_level("1", uid, 1)["ok"]
    assert ea.remove("1", uid)["ok"]
    assert ea.list_player("1") == []
    assert ea.delete_custom_def("wp_test")["ok"]


def test_auction_admin_ops():
    seller = make_player("1", "卖家")
    buyer = make_player("2", "买家", 100000)
    import time
    storage.save_global("auction", {"counter": 2, "listings": {
        "A00001": {"id": "A00001", "seller": "1", "seller_name": "卖家", "kind": "fragment",
                   "payload": {"count": 5}, "mode": "buyout", "price": 100, "step": 50,
                   "current_bid": 0, "current_bidder": "", "deposit": 0,
                   "created_ts": 0, "expire_ts": int(time.time()) + 3600, "status": "active"},
        "A00002": {"id": "A00002", "seller": "1", "seller_name": "卖家", "kind": "fragment",
                   "payload": {"count": 3}, "mode": "bid", "price": 100, "step": 50,
                   "current_bid": 200, "current_bidder": "2", "deposit": 20,
                   "created_ts": 0, "expire_ts": int(time.time()) + 3600, "status": "active"},
    }})
    assert len(aa.list_all()) == 2
    assert aa.force_cancel("A00001")["ok"]
    res = aa.force_settle("A00002")
    assert res["ok"] and res["result"] == "sold"
    assert pm.load("2")["fragments"] >= 3


def test_events_admin_custom_and_toggle():
    assert events.save_custom({"id": "ev_test", "name": "测试活动", "buff_type": "double_gold",
                               "duration": 600})["ok"]
    ids = [d["id"] for d in events.defs()]
    assert "ev_test" in ids
    assert events.open_event("ev_test")["ok"]
    assert any(e["id"] == "ev_test" for e in events.active_events())
    events.set_enabled(False)
    assert events.active_events() == []
    events.set_enabled(True)
    assert events.close_event("ev_test")["ok"]
    assert events.delete_custom("ev_test")["ok"]


def test_scheduler_admin():
    s = Scheduler()
    s.add_job("j1", lambda: None, 60)
    assert s.set_interval("j1", 120)
    j = s.job_info("j1")
    assert j["interval"] == 120 and j["enabled"] is True
    assert s.set_enabled("j1", False)
    assert s.job_info("j1")["enabled"] is False
    asyncio.get_event_loop().run_until_complete(s.run_job("j1"))
    assert s.job_info("j1")["run_count"] == 1


def test_worldboss_admin_custom_spawn_duration():
    assert worldboss.save_custom_boss({"id": "boss_test", "name": "测试BOSS",
                                       "hp": 1000, "atk": 10, "def": 5})["ok"]
    res = worldboss.spawn("boss_test", 120)
    assert res["ok"]
    cur = worldboss.current()
    assert cur["active"] and cur["boss"]["id"] == "boss_test"
    assert cur["end_ts"] - cur["start_ts"] == 120
    assert worldboss.force_close()["ok"]
    assert worldboss.current()["active"] is False
    assert worldboss.delete_custom_boss("boss_test")["ok"]
