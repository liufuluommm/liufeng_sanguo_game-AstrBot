"""回合制战斗模拟（LoL + 王者荣耀 融合：双防/穿透/暴击/攻速/CDR/韧性/免伤/法力 + 技能效果）。

技能效果「随机抽取实现方式」：每个效果原子可带 `chance`，释放时按概率抽取是否生效。
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from ..core.utils import TROOP_COUNTER
from . import troops as troops_mod

POSITIONS = ["front", "mid", "back"]
_VARIANCE = 0.1
_DEF_K = 120.0  # 防御减免常数：减免 = 防御/(防御+K)

STAT_LABEL = {"atk": "攻击", "def": "防御", "mag_def": "法防", "speed": "速度", "crit": "暴击",
              "crit_dmg": "暴伤", "dodge": "闪避", "lifesteal": "吸血", "spellvamp": "法术吸血",
              "shield": "护盾", "reflect": "反伤", "tenacity": "韧性", "hp": "生命",
              "atkspeed": "攻速", "cdr": "冷却缩减", "reduction": "免伤"}
CTRL_LABEL = {"stun": "眩晕", "knockup": "击飞", "knockback": "击退", "frozen": "冻结",
              "silence": "沉默", "taunt": "嘲讽", "disarm": "缴械", "fear": "恐惧",
              "blind": "致盲", "charm": "魅惑", "suppress": "压制", "slow": "减速"}
DOT_LABEL = {"poison": "中毒", "burn": "灼烧", "bleed": "流血"}


def set_variance(value: float) -> None:
    global _VARIANCE
    try:
        _VARIANCE = max(0.0, float(value))
    except (TypeError, ValueError):
        _VARIANCE = 0.1


def _mitigation(defense: float) -> float:
    defense = max(0.0, defense)
    return defense / (defense + _DEF_K)


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
        self.base_max_hp = int((200 + vitality * 4 + force * 1.0) * star_mult + lv * 8)
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.base_atk = (force * 1.3 + eloquence * 0.3) * star_mult + lv * 2
        self.base_phys_def = (vitality * 0.5 + intellect * 0.3) * star_mult
        self.base_mag_def = (intellect * 0.6 + vitality * 0.3) * star_mult
        self.base_speed = (spd * 1.0 + intellect * 0.2 + force * 0.2) * star_mult
        self.bonus = bonus
        self.charisma = charisma
        self.eloquence = eloquence
        self.base_crit = min(0.40, intellect / 320.0 + charisma / 800.0)
        self.base_crit_dmg = 1.5
        self.base_silence = min(0.35, eloquence / 320.0)
        self.aura = 0.0
        # 兵种附带效果（属性加成 + 开局原子 + 特殊机制）
        self.troop_def = troops_mod.get(self.troop)
        _merged = troops_mod.merge(self.troop_def)
        self.troop_bonus: Dict[str, float] = _merged["bonus"]
        self.troop_opening: List[Dict[str, Any]] = _merged["opening"]
        self.troop_mech: Dict[str, float] = _merged["mechanics"]
        tb = self.troop_bonus
        self.base_max_hp = int(self.base_max_hp * (1 + tb.get("hp", 0.0)))
        self.base_atk *= (1 + tb.get("atk", 0.0))
        self.base_phys_def *= (1 + tb.get("def", 0.0))
        self.base_mag_def *= (1 + tb.get("mag_def", 0.0))
        self.base_speed *= (1 + tb.get("speed", 0.0))
        self.base_crit = min(0.9, self.base_crit + tb.get("crit", 0.0))
        self.base_crit_dmg += tb.get("crit_dmg", 0.0)
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.troop_pen = float(tb.get("pen_flat", 0.0))
        self._troop_mana = int(tb.get("mana", 0.0))
        # 技能
        slots = info.get("skill_slots") or {}
        self.passives: List[Dict[str, Any]] = slots.get("passive") or []
        self.actives: List[Dict[str, Any]] = slots.get("active") or []
        if not self.passives and info.get("skill_passive"):
            self.passives = [info["skill_passive"]]
        if not self.actives and info.get("skill_active"):
            self.actives = [info["skill_active"]]
        self.skill_lv = int(info.get("skill_lv", 1))
        # 法力
        mana_bonus = int(info.get("mana_bonus", 0))
        self.max_mana = 100 + int(intellect * 0.6) + lv * 3 + mana_bonus + self._troop_mana
        self.mana = int(self.max_mana * 0.3)
        self.mana_regen = 8 + int(intellect * 0.05)
        # 状态
        self.buffs: Dict[str, Dict[str, Any]] = {}
        self.dots: List[Dict[str, Any]] = []
        self.hot: List[Dict[str, Any]] = []
        self.control: Dict[str, int] = {}
        self.shield = 0.0
        self.cds: List[int] = [0] * max(1, len(self.actives))
        self.invulnerable = 0
        self.untargetable = 0
        self.alive = True

    # -- 有效属性 ---------------------------------------------------------
    def mult(self, attr: str) -> float:
        b = self.buffs.get(attr)
        return 1.0 + (b["value"] if b else 0.0)

    @property
    def atk(self) -> float:
        base = self.base_atk * self.mult("atk") * (1 + self.aura)
        lh = self.troop_mech.get("low_hp_atk", 0.0)
        if lh and self.max_hp:
            base *= 1 + lh * (1 - self.hp / self.max_hp)
        return base

    @property
    def phys_def(self) -> float:
        return self.base_phys_def * self.mult("def")

    @property
    def mag_def(self) -> float:
        return self.base_mag_def * self.mult("mag_def")

    @property
    def speed(self) -> float:
        return self.base_speed * self.mult("speed")

    @property
    def crit_rate(self) -> float:
        return max(0.0, min(1.0, self.base_crit + self.buff_val("crit")))

    @property
    def crit_dmg(self) -> float:
        return self.base_crit_dmg + self.buff_val("crit_dmg")

    @property
    def lifesteal(self) -> float:
        return max(0.0, self.buff_val("lifesteal") + self.troop_bonus.get("lifesteal", 0.0))

    @property
    def spellvamp(self) -> float:
        return max(0.0, self.buff_val("spellvamp") + self.troop_bonus.get("spellvamp", 0.0))

    @property
    def reflect(self) -> float:
        return max(0.0, self.buff_val("reflect") + self.troop_bonus.get("reflect", 0.0))

    @property
    def reduction(self) -> float:
        return max(0.0, min(0.8, self.buff_val("reduction") + self.troop_bonus.get("reduction", 0.0)))

    @property
    def tenacity(self) -> float:
        return max(0.0, min(0.7, self.buff_val("tenacity") + self.troop_bonus.get("tenacity", 0.0)))

    @property
    def atkspeed(self) -> float:
        return self.mult("atkspeed") + self.troop_bonus.get("atkspeed", 0.0)

    @property
    def cdr(self) -> float:
        return max(0.0, min(0.5, self.buff_val("cdr") + self.troop_bonus.get("cdr", 0.0)))

    @property
    def dodge(self) -> float:
        return max(0.0, min(0.8, self.buff_val("dodge") + self.troop_bonus.get("dodge", 0.0)))

    def buff_val(self, attr: str) -> float:
        b = self.buffs.get(attr)
        return b["value"] if b else 0.0

    def troop_mult(self, enemy: "Combatant") -> float:
        counters = self.troop_def.get("counter") if self.troop_def else None
        if counters is None:
            counters = TROOP_COUNTER.get(self.troop, [])
        if enemy.troop in counters:
            return 1.25
        enemy_counters = enemy.troop_def.get("counter") if enemy.troop_def else None
        if enemy_counters is None:
            enemy_counters = TROOP_COUNTER.get(enemy.troop, [])
        if self.troop in enemy_counters:
            return 0.85
        return 1.0

    def take_damage(self, dmg: int) -> int:
        if self.invulnerable > 0:
            return 0
        if self.shield > 0 and dmg > 0:
            absorbed = min(self.shield, dmg)
            self.shield -= absorbed
            dmg -= absorbed
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return max(0, dmg)

    def heal(self, amount: int) -> None:
        if amount <= 0:
            return
        # 重伤：减疗
        grievous = self.buff_val("grievous")
        if grievous:
            amount = int(amount * (1 - min(0.9, abs(grievous))))
        self.hp = min(self.max_hp, self.hp + amount)

    def add_buff(self, attr: str, value: float, rounds: int) -> None:
        cur = self.buffs.get(attr)
        if cur:
            cur["value"] += value
            cur["rounds"] = max(cur["rounds"], rounds)
        else:
            self.buffs[attr] = {"value": value, "rounds": rounds}

    def add_mana(self, amount: int) -> None:
        self.mana = min(self.max_mana, self.mana + amount)

    def is_cc(self) -> bool:
        return any(k in self.control for k in
                   ("stun", "knockup", "frozen", "suppress", "fear", "taunt"))

    def tick(self) -> None:
        for attr in list(self.buffs.keys()):
            self.buffs[attr]["rounds"] -= 1
            if self.buffs[attr]["rounds"] <= 0:
                self.buffs.pop(attr, None)
        for kind in list(self.control.keys()):
            self.control[kind] -= 1
            if self.control[kind] <= 0:
                self.control.pop(kind, None)
        for dot in list(self.dots):
            self.take_damage(dot["value"])
            dot["rounds"] -= 1
        self.dots = [d for d in self.dots if d["rounds"] > 0]
        for h in list(self.hot):
            self.heal(h["value"])
            h["rounds"] -= 1
        self.hot = [h for h in self.hot if h["rounds"] > 0]
        if self.invulnerable > 0:
            self.invulnerable -= 1
        if self.untargetable > 0:
            self.untargetable -= 1
        self.add_mana(self.mana_regen)


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


def _first_alive(team: List[Combatant], ignore_untargetable: bool = False) -> Optional[Combatant]:
    for c in team:
        if c.alive and (not ignore_untargetable or c.untargetable <= 0):
            return c
    return None


def _alive(team: List[Combatant]) -> List[Combatant]:
    return [c for c in team if c.alive]


def _resolve_targets(actor: Combatant, own: List[Combatant], enemy: List[Combatant],
                     target: str) -> List[Combatant]:
    enemies = [c for c in _alive(enemy) if c.untargetable <= 0] or _alive(enemy)
    allies = _alive(own)
    if target == "self":
        return [actor]
    if target == "ally_all":
        return allies
    if target == "lowest_hp_ally" and allies:
        return [min(allies, key=lambda c: c.hp)]
    if target == "ally_single":
        return [actor]
    if target == "enemy_all":
        return enemies
    if target == "lowest_hp_enemy" and enemies:
        return [min(enemies, key=lambda c: c.hp)]
    if target == "highest_hp_enemy" and enemies:
        return [max(enemies, key=lambda c: c.hp)]
    if target == "random_enemy" and enemies:
        return [random.choice(enemies)]
    first = _first_alive(enemy)
    return [first] if first else []


def _eff_dmg(actor: Combatant, target: Combatant, kind: str, base: float, attr_mult: float,
             pen_flat: float, pen_pct: float, rng: random.Random) -> int:
    raw = base + attr_mult
    raw *= rng.uniform(1 - _VARIANCE, 1 + _VARIANCE)
    if kind == "dmg_true":
        return max(1, int(raw * (1 - target.reduction)))
    if kind == "dmg_magic":
        defense = max(0.0, target.mag_def * (1 - pen_pct) - pen_flat)
        vuln = target.troop_mech.get("magic_vuln", 0.0)
    else:
        defense = max(0.0, target.phys_def * (1 - pen_pct) - pen_flat)
        vuln = 0.0
    raw *= (1 - _mitigation(defense)) * (1 - target.reduction) * (1 + vuln)
    return max(1, int(raw))


def _scale_value(actor: Combatant, skill: Dict[str, Any]) -> float:
    scale = skill.get("scale") or {}
    total = 0.0
    for key, coef in (scale.get("attrs") or {}).items():
        total += {"force": actor.base_atk * 0.8 / 1.3,
                  "intellect": (actor.base_atk * 0.5 + actor.base_mag_def),
                  "vitality": actor.max_hp * 0.02,
                  "charisma": actor.max_hp * 0.015,
                  "eloquence": actor.base_atk * 0.4,
                  "speed": actor.speed * 0.5}.get(key, actor.base_atk * 0.3) * float(coef)
    if scale.get("attr") and not scale.get("attrs"):
        key = scale["attr"]
        coef = float(scale.get("coef", 1.0))
        total += {"force": actor.base_atk / 1.3, "intellect": actor.base_mag_def + actor.base_atk * 0.5,
                  "vitality": actor.max_hp * 0.02}.get(key, actor.base_atk * 0.5) * coef
    return total


def _apply_skill(skill: Dict[str, Any], actor: Combatant, own: List[Combatant],
                 enemy: List[Combatant], rng: random.Random, log: List[str]) -> int:
    """执行技能，返回造成的伤害总量。每个效果可带 chance（随机抽取实现方式）。"""
    if not skill:
        return 0
    total = 0
    lv = max(1, actor.skill_lv)
    lv_mult = 1.0 + 0.06 * (lv - 1)
    formula = skill.get("formula") or {}
    scale_val = _scale_value(actor, skill) * lv_mult
    pen_flat = float(formula.get("pen_flat", 0)) + float(getattr(actor, "troop_pen", 0.0))
    pen_pct = float(formula.get("pen_pct", 0))
    default_target = skill.get("target", "enemy_single")
    for effect in skill.get("effects", []):
        et = effect.get("type")
        p = effect.get("params", {}) or {}
        if "chance" in p and rng.random() > float(p.get("chance", 1.0)):
            continue
        tgt_name = p.get("target", default_target)
        if et in ("dmg_physical", "dmg_magic", "dmg_true"):
            hits = int(p.get("hits", 1))
            base = float(p.get("base", formula.get("base", 0))) * lv_mult
            coef = float(p.get("coef", 0))
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                for _ in range(max(1, hits)):
                    if not tgt.alive:
                        break
                    hp_pct = float(p.get("max_hp_pct", 0)) * tgt.max_hp \
                        + float(p.get("missing_hp_pct", 0)) * (tgt.max_hp - tgt.hp)
                    try:
                        target = _eff_dmg(actor, tgt, et, base + hp_pct,
                                          scale_val * (coef if coef else 1.0), pen_flat, pen_pct, rng)
                    except Exception:  # noqa: BLE001
                        target = max(1, int(base))
                    crit = rng.random() < actor.crit_rate
                    if crit:
                        target = int(target * actor.crit_dmg)
                    applied = tgt.take_damage(target)
                    total += applied
                    actor.add_mana(6)
                    if actor.lifesteal > 0 or (et == "dmg_magic" and actor.spellvamp > 0):
                        drain = actor.lifesteal + (actor.spellvamp if et == "dmg_magic" else 0)
                        actor.heal(int(applied * drain))
                    if tgt.reflect > 0 and tgt.alive:
                        actor.take_damage(int(applied * tgt.reflect))
                    if not tgt.alive:
                        log.append(f"  {actor.name} 用【{skill.get('name','技能')}】击败 {tgt.name}")
                    # 对受控增伤
                    if p.get("bonus_vs_cc") and tgt.alive and tgt.is_cc():
                        extra = tgt.take_damage(int(applied * float(p["bonus_vs_cc"])))
                        total += extra
        elif et == "heal":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.heal(int((float(p.get("base", 60)) * lv_mult) + scale_val * float(p.get("coef", 0))))
        elif et == "regen":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.hot.append({"value": int(float(p.get("value", 0.08)) * tgt.max_hp),
                                "rounds": int(p.get("rounds", 3))})
        elif et == "buff":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.add_buff(p.get("attr", "atk"), float(p.get("value", 0.15)), int(p.get("rounds", 3)))
        elif et == "debuff":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                attr = p.get("attr", "atk")
                if attr in ("shred_def", "shred_mag"):
                    tgt.add_buff("def" if attr == "shred_def" else "mag_def",
                                 -abs(float(p.get("value", 0.2))), int(p.get("rounds", 3)))
                else:
                    tgt.add_buff(attr, -abs(float(p.get("value", 0.15))), int(p.get("rounds", 3)))
        elif et == "dot":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.dots.append({"kind": p.get("kind", "burn"),
                                 "value": int(float(p.get("value", 0.05)) * tgt.max_hp),
                                 "rounds": int(p.get("rounds", 3))})
        elif et == "control":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                if rng.random() < float(p.get("chance", 0.5)) * (1 - tgt.tenacity):
                    tgt.control[p.get("kind", "stun")] = int(p.get("rounds", 1))
        elif et == "shield":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.shield += float(p.get("value", 0.15)) * tgt.max_hp
        elif et == "cleanse":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.dots = []
                tgt.control = {k: v for k, v in tgt.control.items() if k == "taunt"}
        elif et == "dispel":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                tgt.buffs = {k: v for k, v in tgt.buffs.items() if v["value"] < 0}
        elif et == "invulnerable":
            actor.invulnerable = int(p.get("rounds", 1))
        elif et == "untargetable":
            actor.untargetable = int(p.get("rounds", 1))
        elif et == "revive":
            for tgt in own:
                if not tgt.alive:
                    tgt.alive = True
                    tgt.hp = int(tgt.max_hp * float(p.get("hp", 0.3)))
                    break
        elif et == "execute":
            for tgt in _resolve_targets(actor, own, enemy, tgt_name):
                if tgt.alive and tgt.hp <= tgt.max_hp * float(p.get("threshold", 0.25)):
                    total += tgt.take_damage(tgt.hp + 1)
                    log.append(f"  {actor.name} 斩杀 {tgt.name}")
        # combo/pursuit/counter/summon/reduction 等由循环或 buff 处理
    return total


def simulate(team_a: List[Dict[str, Any]], team_b: List[Dict[str, Any]],
             bonus_a: float = 0.0, bonus_b: float = 0.0,
             rng: random.Random = random, max_rounds: int = 40) -> Dict[str, Any]:
    a = _build(team_a, bonus_a)
    b = _build(team_b, bonus_b)
    log: List[str] = []
    dmg_a = dmg_b = 0

    for team in (a, b):
        if team:
            avg_cha = sum(c.charisma for c in team) / len(team)
            for c in team:
                c.aura = min(0.25, avg_cha * 0.002)

    # 被动/光环 + 兵种开局效果：开局生效
    for team, enemy_team in ((a, b), (b, a)):
        for c in team:
            if c.troop_opening:
                _apply_skill({"name": "兵种·" + c.troop_def.get("name", ""),
                              "effects": c.troop_opening, "target": "self"},
                             c, team, enemy_team, rng, log)
            for pdef in c.passives:
                _apply_skill(pdef, c, team, enemy_team, rng, log)

    log.append(f"⚔️ {a[0].name if a else '?'} 军 VS {b[0].name if b else '?'} 军")

    rnd = 0
    for rnd in range(1, max_rounds + 1):
        if _first_alive(a) is None or _first_alive(b) is None:
            break
        order = sorted(
            _alive(a) + _alive(b),
            key=lambda c: c.speed + (1000.0 if (rnd == 1 and c.troop_mech.get("first_strike", 0)) else 0.0),
            reverse=True,
        )
        for attacker in order:
            if not attacker.alive or attacker.is_cc():
                continue
            own = a if attacker in a else b
            enemy_team = b if own is a else a
            target = _first_alive(enemy_team)
            if target is None:
                break
            # 普攻（一回合可多次：攻速 / 兵种追加一击）
            swings = 1 + (1 if rng.random() < (attacker.atkspeed - 1.0) else 0)
            if rng.random() < attacker.troop_mech.get("extra_hit_chance", 0.0):
                swings += 1
            for _ in range(swings):
                target = _first_alive(enemy_team)
                if target is None:
                    break
                mult = attacker.troop_mult(target)
                raw = attacker.atk * mult * rng.uniform(1 - _VARIANCE, 1 + _VARIANCE) * (1 + attacker.bonus)
                dmg = max(1, int(raw - target.phys_def * 0.5))
                if rng.random() < attacker.crit_rate:
                    dmg = int(dmg * attacker.crit_dmg)
                if target.dodge > 0 and rng.random() < target.dodge:
                    applied = 0
                else:
                    applied = target.take_damage(dmg)
                attacker.add_mana(6)
                if own is a:
                    dmg_a += applied
                else:
                    dmg_b += applied
                if target.reflect > 0 and target.alive and applied > 0:
                    attacker.take_damage(int(applied * target.reflect))
                if target.alive and rng.random() < attacker.troop_mech.get("knockup_chance", 0.0):
                    target.control["knockup"] = 1
                if not target.alive:
                    log.append(f"  {attacker.name} 击败 {target.name}")
            # 主动技能
            if "silence" not in attacker.control:
                for i, sk in enumerate(attacker.actives):
                    if i >= len(attacker.cds) or attacker.cds[i] > 0:
                        continue
                    cost = int((sk.get("formula") or {}).get("mana_cost", sk.get("mana_cost", 30)))
                    if attacker.mana < cost or rng.random() > float(sk.get("chance", 0.35)):
                        continue
                    attacker.mana -= cost
                    d = _apply_skill(sk, attacker, own, enemy_team, rng, log)
                    if own is a:
                        dmg_a += d
                    else:
                        dmg_b += d
                    cd = int(sk.get("cooldown", 0))
                    attacker.cds[i] = max(0, round(cd * (1 - attacker.cdr)))
                    break
            # 口才：概率削弱目标攻击
            if target.alive and rng.random() < attacker.base_silence:
                target.add_buff("atk", -0.2, 99)

        for team in (a, b):
            for c in _alive(team):
                c.tick()
                for i in range(len(c.cds)):
                    if c.cds[i] > 0:
                        c.cds[i] -= 1

    a_alive = _first_alive(a) is not None
    b_alive = _first_alive(b) is not None
    if a_alive and not b_alive:
        winner = "a"
    elif b_alive and not a_alive:
        winner = "b"
    else:
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
