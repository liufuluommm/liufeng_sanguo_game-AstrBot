"""限时活动：四类全局 buff（双倍掉落/金币/经验、免行动力）。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import storage

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
_STATE = "events_state"
_ENABLED = True
BUFF_LABEL = {
    "double_drop": "掉落翻倍",
    "double_gold": "金币翻倍",
    "double_exp": "经验翻倍",
    "free_stamina": "免行动力",
}


def set_enabled(flag: bool) -> None:
    global _ENABLED
    _ENABLED = bool(flag)


def enabled() -> bool:
    return _ENABLED


def defs() -> List[Dict[str, Any]]:
    path = TABLES_DIR / "events.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _load_state() -> Dict[str, Any]:
    data = storage.load_global(_STATE, None)
    if data is None:
        data = {"active": {}}
        storage.save_global(_STATE, data)
    data.setdefault("active", {})
    return data


def _save_state(data: Dict[str, Any]) -> None:
    storage.save_global(_STATE, data)


def prune() -> None:
    data = _load_state()
    now = int(time.time())
    changed = False
    for eid in list(data["active"].keys()):
        if int(data["active"][eid].get("end_ts", 0)) <= now:
            data["active"].pop(eid, None)
            changed = True
    if changed:
        _save_state(data)


def active_events() -> List[Dict[str, Any]]:
    if not _ENABLED:
        return []
    prune()
    data = _load_state()
    out = []
    for eid, st in data["active"].items():
        definition = next((d for d in defs() if d["id"] == eid), None)
        if definition:
            item = dict(definition)
            item["end_ts"] = st.get("end_ts")
            out.append(item)
    return out


def is_active(buff_type: str) -> bool:
    return any(e.get("buff_type") == buff_type for e in active_events())


def multiplier(buff_type: str, default: float = 1.0) -> float:
    return 2.0 if is_active(buff_type) else default


def free_stamina() -> bool:
    return is_active("free_stamina")


def open_event(event_id: str, duration: Optional[int] = None) -> Dict[str, Any]:
    definition = next((d for d in defs() if d["id"] == event_id), None)
    if definition is None:
        return {"ok": False, "reason": "not_found"}
    duration = int(duration) if duration else int(definition.get("duration", 3600))
    data = _load_state()
    now = int(time.time())
    data["active"][event_id] = {"start_ts": now, "end_ts": now + duration}
    _save_state(data)
    return {"ok": True, "event": definition, "duration": duration}


def close_event(event_id: str) -> Dict[str, Any]:
    data = _load_state()
    if event_id not in data["active"]:
        return {"ok": False, "reason": "not_active"}
    data["active"].pop(event_id, None)
    _save_state(data)
    return {"ok": True}
