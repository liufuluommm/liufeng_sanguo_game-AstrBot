"""3v3 回合制战斗模拟。"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from ..core.utils import TROOP_COUNTER

POSITIONS = ["front", "mid", "back"]
_VARIANCE = 0.1


def set_variance(value: float) -> None:
    global _VARIANCE
    try:
        _VARIANCE = max(0.0, float(value))
    except (TypeError, ValueError):
        _VARIANCE = 0.1


class Combatant:
    def __init__(self, name: str, info: Dict[str, Any], level: int = 1, star: int = 1,
                 bonus: float = 0.0):
        self.name = name
        self.troop = info.get("troop", "infantry")
        force = int(info.get("force", 0))
        intellect = int(info.get("intellect", 0))
        vitality = int(info.get("vitality", info.get("lead", 60)))
        charisma = int(info.get("charisma", 60))
        eloquence = int(info.get("eloquence", 60))
        spd = int(info.get("speed", 60))
        star_mult = 1.0 + 0.15 * max(0, star - 1)
        lv = max(1, level)
        self.max_hp = int((200 + vitality * 4 + force * 1.0) * star_mult + lv * 8)
        self.hp = self.max_hp
        self.atk = (force * 1.3 + eloquence * 0.3) * star_mult + lv * 2
        self.defense = (intellect * 0.6 + vitality * 0.4) * star_mult
        self.speed = (spd * 1.0 + intellect * 0.2 + force * 0.2) * star_mult
        self.bonus = bonus
        self.charisma = charisma
        self.eloquence = eloquence
        self.crit_rate = min(0.40, intellect / 320.0 + charisma / 800.0)
        self.silence_rate = min(0.35, eloquence / 320.0)
        self.aura = 0.0  # 团队魅力光环（simulate 中统一计算）
        self.disarmed = False  # 被口才“说服”削弱
        self.skill_name = info.get("skill_name", "")
        self.alive = True

    def troop_mult(self, enemy: "Combatant") -> float:
        if enemy.troop in TROOP_COUNTER.get(self.troop, []):
            return 1.25
        if self.troop in TROOP_COUNTER.get(enemy.troop, []):
            return 0.85
        return 1.0

    def take_damage(self, dmg: int) -> None:
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False


def _build(team: List[Dict[str, Any]], bonus: float) -> List[Combatant]:
    out = []
    for entry in team:
        info = entry.get("info", entry)
        out.append(Combatant(
            entry.get("name", info.get("name", "?")),
            info,
            entry.get("level", 1),
            entry.get("star", 1),
            bonus,
        ))
    return out


def _first_alive(team: List[Combatant]) -> Optional[Combatant]:
    for c in team:
        if c.alive:
            return c
    return None


def simulate(team_a: List[Dict[str, Any]], team_b: List[Dict[str, Any]],
             bonus_a: float = 0.0, bonus_b: float = 0.0,
             rng: random.Random = random, max_rounds: int = 30) -> Dict[str, Any]:
    a = _build(team_a, bonus_a)
    b = _build(team_b, bonus_b)
    log: List[str] = []
    dmg_a = dmg_b = 0

    # 魅力团队光环：按队伍平均魅力提升攻防（上限 25%）
    for team in (a, b):
        if team:
            avg_cha = sum(c.charisma for c in team) / len(team)
            for c in team:
                c.aura = min(0.25, avg_cha * 0.002)

    log.append(f"⚔️ {a[0].name if a else '?'} 军 VS {b[0].name if b else '?'} 军")

    for rnd in range(1, max_rounds + 1):
        if _first_alive(a) is None or _first_alive(b) is None:
            break
        order = sorted(
            [c for c in a if c.alive] + [c for c in b if c.alive],
            key=lambda c: c.speed,
            reverse=True,
        )
        for attacker in order:
            if not attacker.alive:
                continue
            own = a if attacker in a else b
            enemy_team = b if own is a else a
            target = _first_alive(enemy_team)
            if target is None:
                break
            mult = attacker.troop_mult(target)
            variance = rng.uniform(1 - _VARIANCE, 1 + _VARIANCE)
            eff_atk = attacker.atk * (1 + attacker.aura)
            if attacker.disarmed:
                eff_atk *= 0.8
            raw = eff_atk * mult * variance * (1 + attacker.bonus)
            dmg = max(1, int(raw - target.defense * 0.5))
            tags = []
            # 智力暴击
            if rng.random() < attacker.crit_rate:
                dmg = int(dmg * 1.5)
                tags.append("暴击")
            # 主动技能概率触发，造成额外伤害
            if attacker.skill_name and rng.random() < 0.25:
                dmg = int(dmg * 1.4)
                tags.append("技能")
            target.take_damage(dmg)
            # 口才：概率“说服”削弱目标攻击
            if not target.disarmed and rng.random() < attacker.silence_rate:
                target.disarmed = True
                tags.append("说服")
            if own is a:
                dmg_a += dmg
            else:
                dmg_b += dmg
            mark = f"（{'/'.join(tags)}）" if tags else ""
            if not target.alive:
                log.append(f"  {attacker.name} 击败 {target.name}{mark}")
            if _first_alive(enemy_team) is None:
                break

    a_alive = _first_alive(a) is not None
    b_alive = _first_alive(b) is not None
    if a_alive and not b_alive:
        winner = "a"
    elif b_alive and not a_alive:
        winner = "b"
    else:
        # 未分胜负时按剩余血量比例判定
        a_hp = sum(c.hp for c in a)
        b_hp = sum(c.hp for c in b)
        winner = "a" if a_hp > b_hp else "b" if b_hp > a_hp else "draw"

    return {
        "winner": winner,
        "rounds": rnd,
        "log": log,
        "damage_a": dmg_a,
        "damage_b": dmg_b,
        "a_alive": [c.name for c in a if c.alive],
        "b_alive": [c.name for c in b if c.alive],
    }
