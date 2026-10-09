"""生成战令数据表 tables/battlepass.json。运行：python tools/build_battlepass.py"""

from __future__ import annotations

import json
from pathlib import Path

TABLES = Path(__file__).resolve().parent.parent / "tables"

MAX_LEVEL = 50


def req(level: int) -> int:
    return 1000 + (level - 1) * 200


def main():
    rows = []
    for level in range(1, MAX_LEVEL + 1):
        free = {"gold": 300 + level * 80}
        if level % 5 == 0:
            free["fragment"] = 2
        premium = {"diamond": 10 if level % 5 == 0 else 3}
        if level % 10 == 0:
            premium["event_ticket"] = 2
        if level == MAX_LEVEL:
            premium["title"] = "赛季霸主"
        rows.append({
            "level": level,
            "exp": req(level),
            "free": free,
            "premium": premium,
        })
    data = {
        "season_name": "三国·群雄逐鹿",
        "max_level": MAX_LEVEL,
        "duration_days": 30,
        "premium_cost": 50,
        "levels": rows,
    }
    (TABLES / "battlepass.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"battlepass.json: {len(rows)} 级")


if __name__ == "__main__":
    main()
