"""定时任务（自定义/汉化）单测：job_admin + Scheduler。运行：pytest"""

import pytest

from liufeng_sanguo_game.core import storage
from liufeng_sanguo_game.systems import job_admin


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    storage.set_data_root(tmp_path)
    yield
    storage.set_data_root(None)


def test_actions_catalog():
    assert len(job_admin.ACTIONS) == 12
    ids = job_admin.ACTION_IDS
    for need in ("broadcast", "mail_all", "worldboss_spawn", "events_open", "reload_data"):
        assert need in ids
    mail_params = {p["key"] for p in job_admin.ACTION_MAP["mail_all"]["params"]}
    assert {"title", "gold", "skill_frag", "items", "generals"} <= mail_params
    bc = {p["key"] for p in job_admin.ACTION_MAP["broadcast"]["params"]}
    assert {"target", "text"} <= bc
    target_field = next(p for p in job_admin.ACTION_MAP["broadcast"]["params"] if p["key"] == "target")
    assert {o["value"] for o in target_field["options"]} == {"group", "private", "all"}


def test_normalize_filters_params_and_defaults():
    norm = job_admin.normalize_job({
        "label": "每日补偿", "action": "mail_all", "interval": 0,
        "params": {"title": "补偿", "gold": 100, "not_a_param": 1},
    })
    assert norm["interval"] == 3600  # 0 视为无效 -> 默认 3600
    assert norm["params"] == {"title": "补偿", "gold": 100}
    assert norm["label"] == "每日补偿"
    assert norm["action"] == "mail_all"
    # 负值被夹到 1
    assert job_admin.normalize_job({"label": "x", "action": "broadcast", "interval": -5})["interval"] == 1


def test_validate_job():
    assert job_admin.validate_job({"label": "", "action": "mail_all", "interval": 60})["ok"] is False
    assert job_admin.validate_job({"label": "x", "action": "bad", "interval": 60})["ok"] is False
    assert job_admin.validate_job({"label": "x", "action": "mail_all", "interval": 0})["ok"] is False
    assert job_admin.validate_job({"label": "x", "action": "mail_all", "interval": 60})["ok"] is True


def test_custom_job_crud():
    res = job_admin.save_custom_job({"label": "每小时公告", "action": "broadcast",
                                     "interval": 3600, "enabled": True,
                                     "params": {"text": "hi"}})
    assert res["ok"]
    jid = res["id"]
    assert job_admin.list_custom()[0]["label"] == "每小时公告"
    assert job_admin.delete_custom_job(jid)["ok"]
    assert job_admin.list_custom() == []
    assert job_admin.delete_custom_job("nope")["ok"] is False


def test_scheduler_label_and_remove():
    pytest.importorskip("astrbot.api")
    from liufeng_sanguo_game.core.scheduler import Scheduler

    s = Scheduler()
    s.add_job("builtin_x", lambda: None, 60, label="内置任务")
    info = s.job_info("builtin_x")
    assert info["label"] == "内置任务"
    s.add_job("custom:abc", lambda: None, 30)
    assert s.job_info("custom:abc")["label"] == "custom:abc"
    assert s.remove_job("custom:abc") is True
    assert s.job_info("custom:abc") is None
    assert s.remove_job("nope") is False
    assert s.set_enabled("builtin_x", False) and s.job_info("builtin_x")["enabled"] is False
