"""核心逻辑单元测试（不依赖 astrbot）。运行：pytest -q"""

import random

import pytest

from liufeng_sanguo_game.core import storage
from liufeng_sanguo_game.systems import battle, building, gacha
from liufeng_sanguo_game.systems import player as player_mod
from liufeng_sanguo_game.systems.tables import tables


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    storage.set_data_root(tmp_path)
    yield
    storage.set_data_root(None)


def make_player(qq="10001", name="测试", gold=100000):
    p = player_mod.new_player(qq, name, initial_gold=gold, dorm_capacity=15)
    player_mod.save(p)
    return p


def test_player_persist():
    make_player()
    loaded = player_mod.load("10001")
    assert loaded is not None
    assert loaded["name"] == "测试"
    assert storage.player_exists("10001")
    assert "10001" in storage.list_players()


def test_tables_counts():
    t = tables()
    assert len(t.historical["ssr"]) == 20
    total = sum(len(v) for v in t.historical.values())
    assert total == 150
    assert sum(len(v) for v in t.obscure.values()) == 100
    assert sum(len(v) for v in t.fictional.values()) == 120


def test_exchange_requires_fragments():
    p = make_player()
    res = gacha.exchange_historical(p, 15, {"ssr": 0.05, "sr": 0.15, "r": 0.35, "n": 0.45})
    assert res["ok"] is False
    assert res["reason"] == "fragments"


def test_exchange_success():
    p = make_player()
    p["fragments"] = 15
    res = gacha.exchange_historical(p, 15, {"ssr": 0.05, "sr": 0.15, "r": 0.35, "n": 0.45})
    assert res["ok"] is True
    assert res["fragments_left"] == 0
    assert player_mod.has_general(p, res["general"])


def test_fictional_fail_rate_range():
    rng = random.Random(1234)
    p = make_player(gold=10_000_000)
    fails = 0
    trials = 4000
    for _ in range(trials):
        res = gacha.recruit_fictional(p, 100, 0.25, 0.30, {"ssr": 0.05, "sr": 0.15, "r": 0.35, "n": 0.45}, rng=rng)
        if not res["ok"] and res.get("reason") == "failed":
            fails += 1
            assert 0.25 <= res["fail_rate"] <= 0.30
    rate = fails / trials
    assert 0.22 <= rate <= 0.33, rate


def test_custom_stats_and_capacity():
    p = make_player(gold=100000)
    for i in range(15):
        res = gacha.recruit_custom(p, f"自定义{i}", 1000, 30, 100)
        assert res["ok"] is True, res
        for k in ("force", "intellect", "vitality", "charisma", "eloquence", "speed"):
            assert 30 <= res["stats"][k] <= 100
    # 第 16 个应因容量不足失败
    res = gacha.recruit_custom(p, "溢出", 1000, 30, 100)
    assert res["ok"] is False
    assert res["reason"] == "capacity"


def test_custom_name_taken():
    p = make_player()
    gacha.recruit_custom(p, "柳德", 1000, 30, 100)
    res = gacha.recruit_custom(p, "柳德", 1000, 30, 100)
    assert res["ok"] is False
    assert res["reason"] == "name_taken"


def test_dorm_upgrade_cost_doubles():
    p = make_player(gold=1_000_000)
    base = 1500
    assert building.upgrade_cost(p, base) == 1500
    r1 = building.upgrade(p, base, 1, 3)
    assert r1["ok"] and r1["cost"] == 1500
    assert building.upgrade_cost(p, base) == 3000
    r2 = building.upgrade(p, base, 1, 3)
    assert r2["cost"] == 3000
    assert r2["capacity"] >= r1["capacity"] + 1


def test_battle_deterministic_seed():
    a = [{"name": "吕布", "info": {"name": "吕布", "force": 100, "intellect": 30, "lead": 80, "troop": "cavalry"}}]
    b = [{"name": "小兵", "info": {"name": "小兵", "force": 30, "intellect": 20, "lead": 20, "troop": "archer"}}]
    res = battle.simulate(a, b, rng=random.Random(42))
    assert res["winner"] in ("a", "b", "draw")
    assert res["winner"] == "a"


def test_ranking():
    p1 = make_player("1", "甲", 1000)
    p2 = make_player("2", "乙", 1000)
    player_mod.add_general(p1, "吕布")
    player_mod.add_general(p1, "关羽")
    player_mod.add_general(p2, "小兵") if tables().get("小兵") else None
    player_mod.save(p1)
    player_mod.save(p2)
    from liufeng_sanguo_game.systems.ranking import power_ranking

    rows = power_ranking(10)
    assert rows[0]["name"] == "甲"


def test_cultivate_level_and_cost():
    from liufeng_sanguo_game.systems import cultivate

    p = make_player(gold=100000)
    player_mod.add_general(p, "吕布")
    player_mod.save(p)
    res = cultivate.cultivate(p, "吕布", 5)
    assert res["ok"] and res["level"] == 6
    assert res["spent"] > 0


def test_star_up_needs_fragments():
    from liufeng_sanguo_game.systems import cultivate

    p = make_player(gold=100000)
    player_mod.add_general(p, "吕布")
    player_mod.save(p)
    res = cultivate.star_up(p, "吕布")
    assert res["ok"] is False and res["reason"] == "fragments"
    p["fragments"] = 100
    res = cultivate.star_up(p, "吕布")
    assert res["ok"] and res["star"] == 2


def test_synthesize():
    from liufeng_sanguo_game.systems import collection

    p = make_player(gold=100000)
    # 找三个 N 卡
    ncards = [g["name"] for g in tables().by_rarity("n")][:3]
    for name in ncards:
        player_mod.add_general(p, name)
    player_mod.save(p)
    res = collection.synthesize(p, "n")
    assert res["ok"] is True
    for name in res["consumed"]:
        assert not player_mod.has_general(p, name)


def test_team_and_bond():
    from liufeng_sanguo_game.systems import team

    p = make_player()
    for name in ("关羽", "张飞", "赵云"):
        player_mod.add_general(p, name)
    player_mod.save(p)
    for name in ("关羽", "张飞", "赵云"):
        assert team.add(p, name)["ok"]
    assert len(team.current_team(p)) == 3
    assert team.add(p, "马超")["ok"] is False
    b = team.bonus(p)
    assert b["bonus"] > 0  # 五虎/桃园应激活


def test_pokedex():
    from liufeng_sanguo_game.systems import collection

    p = make_player()
    player_mod.add_general(p, "关羽")
    player_mod.save(p)
    dex = collection.pokedex(p)
    assert dex["categories"]["historical"]["have"] == 1
    assert dex["total"] >= 370


def test_forge_enhance_equip():
    from liufeng_sanguo_game.systems import equipment

    p = make_player(gold=100000)
    player_mod.add_general(p, "关羽")
    player_mod.save(p)
    res = equipment.forge(p)
    assert res["ok"] and len(p["equipments"]) == 1
    assert equipment.enhance(p, 0)["ok"]
    assert p["equipments"][0]["level"] == 2
    assert equipment.equip(p, 0, "关羽")["ok"]
    eq = p["generals"]["关羽"]["equip"]
    assert eq, "装备应挂到武将身上"


def test_dungeon_challenge_and_sweep():
    from liufeng_sanguo_game.systems import dungeon

    p = make_player(gold=100000)
    p["stamina"] = 200
    for name in ("吕布", "关羽", "诸葛亮"):
        player_mod.add_general(p, name)
    player_mod.save(p)
    team = [
        {"name": "吕布", "info": tables().get("吕布"), "level": 100, "star": 10},
        {"name": "关羽", "info": tables().get("关羽"), "level": 100, "star": 10},
        {"name": "诸葛亮", "info": tables().get("诸葛亮"), "level": 100, "star": 10},
    ]
    res = dungeon.challenge(p, "1-1", team)
    assert res["ok"] and res["won"] is True
    assert dungeon.is_cleared(p, "1-1")
    assert dungeon.is_unlocked(p, "1-2")
    sw = dungeon.sweep(p, "1-1", 3)
    assert sw["ok"] and sw["times"] >= 1
    assert sw["gold"] > 0


def test_dungeon_locked():
    from liufeng_sanguo_game.systems import dungeon

    p = make_player()
    assert dungeon.is_unlocked(p, "1-1") is True
    assert dungeon.is_unlocked(p, "1-2") is False


def test_item_use_and_buff():
    from liufeng_sanguo_game.systems import inventory, items as items_mod

    p = make_player(gold=1000)
    inventory.add_item(p, "item_gold_bag", 1)
    assert inventory.count_of(p, "item_gold_bag") == 1
    res = inventory.use_item(p, "item_gold_bag")
    assert res["ok"] and p["gold"] == 3000
    assert inventory.count_of(p, "item_gold_bag") == 0

    inventory.add_item(p, "item_double_gold_card", 1)
    inventory.use_item(p, "item_double_gold_card")
    from liufeng_sanguo_game.systems import buff

    assert buff.value(p, "double_gold") == 2.0


def test_loot_box_and_choice():
    from liufeng_sanguo_game.systems import inventory, items as items_mod

    p = make_player(gold=0)
    inventory.add_item(p, "item_lucky_box", 1)
    res = inventory.use_item(p, "item_lucky_box")
    assert res["ok"]
    # 自选礼盒 -> pending
    inventory.add_item(p, "item_choice_box", 1)
    res = inventory.use_item(p, "item_choice_box")
    assert res["ok"] and p.get("pending_choice")
    out = items_mod.resolve_choice(p, 0)
    assert out["ok"]


def test_shop_buy_and_limit():
    from liufeng_sanguo_game.systems import shop

    p = make_player(gold=100000)
    res = shop.buy(p, "daily", "item_gold_bag", 2)
    assert res["ok"] and res["qty"] == 2
    assert p["inventory"]["item_gold_bag"] == 2
    # 超过每日限购 5
    res2 = shop.buy(p, "daily", "item_gold_bag", 10)
    assert res2["ok"] and res2["qty"] == 3


def test_exchange_single_direction():
    from liufeng_sanguo_game.systems import exchange

    p = make_player(gold=100000)
    res = exchange.do_exchange(p, "ex_gold_diamond", 3)
    assert res["ok"] and p["wallet"]["diamond"] == 3
    assert p["gold"] == 100000 - 1500


def test_auction_buyout():
    from liufeng_sanguo_game.systems import auction

    seller = make_player("20001", "卖家", 1000)
    buyer = make_player("20002", "买家", 100000)
    seller["fragments"] = 10
    player_mod.save(seller)
    res = auction.create_fragment(seller, 5, "buyout", 2000, hours=6)
    assert res["ok"]
    listing_id = res["listing"]["id"]
    before_gold = seller["gold"]
    res2 = auction.buyout(buyer, listing_id)
    assert res2["ok"]
    buyer_reload = player_mod.load("20002")
    seller_reload = player_mod.load("20001")
    assert buyer_reload["fragments"] == 5
    assert seller_reload["gold"] == before_gold + int(2000 * 0.95)


def test_auction_bid_deposit():
    from liufeng_sanguo_game.systems import auction

    seller = make_player("30001", "卖家", 1000)
    b1 = make_player("30002", "竞1", 100000)
    seller["fragments"] = 10
    player_mod.save(seller)
    res = auction.create_fragment(seller, 5, "bid", 1000, step=100, hours=6)
    listing_id = res["listing"]["id"]
    bid = auction.bid(b1, listing_id, 1000)
    assert bid["ok"] and bid["deposit"] > 0
    # 到期结算成交
    import time as _t

    events = auction.settle(now=int(_t.time()) + 7 * 3600)
    assert any(e["id"] == listing_id and e["result"] == "sold" for e in events)
    b1_reload = player_mod.load("30002")
    assert b1_reload["fragments"] == 5


def test_faction_join_donate():
    from liufeng_sanguo_game.systems import faction

    p = make_player(gold=10000)
    res = faction.join(p, "shu")
    assert res["ok"]
    d = faction.donate(p, 1000)
    assert d["ok"] and p["faction_contrib"] > 0
    info = faction.info(p)
    assert info["faction"] == "shu"
    assert any(r["id"] == "shu" for r in info["list"])


def test_guild_create_donate():
    from liufeng_sanguo_game.systems import guild

    p = make_player(gold=100000)
    res = guild.create(p, "桃园结义")
    assert res["ok"]
    gid = res["guild"]["id"]
    p2 = make_player("40002", "小弟", 100000)
    assert guild.join(p2, gid)["ok"]
    d = guild.donate(p, 2000)
    assert d["ok"] and d["guild_level"] >= 1
    info = guild.info(p)
    assert info["guild"]["name"] == "桃园结义"


def test_quest_progress_and_claim():
    from liufeng_sanguo_game.systems import quest

    p = make_player(gold=0)
    quest.progress_event(p, "signin", 1)
    data = quest.quest_list(p)
    d_sign = next(q for q in data["daily"] if q["id"] == "d_signin")
    assert d_sign["progress"] == 1
    res = quest.claim_quest(p, "d_signin")
    assert res["ok"] and p["gold"] >= 200


def test_achievement_claim():
    from liufeng_sanguo_game.systems import quest

    p = make_player()
    quest.progress_event(p, "battle", 100)
    res = quest.claim_achievement(p, "a_battle100")
    assert res["ok"]


def test_mail_send_claim():
    from liufeng_sanguo_game.systems import mail

    p = make_player("50001", "收件人", 0)
    mail.send("50001", "补偿奖励", "感谢参与", {"gold": 500, "fragment": 2})
    mails = mail.inbox("50001")
    assert len(mails) == 1
    res = mail.claim("50001", mails[0]["id"])
    assert res["ok"]
    reloaded = player_mod.load("50001")
    assert reloaded["gold"] == 500
    assert reloaded["fragments"] == 2


def test_worldboss_flow():
    from liufeng_sanguo_game.systems import worldboss, mail

    p = make_player("60001", "讨伐者", 1000)
    worldboss.spawn("boss_zhangjiao")
    data = worldboss.current()
    assert data["active"]
    hp0 = data["hp"]
    r1 = worldboss.attack(p, 100000)
    assert r1["ok"] and r1["damage"] > 0
    assert worldboss.current()["hp"] < hp0
    r2 = worldboss.attack(p, 100000)
    r3 = worldboss.attack(p, 100000)
    r4 = worldboss.attack(p, 100000)
    assert r4["ok"] is False and r4["reason"] == "limit"
    events = worldboss.settle()
    assert events["ok"]
    assert len(mail.inbox("60001")) >= 1


def test_battlepass_flow():
    from liufeng_sanguo_game.systems import battlepass

    p = make_player("70001", "战令玩家", 1000)
    p["wallet"]["diamond"] = 100
    player_mod.save(p)
    battlepass.add_exp(p, 3000)
    prog = battlepass.progress(p)
    assert prog["level"] >= 2
    assert battlepass.unlock_premium(p)["ok"]
    res = battlepass.claim(p, 1, "免费")
    assert res["ok"]
    res2 = battlepass.claim(p, 1, "进阶")
    assert res2["ok"]
    assert battlepass.claim(p, 1, "免费")["ok"] is False


def test_events_buff():
    from liufeng_sanguo_game.systems import events

    events.close_event("ev_double_gold")
    assert events.multiplier("double_gold") == 1.0
    res = events.open_event("ev_double_gold", 3600)
    assert res["ok"]
    assert events.multiplier("double_gold") == 2.0
    events.open_event("ev_free_stamina", 3600)
    assert events.free_stamina() is True
    events.close_event("ev_free_stamina")
    assert events.free_stamina() is False


def test_custom_item_save_delete():
    from liufeng_sanguo_game.systems import items as items_mod

    item = {
        "id": "item_test_custom",
        "name": "测试道具",
        "category": "resource",
        "rarity": "r",
        "desc": "测试",
        "usable": True,
        "target": "self",
        "effects": [{"type": "grant_gold", "params": {"amount": 123}}],
    }
    res = items_mod.save_custom_item(item)
    assert res["ok"]
    assert items_mod.get_item("item_test_custom") is not None
    # 校验非法效果
    bad = dict(item, id="item_bad", effects=[{"type": "not_exist", "params": {}}])
    assert items_mod.save_custom_item(bad)["ok"] is False
    assert items_mod.delete_custom_item("item_test_custom")["ok"]
    assert items_mod.get_item("item_test_custom") is None


def test_custom_item_written_to_data_dir(tmp_path):
    from liufeng_sanguo_game.core import storage
    from liufeng_sanguo_game.systems import items as items_mod

    storage.set_data_root(tmp_path)
    try:
        item = {
            "id": "item_datadir", "name": "数据目录道具", "category": "resource",
            "rarity": "n", "desc": "", "usable": True, "target": "self",
            "effects": [{"type": "grant_gold", "params": {"amount": 1}}],
        }
        assert items_mod.save_custom_item(item)["ok"]
        assert (tmp_path / "items_custom.json").exists()
    finally:
        storage.set_data_root(None)


def test_auction_invalid_listing_keeps_asset():
    from liufeng_sanguo_game.systems import auction

    p = make_player("90001", "卖家", 1000)
    p["fragments"] = 10
    player_mod.save(p)
    # 非法时长 -> 校验失败，碎片不能被扣走
    res = auction.create_fragment(p, 5, "buyout", 1000, hours=99)
    assert res["ok"] is False and res["reason"] == "bad_duration"
    assert p["fragments"] == 10
    # 非法模式
    res2 = auction.create_fragment(p, 5, "xxx", 1000, hours=6)
    assert res2["ok"] is False and p["fragments"] == 10


def test_equipment_no_duplicate_and_replace():
    from liufeng_sanguo_game.systems import equipment

    p = make_player(gold=1000000)
    player_mod.add_general(p, "关羽")
    player_mod.add_general(p, "张飞")
    # 直接放置两件同部位（武器）装备，保证替换语义
    p["equipments"] = [
        {"uid": "u1", "id": "wp_iron", "level": 1, "equipped_by": None},
        {"uid": "u2", "id": "wp_qinggang", "level": 1, "equipped_by": None},
    ]
    player_mod.save(p)
    # 同一件装备不能穿给两个人
    assert equipment.equip(p, 0, "关羽")["ok"]
    dup = equipment.equip(p, 0, "张飞")
    assert dup["ok"] is False and dup["reason"] == "in_use"
    # 关羽换同部位装备时，旧装备应被解绑
    assert equipment.equip(p, 1, "关羽")["ok"]
    assert p["equipments"][0]["equipped_by"] is None
    assert p["equipments"][1]["equipped_by"] == "关羽"


def test_quest_period_validation():
    from liufeng_sanguo_game.systems import quest

    p = make_player()
    # 造一条“上一周期”的已完成记录
    p.setdefault("quests", {})["d_signin"] = {"progress": 1, "claimed": False, "period": "1999-01-01"}
    player_mod.save(p)
    res = quest.claim_quest(p, "d_signin")
    assert res["ok"] is False and res["reason"] == "expired"


def test_quest_sync_max():
    from liufeng_sanguo_game.systems import quest

    p = make_player()
    quest.sync_max(p, "general_level", 20)
    data = quest.quest_list(p)
    g = next(q for q in data["growth"] if q["id"] == "g_level20")
    assert g["progress"] == 20


def test_worldboss_attack_limit_configurable():
    from liufeng_sanguo_game.systems import worldboss

    p = make_player("91001", "王", 1000)
    worldboss.spawn("boss_zhangjiao")
    assert worldboss.attack(p, 1000, limit=1)["ok"]
    r2 = worldboss.attack(p, 1000, limit=1)
    assert r2["ok"] is False and r2["reason"] == "limit" and r2["max"] == 1


def test_events_and_battlepass_toggle():
    from liufeng_sanguo_game.systems import battlepass, events, quest

    try:
        events.set_enabled(False)
        assert events.multiplier("double_gold") == 1.0
        events.set_enabled(True)
        events.open_event("ev_double_gold", 3600)
        assert events.multiplier("double_gold") == 2.0
        events.close_event("ev_double_gold")

        battlepass.set_enabled(False)
        p = make_player("92001", "战令测试", 0)
        before = battlepass.progress(p)["exp"]
        battlepass.add_exp(p, 1000)
        assert battlepass.progress(p)["exp"] == before
        battlepass.set_enabled(True)
    finally:
        events.set_enabled(True)
        battlepass.set_enabled(True)


def test_security_cooldown():
    from liufeng_sanguo_game.core import security

    ok, _ = security.check_cooldown("u1:cmdA", 100)
    assert ok is True
    ok2, remain = security.check_cooldown("u1:cmdA", 100)
    assert ok2 is False and remain > 0
    # 不同指令互不影响
    ok3, _ = security.check_cooldown("u1:cmdB", 100)
    assert ok3 is True


def test_auction_buyout_rejected_on_bid():
    from liufeng_sanguo_game.systems import auction

    seller = make_player("93001", "卖家", 1000)
    buyer = make_player("93002", "买家", 100000)
    seller["fragments"] = 10
    player_mod.save(seller)
    res = auction.create_fragment(seller, 5, "bid", 1000, step=100, hours=6)
    assert res["ok"]
    lid = res["listing"]["id"]
    r = auction.buyout(buyer, lid)
    assert r["ok"] is False and r["reason"] == "bid_only"


def test_load_custom_prefers_existing_data_file(tmp_path, monkeypatch):
    from liufeng_sanguo_game.systems import items as items_mod

    data_root = tmp_path / "data"
    data_root.mkdir()
    legacy = tmp_path / "legacy.json"
    legacy.write_text('{"old": {"id": "old"}}', encoding="utf-8")
    monkeypatch.setattr(items_mod, "_custom_path", lambda: data_root / "items_custom.json")
    monkeypatch.setattr(items_mod, "_legacy_custom_path", lambda: legacy)
    # 无数据文件 -> 回退 legacy
    assert "old" in items_mod.load_custom()
    # 数据文件存在但为空 -> 以数据文件为准，不复活 legacy
    (data_root / "items_custom.json").write_text("{}", encoding="utf-8")
    assert items_mod.load_custom() == {}


def test_duel_entry_and_leader():
    from liufeng_sanguo_game.systems import team

    p = make_player("80001", "决斗者", 1000)
    for name in ("吕布", "关羽", "诸葛亮"):
        player_mod.add_general(p, name)
    player_mod.save(p)
    # 无主将、无阵容 -> 战力最高（关羽 358 > 吕布 310 > 诸葛亮 278）
    assert team.duel_entry(p)["name"] == "关羽"
    # 设置主将后优先主将
    assert team.set_leader(p, "诸葛亮")["ok"]
    assert team.duel_entry(p)["name"] == "诸葛亮"
    # 非持有武将不可设为主将
    assert team.set_leader(p, "不存在")["ok"] is False
    # 无主将时回退阵容首位
    p2 = make_player("80002", "甲", 1000)
    for name in ("张飞", "黄忠"):
        player_mod.add_general(p2, name)
    player_mod.save(p2)
    assert team.add(p2, "张飞")["ok"]
    assert team.duel_entry(p2)["name"] == "张飞"


def test_leader_protected_from_synthesize_and_dismantle():
    from liufeng_sanguo_game.systems import collection, team

    p = make_player("80003", "主将", 1000)
    ncards = [g["name"] for g in tables().by_rarity("n")][:4]
    for name in ncards:
        player_mod.add_general(p, name)
    player_mod.save(p)
    team.set_leader(p, ncards[0])
    # 主将不可被分解
    res = collection.dismantle(p, ncards[0])
    assert res["ok"] is False and res["reason"] == "in_team"
    # 主将不会被合成消耗
    syn = collection.synthesize(p, "n")
    assert syn["ok"]
    assert ncards[0] not in syn["consumed"]
    assert team.leader_name(p) == ncards[0]


def test_dismiss_custom_clears_leader():
    from liufeng_sanguo_game.systems import collection, gacha, team

    p = make_player("80004", "自定义主将", 100000)
    gacha.recruit_custom(p, "柳德", 1000, 30, 100)
    team.set_leader(p, "柳德")
    assert team.leader_name(p) == "柳德"
    collection.dismiss_custom(p, "柳德")
    assert team.leader_name(p) == ""


def test_base_power_multidim():
    from liufeng_sanguo_game.core.utils import base_power

    g = {"force": 100, "intellect": 100, "vitality": 100,
         "charisma": 100, "eloquence": 100, "speed": 100}
    # 权重和 = 2+1.5+1.5+1+1+1.2 = 8.2
    assert base_power(g) == 820


def test_general_info_skill_name():
    from liufeng_sanguo_game.systems import player as pm, tables

    p = make_player("81001", "技能测试", 0)
    pm.add_general(p, "吕布")
    pm.save(p)
    info = pm.general_info(p, "吕布")
    assert info.get("skill_name"), "技能名应接入战斗"
    assert info.get("skill_active"), "主动技能定义应接入"
    assert info.get("skill_active", {}).get("effects"), "主动技能应有效果"
    assert len(tables.tables().skill_effects) == 350


def test_skillgen_deterministic():
    from liufeng_sanguo_game.systems import skillgen, tables

    skillgen.reload()
    a = skillgen.generate("火计", "active")
    b = skillgen.generate("火计", "active")
    assert a == b
    assert a.get("category") and a.get("effects")
    c = skillgen.generate("铁骨", "passive")
    assert c.get("trigger") == "always"
    assert len(tables.tables().skill_effects) == 350


def test_battle_multidim_runs():
    from liufeng_sanguo_game.systems import battle

    a = [{"name": "A", "info": {"name": "A", "troop": "cavalry", "force": 90,
         "intellect": 80, "vitality": 90, "charisma": 70, "eloquence": 60, "speed": 85}}]
    b = [{"name": "B", "info": {"name": "B", "troop": "archer", "force": 60,
         "intellect": 50, "vitality": 60, "charisma": 50, "eloquence": 40, "speed": 60}}]
    res = battle.simulate(a, b, rng=random.Random(1))
    assert res["winner"] in ("a", "b", "draw")
    assert res["winner"] == "a"


def test_generals_admin_crud(tmp_path):
    from liufeng_sanguo_game.core import storage
    from liufeng_sanguo_game.systems import generals_admin, tables

    storage.set_data_root(tmp_path)
    try:
        g = {"name": "测试神将", "title": "试炼", "rarity": "ssr", "faction": "shu",
             "troop": "cavalry", "force": 99, "intellect": 88, "vitality": 90,
             "charisma": 85, "eloquence": 80, "speed": 95, "desc": "测试"}
        assert generals_admin.save_custom_general(g)["ok"]
        got = tables.tables().get("测试神将")
        assert got is not None and got["rarity"] == "ssr" and got["category"] == "custom"
        g["force"] = 100
        assert generals_admin.save_custom_general(g)["ok"]
        assert tables.tables().get("测试神将")["force"] == 100
        assert generals_admin.delete_custom_general("测试神将")["ok"]
        assert tables.tables().get("测试神将") is None
    finally:
        storage.set_data_root(None)
        tables.reload_tables()


def test_equipment_power_counts_lead():
    from liufeng_sanguo_game.systems import equipment

    base = equipment.equipment_power({"force": 10, "intellect": 0, "lead": 0})
    more = equipment.equipment_power({"force": 10, "intellect": 0, "lead": 10})
    assert more > base  # 装备「统率」计入战力









