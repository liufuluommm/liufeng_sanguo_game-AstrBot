"""GM 操作审计与回滚快照。

审计日志保存到 global/audit.json（保留最近 N 条）。
可逆操作的玩家快照保存到 global/snapshots/<op_id>.json。
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from . import storage

_AUDIT_FILE = "audit"
_SNAPSHOT_DIR = "snapshots"
_MAX_RECORDS = 2000


def _now() -> int:
    return int(time.time())


def snapshot(qq: str, data: Dict[str, Any]) -> str:
    """保存玩家快照，返回快照 id。"""
    snap_id = uuid.uuid4().hex[:12]
    storage.save_global(f"{_SNAPSHOT_DIR}/{snap_id}", {"qq": qq, "data": data, "ts": _now()})
    return snap_id


def load_snapshot(snap_id: str) -> Optional[Dict[str, Any]]:
    return storage.load_global(f"{_SNAPSHOT_DIR}/{snap_id}", None)


def log(
    operator: str,
    action: str,
    target: str = "",
    params: Any = None,
    result: str = "",
    reversible: bool = False,
    before_snapshot: str = "",
    after_snapshot: str = "",
) -> str:
    """写一条审计记录，返回 op_id。"""
    op_id = uuid.uuid4().hex[:12]
    record = {
        "op_id": op_id,
        "ts": _now(),
        "operator": operator,
        "action": action,
        "target": target,
        "params": params,
        "result": result,
        "reversible": reversible,
        "before": before_snapshot,
        "after": after_snapshot,
    }
    records: List[Dict[str, Any]] = storage.load_global(_AUDIT_FILE, []) or []
    records.append(record)
    if len(records) > _MAX_RECORDS:
        records = records[-_MAX_RECORDS:]
    storage.save_global(_AUDIT_FILE, records)
    return op_id


def recent(limit: int = 20) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = storage.load_global(_AUDIT_FILE, []) or []
    return records[-limit:][::-1]


def find(op_id: str) -> Optional[Dict[str, Any]]:
    records: List[Dict[str, Any]] = storage.load_global(_AUDIT_FILE, []) or []
    for rec in records:
        if rec.get("op_id") == op_id:
            return rec
    return None


def mark_rolled_back(op_id: str) -> None:
    records: List[Dict[str, Any]] = storage.load_global(_AUDIT_FILE, []) or []
    for rec in records:
        if rec.get("op_id") == op_id:
            rec["rolled_back"] = True
    storage.save_global(_AUDIT_FILE, records)
