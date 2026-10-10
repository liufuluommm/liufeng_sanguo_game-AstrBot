"""管理台「定时任务」：动作目录 + 自定义定时任务（持久化于数据目录 custom_jobs.json）。

自定义任务以固定间隔（秒）调度，由插件启动时注册进 `Scheduler`；
每个任务绑定一个 **动作**（基于游戏运行逻辑，见 `ACTIONS`）与一组中文参数。
"""

from __future__ import annotations

import json
import os
import zlib
from typing import Any, Dict, List

from ..core import storage

# 动作目录：id / 中文名 / 说明 / 参数 schema
ACTIONS: List[Dict[str, Any]] = [
    {
        "id": "broadcast", "label": "群发公告", "desc": "向已记录的会话群发一条文本公告（默认群聊）。",
        "params": [
            {"key": "target", "label": "目标", "type": "enum", "default": "group",
             "options": [{"value": "group", "label": "群聊"},
                         {"value": "private", "label": "私聊"},
                         {"value": "all", "label": "全部"}]},
            {"key": "text", "label": "公告内容", "type": "text", "default": ""},
        ],
    },
    {
        "id": "mail_all", "label": "全服邮件（含奖励）", "desc": "给所有玩家发送一封邮件，可附带奖励。",
        "params": [
            {"key": "title", "label": "邮件标题", "type": "text", "default": "系统奖励"},
            {"key": "body", "label": "邮件正文", "type": "text", "default": ""},
            {"key": "gold", "label": "金币", "type": "int", "default": 0},
            {"key": "diamond", "label": "元宝", "type": "int", "default": 0},
            {"key": "merit", "label": "功勋", "type": "int", "default": 0},
            {"key": "soul", "label": "将魂", "type": "int", "default": 0},
            {"key": "repute", "label": "声望", "type": "int", "default": 0},
            {"key": "event_ticket", "label": "活动券", "type": "int", "default": 0},
            {"key": "challenge", "label": "挑战令", "type": "int", "default": 0},
            {"key": "skill_frag", "label": "技能书碎片", "type": "int", "default": 0},
            {"key": "fragments", "label": "通用碎片", "type": "int", "default": 0},
            {"key": "stamina", "label": "行动力", "type": "int", "default": 0},
            {"key": "items", "label": "道具(JSON {道具ID:数量})", "type": "json", "default": {}},
            {"key": "generals", "label": "武将(逗号分隔)", "type": "text", "default": ""},
        ],
    },
    {
        "id": "worldboss_spawn", "label": "开启世界BOSS", "desc": "自动开启一个世界BOSS。",
        "params": [
            {"key": "boss_id", "label": "BOSS", "type": "enum", "source": "bosses", "default": ""},
            {"key": "duration", "label": "时长(秒,0=默认)", "type": "int", "default": 0},
        ],
    },
    {"id": "worldboss_settle", "label": "结算世界BOSS", "desc": "提前结算当前世界BOSS并发放奖励。", "params": []},
    {"id": "worldboss_watch", "label": "世界BOSS巡检", "desc": "巡检并在到期时自动结算世界BOSS。", "params": []},
    {"id": "auction_settle", "label": "拍卖行结算", "desc": "结算到期拍卖挂单。", "params": []},
    {
        "id": "events_open", "label": "开启活动", "desc": "自动开启一个限时活动。",
        "params": [
            {"key": "event_id", "label": "活动", "type": "enum", "source": "events", "default": ""},
            {"key": "duration", "label": "时长(秒,0=默认)", "type": "int", "default": 0},
        ],
    },
    {
        "id": "events_close", "label": "关闭活动", "desc": "关闭指定限时活动。",
        "params": [{"key": "event_id", "label": "活动", "type": "enum", "source": "events", "default": ""}],
    },
    {"id": "events_prune", "label": "活动巡检/清理", "desc": "清理已结束的活动状态。", "params": []},
    {"id": "stamina_recovery", "label": "行动力恢复", "desc": "为所有玩家恢复行动力。", "params": []},
    {"id": "reload_data", "label": "重载数据表", "desc": "热重载武将/技能/兵种/道具/商店等数据表。", "params": []},
    {"id": "housekeeping", "label": "系统巡检", "desc": "系统级巡检（占位日志）。", "params": []},
]

ACTION_IDS = [a["id"] for a in ACTIONS]
ACTION_MAP = {a["id"]: a for a in ACTIONS}


def _path():
    return storage.data_root() / "custom_jobs.json"


def load_custom() -> Dict[str, Dict]:
    p = _path()
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: Dict[str, Any]) -> None:
    p = _path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _slug(label: str) -> str:
    return "job_" + format(zlib.crc32(label.encode("utf-8")) % 0xFFFFFF, "06x")


def normalize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    label = str(job.get("label", "")).strip()
    action = job.get("action", "")
    if action not in ACTION_MAP:
        action = "housekeeping"
    # 只保留该动作声明的参数键
    allowed = {p["key"] for p in ACTION_MAP[action]["params"]}
    params = {}
    for k, v in (job.get("params") or {}).items():
        if k in allowed:
            params[k] = v
    jid = str(job.get("id") or "").strip() or _slug(label or action)
    return {
        "id": jid,
        "label": label or ACTION_MAP[action]["label"],
        "action": action,
        "interval": max(1, int(job.get("interval", 3600) or 3600)),
        "enabled": bool(job.get("enabled", True)),
        "params": params,
    }


def validate_job(job: Dict[str, Any]) -> Dict[str, Any]:
    label = str(job.get("label", "")).strip()
    if not label:
        return {"ok": False, "reason": "no_label"}
    if len(label) > 16:
        return {"ok": False, "reason": "label_too_long"}
    if job.get("action") not in ACTION_IDS:
        return {"ok": False, "reason": "bad_action"}
    try:
        if int(job.get("interval", 0)) < 1:
            return {"ok": False, "reason": "bad_interval"}
    except (TypeError, ValueError):
        return {"ok": False, "reason": "bad_interval"}
    return {"ok": True}


def save_custom_job(job: Dict[str, Any]) -> Dict[str, Any]:
    check = validate_job(job)
    if not check["ok"]:
        return check
    norm = normalize_job(job)
    data = load_custom()
    data[norm["id"]] = norm
    _write(data)
    return {"ok": True, "id": norm["id"], "job": norm}


def delete_custom_job(job_id: str) -> Dict[str, Any]:
    data = load_custom()
    if job_id not in data:
        return {"ok": False, "reason": "not_found"}
    data.pop(job_id, None)
    _write(data)
    return {"ok": True}


def list_custom() -> List[Dict[str, Any]]:
    return list(load_custom().values())
