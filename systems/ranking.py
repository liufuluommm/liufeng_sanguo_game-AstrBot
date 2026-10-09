"""排行榜。"""

from __future__ import annotations

from typing import Any, Dict, List

from ..core import storage

from . import player as player_mod


def power_ranking(limit: int = 10) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for qq, data in storage.iter_players():
        try:
            power = player_mod.total_power(data)
            rows.append({
                "qq": qq,
                "name": data.get("name", qq),
                "power": power,
                "count": len(player_mod.owned_names(data)),
                "win": int(data.get("win", 0)),
                "lose": int(data.get("lose", 0)),
            })
        except Exception:  # noqa: BLE001
            continue
    rows.sort(key=lambda r: r["power"], reverse=True)
    return rows[:limit]
