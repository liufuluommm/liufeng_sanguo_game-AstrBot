"""柳弗罗三国演义 —— 插件入口。"""

from __future__ import annotations

import random
import re
import sys
import time
from typing import Any, Dict, List, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

try:
    import astrbot.api.message_components as Comp
except Exception:  # pragma: no cover
    Comp = None

try:
    from astrbot.api import AstrBotConfig
except Exception:  # pragma: no cover
    AstrBotConfig = dict

from .core import audit, maintenance, security, storage
from .core.config import GameConfig
from .core.scheduler import Scheduler
from .core.utils import (
    FACTION_LABEL,
    RARITY_LABEL,
    TROOP_LABEL,
    base_power,
    fmt_duration,
    general_power,
    progress_bar,
    sep,
)
from .systems import battle as battle_sys
from .systems import building, collection, cultivate, gacha, ranking, team
from .systems import equipment as equip_sys
from .systems import dungeon as dungeon_sys
from .systems import inventory as inventory_sys
from .systems import items as items_mod
from .systems import generals_admin as generals_admin_mod
from .systems import shop as shop_sys
from .systems import exchange as exchange_sys
from .systems import auction as auction_sys
from .systems import buff as buff_sys
from .systems import faction as faction_sys
from .systems import guild as guild_sys
from .systems import social as social_sys
from .systems import quest as quest_sys
from .systems import mail as mail_sys
from .systems import render as render_sys
from .systems import worldboss as worldboss_sys
from .systems import battlepass as battlepass_sys
from .systems import events as events_sys
from .systems import player as player_mod
from .systems.tables import tables

EMOJI = {
    "gold": "💰", "star": "⭐", "fire": "⚔️", "ok": "✅", "no": "⚠️",
    "win": "🎉", "lose": "😢", "frag": "🧩", "dorm": "🏠", "sign": "📅",
    "rank": "🏆", "shop": "🏪", "book": "📖",
}


def equipment_stats_text(eq: Dict[str, Any]) -> str:
    return f"武{eq.get('force', 0)} 智{eq.get('intellect', 0)} 统{eq.get('lead', 0)}"


class LiuFengSanGuoGame(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.cfg = GameConfig(config if config is not None else {})
        try:
            storage.set_plugin_name(getattr(self, "name", "") or "")
        except Exception:  # noqa: BLE001
            pass
        events_sys.set_enabled(self.cfg.get("events.enable", True))
        battlepass_sys.set_enabled(self.cfg.get("battlepass.enable", True))
        battle_sys.set_variance(self.cfg.get("game.battle_variance", 0.1))
        dungeon_sys.set_drop_bounds(
            self.cfg.get("dungeon.fragment_drop_min", 0.05),
            self.cfg.get("dungeon.fragment_drop_max", 0.15),
        )
        tables()  # 预加载
        self.scheduler = Scheduler()
        self._scheduler_started = False
        self._register_jobs()
        self._register_web_api()
        logger.info("柳弗罗三国演义游戏插件加载成功")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    @filter.on_astrbot_loaded()
    async def _on_astrbot_loaded(self):
        """Bot 初始化完成后启动调度器（事件钩子不可与指令装饰器混用）。"""
        self._start_scheduler()

    def _start_scheduler(self) -> None:
        if self._scheduler_started:
            return
        if not self.cfg.get("system.enable_scheduler", True):
            return
        try:
            self.scheduler.start()
            self._scheduler_started = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[三国] 调度器启动失败: {exc}")

    async def terminate(self):
        await self.scheduler.stop()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _sender(self, event: AstrMessageEvent):
        return str(event.get_sender_id()), event.get_sender_name()

    def _at_ids(self, event: AstrMessageEvent) -> List[str]:
        result: List[str] = []
        try:
            message = getattr(event.message_obj, "message", []) or []
            for seg in message:
                if Comp is not None and isinstance(seg, Comp.At):
                    qq = getattr(seg, "qq", None) or getattr(seg, "user_id", None)
                    if qq:
                        result.append(str(qq))
        except Exception:  # noqa: BLE001
            pass
        if not result:
            # 兜底：部分平台（如 QQ 官方接口）不支持下发 At 段，退化为从纯文本提取数字 QQ
            text = getattr(event, "message_str", "") or ""
            result = re.findall(r"\d{5,12}", text)
        return result

    def _is_super_admin(self, event: AstrMessageEvent) -> bool:
        """超级管理员判定：admin.super_admins 白名单；为空则所有管理员视为超管。"""
        supers = self.cfg.get("admin.super_admins", []) or []
        if not supers:
            return True
        qq = str(event.get_sender_id())
        return qq in [str(x) for x in supers]

    def _admin_allowed(self) -> bool:
        """管理台接口鉴权：admin.web_admins 白名单；为空则仅要求登录态。"""
        try:
            from astrbot.api.web import request
        except Exception:  # noqa: BLE001
            return True
        admins = self.cfg.get("admin.web_admins", []) or []
        if not admins:
            return True
        return str(getattr(request, "username", "") or "") in [str(x) for x in admins]

    def _track_session(self, event: AstrMessageEvent) -> None:
        if not self.cfg.get("system.enable_push", True):
            return
        try:
            umo = getattr(event, "unified_msg_origin", "")
            if not umo:
                return
            platform = ""
            fn = getattr(event, "get_platform_name", None)
            if callable(fn):
                try:
                    platform = str(fn() or "")
                except Exception:  # noqa: BLE001
                    platform = ""
            sessions = storage.load_global("session_index", {}) or {}
            if not isinstance(sessions.get(umo), dict):
                sessions[umo] = {"umo": umo, "platform": platform}
                storage.save_global("session_index", sessions)
        except Exception:  # noqa: BLE001
            pass

    def _guard(self, event: AstrMessageEvent, cooldown: Optional[float] = None,
               cmd: str = "") -> Optional[str]:
        """守卫：返回 None=放行、""=静默拦截、非空文本=提示拦截。"""
        if not self.cfg.get("enable", True):
            return "⚠️ 三国演义游戏当前已停用。"
        if maintenance.is_on():
            return maintenance.message()
        self._start_scheduler()  # 兜底：确保调度器已启动
        self._track_session(event)
        if not cmd:
            try:
                cmd = sys._getframe(1).f_code.co_name
            except Exception:  # noqa: BLE001
                cmd = "default"
        cd = self.cfg.get("system.cooldown_default", 1.5) if cooldown is None else cooldown
        if cd and cd > 0:
            qq = str(event.get_sender_id())
            ok, _remain = security.check_cooldown(f"{qq}:{cmd}", cd)
            if not ok:
                return ""  # 静默拦截
        return None

    def _progress(self, player: Dict[str, Any], event: str, amount: int = 1) -> None:
        try:
            quest_sys.progress_event(player, event, amount)
        except Exception:  # noqa: BLE001
            pass
        try:
            mult = events_sys.multiplier("double_exp")
            per = int(self.cfg.get("battlepass.exp_per_point", 50))
            battlepass_sys.add_exp(player, int(amount * per * mult))
        except Exception:  # noqa: BLE001
            pass

    def _initial_gold(self) -> int:
        return int(self.cfg.get("game.initial_gold", 1000))

    def _dorm_capacity(self) -> int:
        return int(self.cfg.get("gacha.dorm_initial_capacity", 15))

    def _team_entries(self, player: Dict[str, Any]) -> List[Dict[str, Any]]:
        names = [n for n in player.get("team", []) if player_mod.has_general(player, n)]
        if not names:
            names = [e["name"] for e in player_mod.all_generals_power(player)[:3]]
        entries = []
        for name in names[:3]:
            info = player_mod.general_info(player, name)
            if info:
                entries.append({
                    "name": name,
                    "info": info,
                    "level": info.get("level", 1),
                    "star": info.get("star", 1),
                })
        return entries

    def _duel_entry(self, player: Dict[str, Any]):
        """1v1 出战单将：主将 → 阵容首位 → 战力最高。"""
        return team.duel_entry(player)

    # ------------------------------------------------------------------
    # 定时任务
    # ------------------------------------------------------------------
    def _register_jobs(self):
        self.scheduler.add_job("stamina_recovery", self._job_stamina, 120)
        self.scheduler.add_job("auction_settle", self._job_auction, 60)
        self.scheduler.add_job("events_prune", self._job_events, 120)
        self.scheduler.add_job("worldboss_watch", self._job_worldboss, 300)
        self.scheduler.add_job("housekeeping", self._job_housekeeping, 3600)

    async def _job_stamina(self):
        max_st = int(self.cfg.get("stamina.max", 120))
        interval = int(self.cfg.get("stamina.recover_interval", 300))
        amount = int(self.cfg.get("stamina.recover_amount", 1))
        for _qq, data in storage.iter_players():
            before = int(data.get("stamina", 0))
            player_mod.apply_stamina_recovery(data, max_st, interval, amount)
            if int(data.get("stamina", 0)) != before:
                player_mod.save(data)

    async def _job_housekeeping(self):
        logger.info("[三国] 定时巡检完成")

    async def _job_auction(self):
        try:
            auction_sys.settle()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[三国] 拍卖结算失败: {exc}")

    async def _job_events(self):
        try:
            events_sys.prune()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[三国] 活动巡检失败: {exc}")

    async def _job_worldboss(self):
        try:
            worldboss_sys.current()  # 内部会对到期 BOSS 自动结算
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[三国] 世界BOSS巡检失败: {exc}")

    # ------------------------------------------------------------------
    # 基础指令
    # ------------------------------------------------------------------
    @filter.command("注册")
    async def register(self, event: AstrMessageEvent):
        """注册游戏账号"""
        guard = self._guard(event, cooldown=0)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, name = self._sender(event)
        if player_mod.load(qq) is not None:
            yield event.plain_result(f"⚠️ {name}，你已经注册过了！发送 /武将 查看你的武将。")
            return
        player = player_mod.get_or_create(qq, name, self._initial_gold(), self._dorm_capacity())
        player_mod.save(player)
        yield event.plain_result(
            f"🎉 恭喜 {name} 加入三国乱世！\n"
            f"💰 初始金币：{player['gold']}\n"
            f"{sep()}\n"
            f"📜 常用指令：\n"
            f"  /签到  每日领金币\n"
            f"  /兑换  碎片换武将\n"
            f"  /架空招募  金币招募架空武将\n"
            f"  自由武将招募 <名字>  创建自定义武将\n"
            f"  /武将  查看武将   /排行  战力榜\n"
            f"  /帮助  全部玩法"
        )

    @filter.command("签到")
    async def sign_in(self, event: AstrMessageEvent):
        """每日签到领金币"""
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, name = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册 开始游戏。")
            return
        today = time.strftime("%Y-%m-%d")
        if player.get("sign_date") == today:
            yield event.plain_result(f"⚠️ {name}，今天已经签到过了，明天再来。")
            return
        lo = int(self.cfg.get("game.signin_min", 100))
        hi = int(self.cfg.get("game.signin_max", 300))
        reward = int(random.randint(lo, hi) * events_sys.multiplier("double_gold"))
        player_mod.add_gold(player, reward)
        player["sign_date"] = today
        player["sign_streak"] = int(player.get("sign_streak", 0)) + 1
        player_mod.save(player)
        self._progress(player, "signin")
        yield event.plain_result(
            f"📅 签到成功！\n👤 {name}\n💰 +{reward} 金币\n"
            f"🔥 连签：{player['sign_streak']} 天\n💵 当前金币：{player['gold']}"
        )

    @filter.command("帮助")
    async def help_cmd(self, event: AstrMessageEvent):
        """查看游戏玩法帮助"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        yield event.plain_result(
            f"📖 柳弗罗三国演义 · 玩法\n{sep()}\n"
            f"【基础】/注册 /签到 /帮助 /商城\n"
            f"【招募】/兑换(碎片) /架空招募 /架空十连 /碎片\n"
            f"         自由武将招募 <名字>(无前缀)\n"
            f"【武将】/武将 /培养 /升星 /技能 /图鉴 /合成 /遣散\n"
            f"【建筑】/宿舍 /宿舍升级\n"
            f"【战斗】/阵容 /上阵 /下阵 /主将 /对战 @玩家 /切磋 @玩家 /副本 /挑战 /排行\n"
            f"【装备】/装备 /锻造 /穿戴 /强化\n"
            f"【势力】/势力 /加入 /捐献 /势力战\n"
            f"【任务】/任务 /成就 /领取\n{sep()}\n"
            f"💡 收集历代名将，一统三国！"
        )

    @filter.command("商城")
    async def shop(self, event: AstrMessageEvent):
        """查看商城（道具由管理员上架）"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        yield event.plain_result(
            f"🏪 三国商城\n{sep()}\n"
            f"📌 商品由管理员在 WebUI「道具工坊」上架。\n"
            f"💰 金币/元宝/功勋等货币购买，购买后进入背包。\n"
            f"🎁 更多系统：每日商店 / 黑市 / 限时 / 兑换所 / 拍卖行（开发中）。"
        )

    @filter.command("碎片")
    async def fragments(self, event: AstrMessageEvent):
        """查看通用武将碎片"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        need = int(self.cfg.get("gacha.fragment_exchange_cost", 15))
        frag = int(player.get("fragments", 0))
        yield event.plain_result(
            f"🧩 通用武将碎片：{frag}\n"
            f"{progress_bar(frag, need)} {min(frag, need)}/{need}\n"
            f"发送 /兑换 消耗 {need} 碎片随机兑换一名历史武将。"
        )

    @filter.command("兑换")
    async def exchange(self, event: AstrMessageEvent):
        """用碎片随机兑换历史武将"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        cost = int(self.cfg.get("gacha.fragment_exchange_cost", 15))
        result = gacha.exchange_historical(player, cost, self.cfg.rarity_rates())
        if not result["ok"]:
            yield event.plain_result(
                f"⚠️ 碎片不足！需要 {cost} 个，你只有 {result.get('fragments', 0)} 个。\n"
                f"碎片可在副本 PVE 掉落获得。"
            )
            return
        info = tables().get(result["general"]) or {}
        dup = "（重复，自动升星）" if result["duplicate"] else "（新武将！）"
        self._progress(player, "gacha")
        if not result["duplicate"]:
            self._progress(player, "general_obtain")
        yield event.plain_result(
            f"🎴 兑换成功！【{result['general']}】{dup}\n"
            f"品质：{RARITY_LABEL.get(result['rarity'], result['rarity'])} · "
            f"{FACTION_LABEL.get(info.get('faction', ''), '')}\n"
            f"⚔️武力 {info.get('force')}  📖智力 {info.get('intellect')}  👑统帅 {info.get('lead')}\n"
            f"💪战力 {base_power(info)}\n"
            f"🧩 剩余碎片：{result['fragments_left']}"
        )

    @filter.command("架空招募")
    async def fictional_recruit(self, event: AstrMessageEvent):
        """金币招募架空武将（有失败率）"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        yield event.plain_result(self._do_fictional(event))

    @filter.command("架空十连")
    async def fictional_recruit_ten(self, event: AstrMessageEvent):
        """连续十次架空招募"""
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        cost = int(self.cfg.get("gacha.fictional_cost", 5000))
        fmin = float(self.cfg.get("gacha.fictional_fail_min", 0.25))
        fmax = float(self.cfg.get("gacha.fictional_fail_max", 0.30))
        rates = self.cfg.rarity_rates()
        lines = [f"🎴 架空十连招募（每次 {cost} 金币）", sep()]
        success = fail = 0
        for i in range(1, 11):
            if int(player.get("gold", 0)) < cost:
                lines.append(f"  {i}. 💰 金币不足，停止。")
                break
            res = gacha.recruit_fictional(player, cost, fmin, fmax, rates)
            if res["ok"]:
                success += 1
                tag = "重复升星" if res["duplicate"] else "新武将"
                lines.append(f"  {i}. ✅ {RARITY_LABEL.get(res['rarity'])} 【{res['general']}】({tag})")
            else:
                fail += 1
                lines.append(f"  {i}. ❌ 招募失败")
        lines.append(sep())
        lines.append(f"成功 {success} 次，失败 {fail} 次，剩余金币 {player.get('gold', 0)}")
        self._progress(player, "gacha", success + fail)
        yield event.plain_result("\n".join(lines))

    def _do_fictional(self, event: AstrMessageEvent) -> str:
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            return "⚠️ 你还没有注册！发送 /注册。"
        cost = int(self.cfg.get("gacha.fictional_cost", 5000))
        fmin = float(self.cfg.get("gacha.fictional_fail_min", 0.25))
        fmax = float(self.cfg.get("gacha.fictional_fail_max", 0.30))
        res = gacha.recruit_fictional(player, cost, fmin, fmax, self.cfg.rarity_rates())
        if not res["ok"]:
            if res.get("reason") == "gold":
                return f"⚠️ 金币不足！需要 {cost}，你只有 {res.get('gold', 0)}。"
            self._progress(player, "gacha")
            return (
                f"😢 招募失败！（本次失败率 {res.get('fail_rate', 0)*100:.1f}%）\n"
                f"💰 剩余金币：{res.get('gold_left', 0)}"
            )
        info = tables().get(res["general"]) or {}
        dup = "（重复升星）" if res["duplicate"] else "（新武将！）"
        self._progress(player, "gacha")
        if not res["duplicate"]:
            self._progress(player, "general_obtain")
        return (
            f"🎴 【架空】招募成功！{dup}\n"
            f"品质：{RARITY_LABEL.get(res['rarity'])} 【{res['general']}】\n"
            f"⚔️武力 {info.get('force')}  📖智力 {info.get('intellect')}  👑统帅 {info.get('lead')}\n"
            f"💪战力 {base_power(info)}\n💰 剩余金币：{res['gold_left']}"
        )

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_free_recruit(self, event: AstrMessageEvent):
        """无前缀触发：自由武将招募 <名字>"""
        text = (event.message_str or "").strip().lstrip("/")
        keyword = "自由武将招募"
        if not text.startswith(keyword):
            return
        name = text[len(keyword):].strip()
        try:
            event.stop_event()
        except Exception:  # noqa: BLE001
            pass
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        if not name:
            yield event.plain_result("⚠️ 用法：自由武将招募 <名字>，例如：自由武将招募 柳德")
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        cost = int(self.cfg.get("gacha.custom_cost", 1000))
        smin = int(self.cfg.get("gacha.custom_stat_min", 30))
        smax = int(self.cfg.get("gacha.custom_stat_max", 100))
        res = gacha.recruit_custom(player, name, cost, smin, smax)
        if not res["ok"]:
            reason = res.get("reason")
            if reason == "gold":
                yield event.plain_result(f"⚠️ 金币不足！自定义招募需要 {cost} 金币。")
            elif reason == "capacity":
                yield event.plain_result(
                    f"⚠️ 自定义武将名额已满（{res['capacity']}）。\n发送 /宿舍升级 扩建武将宿舍。"
                )
            elif reason == "name_taken":
                yield event.plain_result(f"⚠️ 名字「{name}」已存在，请换一个。")
            elif reason == "name_too_long":
                yield event.plain_result("⚠️ 名字太长（最多 10 字）。")
            else:
                yield event.plain_result("⚠️ 名字无效，请重新输入。")
            return
        s = res["stats"]
        self._progress(player, "gacha")
        self._progress(player, "general_obtain")
        yield event.plain_result(
            f"🎉 自定义武将【{name}】加入！\n{sep()}\n"
            f"⚔️武力 {s['force']}  📖智力 {s['intellect']}  👑统帅 {s['lead']}\n"
            f"💪战力 {res['power']}\n"
            f"🏠 名额：{res['custom_count']}/{res['capacity']}\n"
            f"💰 剩余金币：{res['gold_left']}"
        )

    @filter.command("宿舍")
    async def dormitory(self, event: AstrMessageEvent):
        """查看武将宿舍"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        base = int(self.cfg.get("gacha.dorm_upgrade_base", 1500))
        st = building.status(player, base)
        yield event.plain_result(
            f"🏠 武将宿舍 Lv.{st['level']}\n{sep()}\n"
            f"自定义武将容量：{st['used']}/{st['capacity']}\n"
            f"下级升级费用：{st['next_cost']} 金币（容量 +1~3）\n"
            f"发送 /宿舍升级 进行扩建。"
        )

    @filter.command("宿舍升级")
    async def dormitory_upgrade(self, event: AstrMessageEvent):
        """升级武将宿舍，随机增加容量"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        base = int(self.cfg.get("gacha.dorm_upgrade_base", 1500))
        gmin = int(self.cfg.get("gacha.dorm_upgrade_gain_min", 1))
        gmax = int(self.cfg.get("gacha.dorm_upgrade_gain_max", 3))
        res = building.upgrade(player, base, gmin, gmax)
        if not res["ok"]:
            yield event.plain_result(
                f"⚠️ 金币不足！升级需要 {res['need']}，你只有 {res['gold']}。"
            )
            return
        yield event.plain_result(
            f"🏠 宿舍升级成功！\n"
            f"等级：Lv.{res['level']}\n"
            f"容量 +{res['gain']} → {res['capacity']}\n"
            f"💰 花费 {res['cost']}，剩余 {res['gold_left']}\n"
            f"下级费用：{res['next_cost']}"
        )

    @filter.command("武将")
    async def my_generals(self, event: AstrMessageEvent):
        """查看我的武将列表"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, name = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        entries = player_mod.all_generals_power(player)
        if not entries:
            yield event.plain_result(
                f"📦 {name} 的武将背包\n{sep()}\n空空如也...\n"
                f"发送 /兑换 或 /架空招募 获得武将吧！"
            )
            return
        lines = [
            f"📦 {name} 的武将（{len(entries)} 名）",
            f"💰 金币 {player['gold']} · 🧩 碎片 {player.get('fragments', 0)} · 💪总战力 {player_mod.total_power(player)}",
            sep(),
        ]
        for i, e in enumerate(entries[:15], 1):
            info = e["info"]
            lines.append(
                f"{i}. 【{e['name']}】{RARITY_LABEL.get(info.get('rarity', ''), '')} "
                f"Lv.{e['level']} ★{e['star']} 战力{e['power']}"
            )
        if len(entries) > 15:
            lines.append(f"… 还有 {len(entries) - 15} 名")
        yield event.plain_result("\n".join(lines))

    @filter.command("排行")
    async def ranking_cmd(self, event: AstrMessageEvent):
        """查看战力排行榜"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        rows = ranking.power_ranking(10)
        if not rows:
            yield event.plain_result("🏆 暂无玩家数据")
            return
        lines = ["🏆 三国战力排行榜", sep()]
        for i, r in enumerate(rows, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            lines.append(
                f"{medal} {r['name']} | 战力{r['power']} | {r['count']}将 | {r['win']}胜{r['lose']}负"
            )
        yield event.plain_result("\n".join(lines))

    @filter.command("对战")
    async def pvp(self, event: AstrMessageEvent):
        """与其他玩家进行 1v1 武将对战"""
        guard = self._guard(event, cooldown=3)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, name = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        my_entry = self._duel_entry(player)
        if not my_entry:
            yield event.plain_result("⚠️ 你还没有武将！发送 /兑换 或 /架空招募。")
            return
        ats = self._at_ids(event)
        if not ats:
            yield event.plain_result("⚠️ 请 @ 一名玩家对战，格式：/对战 @玩家")
            return
        target_id = ats[0]
        if target_id == qq:
            yield event.plain_result("⚠️ 不能和自己对战。")
            return
        target = player_mod.load(target_id)
        if not target:
            yield event.plain_result("⚠️ 对方还没有注册游戏。")
            return
        target_entry = self._duel_entry(target)
        if not target_entry:
            yield event.plain_result("⚠️ 对方还没有武将，无法对战。")
            return
        bonus_a = team.bonus(player)["bonus"]
        bonus_b = team.bonus(target)["bonus"]
        result = battle_sys.simulate([my_entry], [target_entry], bonus_a, bonus_b)

        lo = int(self.cfg.get("game.battle_reward_min", 50))
        hi = int(self.cfg.get("game.battle_reward_max", 150))
        reward = int(random.randint(lo, hi) * events_sys.multiplier("double_gold"))
        player.setdefault("pvp", {})
        target.setdefault("pvp", {})
        if result["winner"] == "a":
            player["win"] = int(player.get("win", 0)) + 1
            target["lose"] = int(target.get("lose", 0)) + 1
            player_mod.add_gold(player, reward)
            player["pvp"]["rating"] = int(player["pvp"].get("rating", 1000)) + 15
            target["pvp"]["rating"] = max(0, int(target["pvp"].get("rating", 1000)) - 10)
            outcome = f"🎉 {name} 胜利！获得 {reward} 金币。"
        elif result["winner"] == "b":
            target["win"] = int(target.get("win", 0)) + 1
            player["lose"] = int(player.get("lose", 0)) + 1
            player_mod.add_gold(target, reward)
            target["pvp"]["rating"] = int(target["pvp"].get("rating", 1000)) + 15
            player["pvp"]["rating"] = max(0, int(player["pvp"].get("rating", 1000)) - 10)
            outcome = f"😢 {name} 战败... 对方获得 {reward} 金币。"
        else:
            outcome = "🤝 平局！"
        player_mod.save(player)
        player_mod.save(target)
        self._progress(player, "battle")

        lines = [
            f"⚔️ 三国对决（1v1）⚔️", sep(),
            f"🔵 {name}：{my_entry['name']} "
            f"{RARITY_LABEL.get(my_entry['info'].get('rarity', ''), '')} "
            f"Lv.{my_entry['level']} ★{my_entry['star']}",
            f"    战力 {general_power(my_entry['info'], my_entry['level'], my_entry['star'])}",
            f"🆚",
            f"🔴 {target['name']}：{target_entry['name']} "
            f"{RARITY_LABEL.get(target_entry['info'].get('rarity', ''), '')} "
            f"Lv.{target_entry['level']} ★{target_entry['star']}",
            f"    战力 {general_power(target_entry['info'], target_entry['level'], target_entry['star'])}",
            sep(),
            *result["log"][:6],
            outcome,
        ]
        yield event.plain_result("\n".join(lines))

    # ------------------------------------------------------------------
    # 养成 / 阵容
    # ------------------------------------------------------------------
    @filter.command("培养")
    async def cultivate_cmd(self, event: AstrMessageEvent, name: str = "", times: int = 1):
        """花金币提升武将等级：/培养 <武将> [次数]"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/培养 <武将名> [次数]")
            return
        res = cultivate.cultivate(player, name, times)
        if not res["ok"]:
            if res["reason"] == "not_owned":
                yield event.plain_result(f"⚠️ 你没有武将「{name}」。")
            else:
                yield event.plain_result(
                    f"⚠️ 培养失败：可能金币不足或已达上限 Lv.{res.get('level')}。"
                )
            return
        yield event.plain_result(
            f"📈 【{name}】培养 {res['times']} 次\n"
            f"等级 → Lv.{res['level']}\n💰 花费 {res['spent']}，剩余 {res['gold_left']}"
        )

    @filter.command("升星")
    async def star_cmd(self, event: AstrMessageEvent, name: str = ""):
        """用碎片升星：/升星 <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/升星 <武将名>")
            return
        res = cultivate.star_up(player, name)
        if not res["ok"]:
            if res["reason"] == "not_owned":
                yield event.plain_result(f"⚠️ 你没有武将「{name}」。")
            elif res["reason"] == "max":
                yield event.plain_result(f"⚠️ 【{name}】已满星 ★{res['star']}。")
            else:
                yield event.plain_result(
                    f"⚠️ 碎片不足！升星需要 {res['need']}，你只有 {res['fragments']}。"
                )
            return
        yield event.plain_result(
            f"⭐ 【{name}】升星成功 → ★{res['star']}\n"
            f"🧩 消耗 {res['cost']}，剩余 {res['fragments_left']}"
        )

    @filter.command("技能")
    async def skill_cmd(self, event: AstrMessageEvent, name: str = ""):
        """升级武将技能：/技能 <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/技能 <武将名>")
            return
        res = cultivate.skill_up(player, name)
        if not res["ok"]:
            if res["reason"] == "not_owned":
                yield event.plain_result(f"⚠️ 你没有武将「{name}」。")
            elif res["reason"] == "max":
                yield event.plain_result(f"⚠️ 【{name}】技能已满级。")
            else:
                yield event.plain_result(f"⚠️ 金币不足！需要 {res['need']}。")
            return
        yield event.plain_result(
            f"📖 【{name}】技能升级 → Lv.{res['skill_lv']}\n"
            f"💰 花费 {res['cost']}，剩余 {res['gold_left']}"
        )

    @filter.command("图鉴")
    async def pokedex_cmd(self, event: AstrMessageEvent):
        """查看武将图鉴收集度"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        dex = collection.pokedex(player)
        lines = [f"📚 武将图鉴（{dex['owned_total']}/{dex['total']}）", sep()]
        for key, info in dex["categories"].items():
            bar = progress_bar(info["have"], info["total"])
            lines.append(f"{info['label']}：{info['have']}/{info['total']} {bar}")
        yield event.plain_result("\n".join(lines))

    @filter.command("合成")
    async def synthesize_cmd(self, event: AstrMessageEvent, rarity: str = ""):
        """消耗3名同稀有度武将合成更高稀有度：/合成 n|r|sr"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        rarity = (rarity or "").lower()
        if rarity not in ("n", "r", "sr"):
            yield event.plain_result("⚠️ 用法：/合成 n|r|sr（消耗3名该稀有度武将）")
            return
        res = collection.synthesize(player, rarity)
        if not res["ok"]:
            if res["reason"] == "not_enough":
                yield event.plain_result(
                    f"⚠️ {RARITY_LABEL.get(rarity)} 武将不足，需要 3 名（不在上阵中），当前 {res['have']}。"
                )
            else:
                yield event.plain_result("⚠️ 无法合成。")
            return
        info = tables().get(res["general"]) or {}
        dup = "（重复升星）" if res["duplicate"] else "（新武将！）"
        yield event.plain_result(
            f"⚗️ 合成成功！消耗 {'、'.join(res['consumed'])}\n"
            f"获得：【{res['general']}】{RARITY_LABEL.get(res['rarity'])} {dup}\n"
            f"⚔️武力 {info.get('force')}  📖智力 {info.get('intellect')}  👑统帅 {info.get('lead')}"
        )

    @filter.command("遣散")
    async def dismiss_cmd(self, event: AstrMessageEvent, name: str = ""):
        """遣散自定义武将释放名额：/遣散 <名字>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/遣散 <自定义武将名>")
            return
        res = collection.dismiss_custom(player, name)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 没有自定义武将「{name}」。")
            return
        yield event.plain_result(
            f"👋 已遣散【{name}】\n🏠 名额：{res['used']}/{res['capacity']}"
        )

    @filter.command("阵容")
    async def lineup_cmd(self, event: AstrMessageEvent):
        """查看当前出战阵容与羁绊"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        names = team.current_team(player)
        if not names:
            names = [e["name"] for e in player_mod.all_generals_power(player)[:3]]
        if not names:
            yield event.plain_result("⚠️ 你还没有武将，无法组建阵容。")
            return
        b = team.bonus(player)
        leader = team.leader_name(player)
        lines = [f"🛡️ 当前阵容（{len(names)}/3）", sep()]
        for i, n in enumerate(names, 1):
            info = player_mod.general_info(player, n) or {}
            mark = "👑主将 " if n == leader else ""
            lines.append(
                f"{i}. {mark}【{n}】{RARITY_LABEL.get(info.get('rarity', ''), '')} "
                f"{TROOP_LABEL.get(info.get('troop', ''), '')} "
                f"Lv.{info.get('level', 1)} ★{info.get('star', 1)} 战力{player_mod.general_power_of(player, n)}"
            )
        lines.append(sep())
        if b["active"]:
            for a in b["active"]:
                lines.append(f"🔗 羁绊·{a['name']}（{'+'.join(a['members'])}）{a['desc']}")
        else:
            lines.append("（暂无激活羁绊）")
        if not leader:
            lines.append("⚠️ 未设置主将，1v1 对战将默认使用阵容首位。")
        lines.append("发送 /上阵 <武将> 调整阵容；/主将 <武将> 设定 1v1 出战主将。")
        yield event.plain_result("\n".join(lines))

    @filter.command("上阵")
    async def deploy_cmd(self, event: AstrMessageEvent, name: str = ""):
        """将武将编入阵容：/上阵 <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/上阵 <武将名>")
            return
        res = team.add(player, name)
        if not res["ok"]:
            if res["reason"] == "not_owned":
                yield event.plain_result(f"⚠️ 你没有武将「{name}」。")
            elif res["reason"] == "already":
                yield event.plain_result(f"⚠️ 【{name}】已在阵容中。")
            else:
                yield event.plain_result(
                    f"⚠️ 阵容已满（3人）：{'、'.join(res['team'])}\n先用 /下阵 移除。"
                )
            return
        yield event.plain_result(f"✅ 已上阵【{name}】\n阵容：{'、'.join(res['team'])}")

    @filter.command("下阵")
    async def undeploy_cmd(self, event: AstrMessageEvent, name: str = ""):
        """将武将移出阵容：/下阵 <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/下阵 <武将名>")
            return
        res = team.remove(player, name)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 【{name}】不在阵容中。")
            return
        yield event.plain_result(f"✅ 已移除【{name}】\n阵容：{'、'.join(res['team']) or '（空）'}")

    @filter.command("主将")
    async def set_leader_cmd(self, event: AstrMessageEvent, name: str = ""):
        """设定 1v1 出战主将：/主将 <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            cur = team.leader_name(player) or "（未设置）"
            yield event.plain_result(f"当前主将：{cur}\n用法：/主将 <武将名>（用于 1v1 对战出战）")
            return
        res = team.set_leader(player, name)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 你没有武将「{name}」。")
            return
        yield event.plain_result(f"👑 已将【{name}】设为出战主将（1v1 对战时出战）。")

    # ------------------------------------------------------------------
    # 装备
    # ------------------------------------------------------------------
    @filter.command("装备")
    async def equipment_cmd(self, event: AstrMessageEvent):
        """查看装备背包"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        items = equip_sys.list_equipment(player)
        if not items:
            yield event.plain_result("🎒 装备背包空空如也，发送 /锻造 打造装备。")
            return
        lines = [f"🎒 装备背包（{len(items)}）", sep()]
        for it in items[:15]:
            worn = f" → {it['equipped_by']}" if it["equipped_by"] else ""
            lines.append(
                f"[{it['index']}] {RARITY_LABEL.get(it['rarity'])} {it['name']} "
                f"+{it['level']} {it['slot']} 战力{it['power']}{worn}"
            )
        lines.append("发送 /强化 <序号> 或 /穿戴 <序号> <武将>")
        yield event.plain_result("\n".join(lines))

    @filter.command("锻造")
    async def forge_cmd(self, event: AstrMessageEvent):
        """锻造装备"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = equip_sys.forge(player)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 金币不足！锻造需要 {res['need']} 金币。")
            return
        eq = res["equipment"]
        yield event.plain_result(
            f"🔨 锻造成功！{RARITY_LABEL.get(res['rarity'])} 【{eq['name']}】\n"
            f"部位：{equip_sys.SLOT_LABEL.get(eq['slot'])}\n"
            f"属性：武{equipment_stats_text(eq)}\n"
            f"💰 花费 {res['cost']}，剩余 {res['gold_left']}"
        )

    @filter.command("强化")
    async def enhance_cmd(self, event: AstrMessageEvent, index: int = -1):
        """强化装备：/强化 <序号>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if index < 0:
            yield event.plain_result("⚠️ 用法：/强化 <装备序号>（用 /装备 查看）")
            return
        res = equip_sys.enhance(player, index)
        if not res["ok"]:
            if res["reason"] == "not_found":
                yield event.plain_result("⚠️ 没有该序号的装备。")
            else:
                yield event.plain_result(f"⚠️ 金币不足！需要 {res['need']}。")
            return
        yield event.plain_result(
            f"⬆️ 【{res['name']}】强化成功 → +{res['level']}\n"
            f"💰 花费 {res['cost']}，剩余 {res['gold_left']}"
        )

    @filter.command("穿戴")
    async def equip_cmd(self, event: AstrMessageEvent, index: int = -1, general: str = ""):
        """给武将穿戴装备：/穿戴 <序号> <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if index < 0 or not general:
            yield event.plain_result("⚠️ 用法：/穿戴 <装备序号> <武将名>")
            return
        res = equip_sys.equip(player, index, general)
        if not res["ok"]:
            yield event.plain_result("⚠️ 装备或武将不存在。" if res["reason"] != "not_owned" else "⚠️ 你没有该武将。")
            return
        yield event.plain_result(
            f"✅ 已为【{res['general']}】装备【{res['name']}】（{equip_sys.SLOT_LABEL.get(res['slot'])}）"
        )

    @filter.command("卸下")
    async def unequip_cmd(self, event: AstrMessageEvent, general: str = "", slot: str = ""):
        """卸下装备：/卸下 <武将> <武器|防具|坐骑|宝物>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        label_to_slot = {v: k for k, v in equip_sys.SLOT_LABEL.items()}
        slot_key = label_to_slot.get(slot, slot)
        if not general or slot_key not in equip_sys.SLOTS:
            yield event.plain_result("⚠️ 用法：/卸下 <武将> <武器|防具|坐骑|宝物>")
            return
        res = equip_sys.unequip(player, general, slot_key)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 【{general}】的该部位没有装备。")
            return
        yield event.plain_result(f"✅ 已卸下【{general}】的{slot}。")

    # ------------------------------------------------------------------
    # 副本 PVE
    # ------------------------------------------------------------------
    def _recover_stamina(self, player: Dict[str, Any]) -> None:
        max_st = int(self.cfg.get("stamina.max", 120))
        interval = int(self.cfg.get("stamina.recover_interval", 300))
        amount = int(self.cfg.get("stamina.recover_amount", 1))
        player_mod.apply_stamina_recovery(player, max_st, interval, amount)

    @filter.command("副本")
    async def dungeon_cmd(self, event: AstrMessageEvent):
        """查看副本进度"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        self._recover_stamina(player)
        player_mod.save(player)
        prog = dungeon_sys.progress(player)
        lines = [
            f"🗺️ 副本进度：{prog['cleared']}/{prog['total']} ★{prog['stars']}/{prog['max_stars']}",
            f"⚡ 行动力：{player.get('stamina')}",
            sep(),
        ]
        for ch in dungeon_sys.chapters():
            marks = []
            for st in ch["stages"]:
                if dungeon_sys.is_cleared(player, st["id"]):
                    marks.append("✅")
                elif dungeon_sys.is_unlocked(player, st["id"]):
                    marks.append("🔓")
                else:
                    marks.append("🔒")
            lines.append(f"第{ch['id']}章 {ch['name']}  {''.join(marks)}")
        lines.append("发送 /挑战 <关卡ID>（如 /挑战 1-1）")
        yield event.plain_result("\n".join(lines))

    @filter.command("挑战")
    async def challenge_cmd(self, event: AstrMessageEvent, stage_id: str = ""):
        """挑战副本关卡：/挑战 1-1"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not stage_id or dungeon_sys.get_stage(stage_id) is None:
            yield event.plain_result("⚠️ 关卡ID无效，用 /副本 查看，例如 /挑战 1-1")
            return
        self._recover_stamina(player)
        team_entries = self._team_entries(player)
        res = dungeon_sys.challenge(player, stage_id, team_entries)
        if not res["ok"]:
            reason = res["reason"]
            if reason == "locked":
                yield event.plain_result("🔒 该关卡尚未解锁，请先通关上一关。")
            elif reason == "stamina":
                yield event.plain_result(f"⚡ 行动力不足！需要 {res['need']}，当前 {res['stamina']}。")
            else:
                yield event.plain_result("⚠️ 你还没有可出战的武将。")
            return
        st = res["stage"]
        rw = res["rewards"]
        if res["won"]:
            self._progress(player, "dungeon_clear")
            extra = f"，🧩 碎片 +{rw['fragment']}" if rw["fragment"] else ""
            yield event.plain_result(
                f"🎉 通关！【{st['chapter_name']}·{st['name']}】\n"
                f"💰 金币 +{rw['gold']}{extra}\n"
                f"⚡ 剩余行动力：{res['stamina_left']}"
            )
        else:
            yield event.plain_result(
                f"😢 挑战失败【{st['chapter_name']}·{st['name']}】\n"
                f"建议提升战力后再来。\n⚡ 剩余行动力：{res['stamina_left']}"
            )

    @filter.command("扫荡")
    async def sweep_cmd(self, event: AstrMessageEvent, stage_id: str = "", times: int = 1):
        """扫荡已通关卡：/扫荡 1-1 [次数]"""
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not stage_id:
            yield event.plain_result("⚠️ 用法：/扫荡 <关卡ID> [次数]")
            return
        self._recover_stamina(player)
        res = dungeon_sys.sweep(player, stage_id, times)
        if not res["ok"]:
            if res["reason"] == "not_cleared":
                yield event.plain_result("⚠️ 该关卡尚未通关，无法扫荡。")
            elif res["reason"] == "no_stage":
                yield event.plain_result("⚠️ 关卡ID无效。")
            else:
                yield event.plain_result(f"⚡ 行动力不足！当前 {res.get('stamina')}。")
            return
        yield event.plain_result(
            f"⚡ 扫荡【{res['stage']['name']}】×{res['times']}\n"
            f"💰 金币 +{res['gold']} · 🧩 碎片 +{res['fragment']}\n"
            f"⚡ 剩余行动力：{res['stamina_left']}"
        )

    # ------------------------------------------------------------------
    # 背包 / 道具
    # ------------------------------------------------------------------
    def _find_item(self, key: str):
        key = (key or "").strip()
        for item_id, item in items_mod.all_items().items():
            if item_id == key or item.get("name") == key:
                return item
        return None

    @filter.command("背包")
    async def bag_cmd(self, event: AstrMessageEvent):
        """查看背包"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        entries = inventory_sys.list_items(player)
        buffs = buff_sys.active(player)
        player_mod.save(player)
        lines = [
            f"🎒 背包 · 💰{player.get('gold')} · 🧩{player.get('fragments', 0)}",
            f"💎{player.get('wallet', {}).get('diamond', 0)} "
            f"🏅{player.get('wallet', {}).get('merit', 0)} "
            f"👻{player.get('wallet', {}).get('soul', 0)} "
            f"📣{player.get('wallet', {}).get('repute', 0)} "
            f"🎫{player.get('wallet', {}).get('event_ticket', 0)}",
            sep(),
        ]
        if not entries:
            lines.append("（背包空空如也，去 /商城 看看吧）")
        for e in entries:
            it = e["item"]
            lines.append(f"{RARITY_LABEL.get(it.get('rarity', 'n'), '')} {it['name']} x{e['count']}  ({it['id']})")
        if buffs:
            lines.append(sep())
            for b in buffs:
                left = int(b.get("expire", 0)) - int(time.time())
                lines.append(f"⏳ {buff_sys.BUFF_NAME.get(b['type'], b['type'])} x{b.get('value')} 剩 {fmt_duration(left)}")
        lines.append("发送 /使用 <道具名> 使用道具。")
        yield event.plain_result("\n".join(lines))

    @filter.command("使用")
    async def use_cmd(self, event: AstrMessageEvent, item_key: str = "", target: str = ""):
        """使用道具：/使用 <道具名> [武将]"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not item_key:
            yield event.plain_result("⚠️ 用法：/使用 <道具名> [武将名]")
            return
        item = self._find_item(item_key)
        if item is None:
            yield event.plain_result(f"⚠️ 找不到道具「{item_key}」。")
            return
        res = inventory_sys.use_item(player, item["id"], target or None)
        if not res["ok"]:
            reason = res["reason"]
            if reason == "none_owned":
                yield event.plain_result(f"⚠️ 你没有【{item['name']}】。")
            elif reason == "need_target":
                yield event.plain_result(f"⚠️ 使用【{item['name']}】需要指定武将：/使用 {item['name']} <武将>")
            else:
                yield event.plain_result("⚠️ 无法使用该道具。")
            return
        text = f"✅ 使用【{item['name']}】\n" + "\n".join(res["logs"])
        self._progress(player, "use_item")
        if res.get("pending"):
            opts = res["pending"]["options"]
            text += "\n请选择：\n" + "\n".join(f"{i}. {o['label']}" for i, o in enumerate(opts))
            text += "\n发送 /选择 <序号>"
        yield event.plain_result(text)

    @filter.command("选择")
    async def choose_cmd(self, event: AstrMessageEvent, index: int = -1):
        """自选礼盒选择：/选择 <序号>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = items_mod.resolve_choice(player, index)
        if not res["ok"]:
            yield event.plain_result("⚠️ 没有待选择的奖励，或序号无效。")
            return
        yield event.plain_result(f"🎁 已选择【{res['label']}】：{res['log']}")

    # ------------------------------------------------------------------
    # 商店 / 兑换所
    # ------------------------------------------------------------------
    @filter.command_group("商店")
    def shop_group(self):
        pass

    async def _show_shop(self, event: AstrMessageEvent, shop_key: str):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        view = shop_sys.view(player, shop_key)
        if not view["ok"]:
            yield event.plain_result("⚠️ 商店不存在。")
            return
        lines = [f"🏪 {view['name']}（发送 /商店 购买 <商品ID> <数量>）", sep()]
        for row in view["rows"]:
            item = items_mod.get_item(row["item"]) or {}
            remain = row["limit"] - row["bought"] if row["limit"] > 0 else "∞"
            lines.append(
                f"{item.get('name', row['item'])} | {row['price']}{row['currency']} "
                f"| 限购 {remain}/{row['limit']} | ID:{row['item']}"
            )
        yield event.plain_result("\n".join(lines))

    @shop_group.command("每日")
    async def shop_daily(self, event: AstrMessageEvent):
        async for r in self._show_shop(event, "daily"):
            yield r

    @shop_group.command("每周")
    async def shop_weekly(self, event: AstrMessageEvent):
        async for r in self._show_shop(event, "weekly"):
            yield r

    @shop_group.command("黑市")
    async def shop_black(self, event: AstrMessageEvent):
        async for r in self._show_shop(event, "black"):
            yield r

    @shop_group.command("活动")
    async def shop_event(self, event: AstrMessageEvent):
        async for r in self._show_shop(event, "event"):
            yield r

    @shop_group.command("购买")
    async def shop_buy(self, event: AstrMessageEvent, shop_key: str = "", item_id: str = "", qty: int = 1):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not shop_key or not item_id:
            yield event.plain_result("⚠️ 用法：/商店 购买 <商店daily|weekly|black|event> <商品ID> [数量]")
            return
        res = shop_sys.buy(player, shop_key, item_id, qty)
        if not res["ok"]:
            reasons = {
                "no_shop": "商店不存在。", "not_listed": "该商品不在本店。",
                "limit": "已达到限购上限。", "currency": "货币不足。",
            }
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "购买失败。"))
            return
        item = items_mod.get_item(res["item"]) or {}
        yield event.plain_result(
            f"✅ 购买【{item.get('name', res['item'])}】x{res['qty']}\n"
            f"💰 花费 {res['total']}{res['currency']}，剩余 {res['balance']}"
        )

    @shop_group.command("锁定")
    async def shop_lock(self, event: AstrMessageEvent, shop_key: str = "", item_id: str = ""):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = shop_sys.lock(player, shop_key, item_id)
        yield event.plain_result("✅ 已锁定。" if res["ok"] else f"⚠️ 锁定失败（{res.get('reason')}）。")

    @shop_group.command("解锁")
    async def shop_unlock(self, event: AstrMessageEvent, shop_key: str = "", item_id: str = ""):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = shop_sys.unlock(player, shop_key, item_id)
        yield event.plain_result("✅ 已解锁。" if res["ok"] else f"⚠️ 解锁失败（{res.get('reason')}）。")

    @shop_group.command("兑换所")
    async def exchange_list(self, event: AstrMessageEvent):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        lines = ["🏦 兑换所（单向兑换，发送 /商店 兑换 <规则ID> [次数]）", sep()]
        for r in exchange_sys.rules():
            lines.append(f"[{r['id']}] {r['cost']}{r['from']} → {r['gain']}{r['to']}  每日限 {r['daily_limit']}")
        yield event.plain_result("\n".join(lines))

    @shop_group.command("兑换")
    async def exchange_do(self, event: AstrMessageEvent, rule_id: str = "", times: int = 1):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = exchange_sys.do_exchange(player, rule_id, times)
        if not res["ok"]:
            if res["reason"] == "currency":
                yield event.plain_result(f"⚠️ 货币不足！需要 {res['need']}，你有 {res['have']}。")
            elif res["reason"] == "limit":
                yield event.plain_result("⚠️ 已达今日兑换上限。")
            else:
                yield event.plain_result("⚠️ 兑换规则无效。")
            return
        yield event.plain_result(
            f"🏦 兑换成功 x{res['times']}\n{res['cost']}{res['from']} → {res['gain']}{res['to']}\n剩余次数 {res['remain']}"
        )

    # ------------------------------------------------------------------
    # 拍卖行
    # ------------------------------------------------------------------
    @filter.command_group("拍卖")
    def auction_group(self):
        pass

    @auction_group.command("查看")
    async def auction_view(self, event: AstrMessageEvent):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        listings = auction_sys.list_active(20)
        if not listings:
            yield event.plain_result("🔨 拍卖行暂无在售物品。")
            return
        lines = ["🔨 拍卖行", sep()]
        for l in listings:
            lines.append(auction_sys.describe(l))
        lines.append("发送 /拍卖 出价 <编号> <金额> 或 /拍卖 一口价 <编号>")
        yield event.plain_result("\n".join(lines))

    @auction_group.command("我的")
    async def auction_mine(self, event: AstrMessageEvent):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        listings = auction_sys.my_listings(qq)
        if not listings:
            yield event.plain_result("🔨 你没有在售物品。")
            return
        lines = ["🔨 我的拍卖", sep()]
        for l in listings:
            lines.append(f"[{l['id']}] {l.get('status')} {auction_sys.describe(l)}")
        yield event.plain_result("\n".join(lines))

    @auction_group.command("上架装备")
    async def auction_list_equip(self, event: AstrMessageEvent, index: int = -1,
                                 mode: str = "一口价", price: int = 0, hours: int = 6):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if index < 0 or price <= 0:
            yield event.plain_result("⚠️ 用法：/拍卖 上架装备 <序号> <一口价|竞拍> <价格> [时长1|6|12|24]")
            return
        res = auction_sys.create_equipment(player, index, "buyout" if mode == "一口价" else "bid", price, 50, hours)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 上架失败（{res['reason']}）。")
            return
        yield event.plain_result(f"🔨 已上架 [{res['listing']['id']}]")

    @auction_group.command("上架碎片")
    async def auction_list_frag(self, event: AstrMessageEvent, count: int = 0,
                                mode: str = "一口价", price: int = 0, hours: int = 6):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if count <= 0 or price <= 0:
            yield event.plain_result("⚠️ 用法：/拍卖 上架碎片 <数量> <一口价|竞拍> <价格> [时长]")
            return
        res = auction_sys.create_fragment(player, count, "buyout" if mode == "一口价" else "bid", price, 50, hours)
        if not res["ok"]:
            yield event.plain_result(f"⚠️ 上架失败（{res['reason']}）。")
            return
        yield event.plain_result(f"🔨 已上架 [{res['listing']['id']}]")

    @auction_group.command("出价")
    async def auction_bid(self, event: AstrMessageEvent, listing_id: str = "", amount: int = 0):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = auction_sys.bid(player, listing_id, amount)
        if not res["ok"]:
            reasons = {"too_low": f"出价过低，至少 {res.get('min')}", "self": "不能竞拍自己的物品",
                       "gold": "金币不足（含保证金）", "not_biddable": "该物品不可竞拍"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "出价失败。"))
            return
        yield event.plain_result(f"✅ 出价 {res['amount']}（保证金 {res['deposit']}）")

    @auction_group.command("一口价")
    async def auction_buyout(self, event: AstrMessageEvent, listing_id: str = ""):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = auction_sys.buyout(player, listing_id)
        if not res["ok"]:
            reasons = {"self": "不能购买自己的物品", "gold": "金币不足", "expired": "已过期",
                       "not_found": "物品不存在", "bid_only": "竞拍商品不支持一口价，请使用 /拍卖 出价"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "购买失败。"))
            return
        yield event.plain_result(f"✅ 一口价成交 {res['price']}（税 {res['tax']}），物品已入包。")

    @auction_group.command("下架")
    async def auction_cancel(self, event: AstrMessageEvent, listing_id: str = ""):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = auction_sys.cancel(player, listing_id)
        if not res["ok"]:
            reasons = {"not_owner": "这不是你的物品", "has_bid": "已有竞拍，无法下架", "not_found": "物品不存在"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "下架失败。"))
            return
        yield event.plain_result("✅ 已下架，物品已退回。")

    # ------------------------------------------------------------------
    # 势力 / 军团 / 好友
    # ------------------------------------------------------------------
    @filter.command("势力")
    async def faction_cmd(self, event: AstrMessageEvent):
        """查看势力信息"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        info = faction_sys.info(player)
        lines = ["🏳️ 势力", sep()]
        mine = info.get("faction")
        lines.append(f"你的势力：{faction_sys.FACTIONS.get(mine, {}).get('name', '未加入')}"
                     f"（贡献 {info['contrib']}）")
        for row in info["list"]:
            lines.append(
                f"【{row['name']}】成员{row['members']} 势力战{row['war_points']} 总战力{row['power']}"
            )
        lines.append("发送 /加入 <魏|蜀|吴|群> 加入势力，/捐献 <金币> 提升贡献。")
        yield event.plain_result("\n".join(lines))

    @filter.command("加入")
    async def join_faction(self, event: AstrMessageEvent, faction: str = ""):
        """加入势力：/加入 魏|蜀|吴|群"""
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        name_map = {"魏": "wei", "蜀": "shu", "吴": "wu", "群": "qun"}
        key = name_map.get(faction, faction.lower())
        res = faction_sys.join(player, key)
        if not res["ok"]:
            if res["reason"] == "already":
                yield event.plain_result(f"⚠️ 你已加入【{faction_sys.FACTIONS.get(player.get('faction'), {}).get('name')}】。")
            else:
                yield event.plain_result("⚠️ 势力无效，可选：魏/蜀/吴/群。")
            return
        yield event.plain_result(f"🏳️ 你已加入【{res['name']}】势力！")

    @filter.command("捐献")
    async def donate_cmd(self, event: AstrMessageEvent, gold: int = 0):
        """向势力捐献金币：/捐献 <金币>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = faction_sys.donate(player, gold)
        if not res["ok"]:
            reasons = {"no_faction": "你还没有加入势力。", "gold": "金币不足。"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "捐献失败。"))
            return
        yield event.plain_result(
            f"🤝 捐献成功！势力贡献 +{res['contrib']}，功勋 +{res['merit']}\n累计贡献 {res['total']}"
        )
        self._progress(player, "donate")

    @filter.command("势力战")
    async def faction_war(self, event: AstrMessageEvent):
        """查看势力战排名"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq) or {"qq": qq}
        info = faction_sys.info(player)
        lines = ["⚔️ 势力战排名", sep()]
        for i, row in enumerate(info["list"], 1):
            lines.append(f"{i}. 【{row['name']}】势力战积分 {row['war_points']} 成员 {row['members']}")
        yield event.plain_result("\n".join(lines))

    @filter.command("军团")
    async def guild_cmd(self, event: AstrMessageEvent):
        """查看我的军团"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = guild_sys.info(player)
        guild = res["guild"]
        if not guild:
            yield event.plain_result(
                f"🎏 你还没有军团。\n发送 /创建军团 <名字>（{guild_sys.CREATE_COST}金币）或 /军团排行 查看军团。"
            )
            return
        yield event.plain_result(
            f"🎏 军团【{guild['name']}】Lv.{guild['level']}\n"
            f"团长：{guild['leader']} · 成员 {len(guild['members'])}/50 · 资金 {guild['fund']}\n"
            f"发送 /军团捐献 <金币> 提升军团等级。"
        )

    @filter.command("创建军团")
    async def guild_create(self, event: AstrMessageEvent, name: str = ""):
        """创建军团：/创建军团 <名字>"""
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = guild_sys.create(player, name)
        if not res["ok"]:
            reasons = {"gold": "金币不足。", "name_taken": "军团名已存在。",
                       "in_guild": "你已加入军团。", "bad_name": "名字无效（1-12字）。"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "创建失败。"))
            return
        yield event.plain_result(f"🎏 军团【{res['guild']['name']}】创建成功！ID {res['guild']['id']}")

    @filter.command("加入军团")
    async def guild_join(self, event: AstrMessageEvent, gid: str = ""):
        """加入军团：/加入军团 <军团ID>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = guild_sys.join(player, gid)
        if not res["ok"]:
            reasons = {"not_found": "军团不存在。", "in_guild": "你已加入军团。", "full": "军团已满。"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "加入失败。"))
            return
        yield event.plain_result(f"🎏 已加入军团【{res['guild']['name']}】")

    @filter.command("退出军团")
    async def guild_leave(self, event: AstrMessageEvent):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = guild_sys.leave(player)
        yield event.plain_result("✅ 已退出军团。" if res["ok"] else "⚠️ 你还没有军团。")

    @filter.command("军团捐献")
    async def guild_donate(self, event: AstrMessageEvent, gold: int = 0):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = guild_sys.donate(player, gold)
        if not res["ok"]:
            reasons = {"no_guild": "你还没有军团。", "gold": "金币不足。"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "捐献失败。"))
            return
        yield event.plain_result(f"🎏 军团捐献 {res['fund']} 金币，军团 Lv.{res['guild_level']}")

    @filter.command("军团排行")
    async def guild_rank(self, event: AstrMessageEvent):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        rows = guild_sys.top(10)
        if not rows:
            yield event.plain_result("🎏 暂无军团。")
            return
        lines = ["🎏 军团排行", sep()]
        for i, g in enumerate(rows, 1):
            lines.append(f"{i}. 【{g['name']}】Lv.{g['level']} 成员{len(g['members'])} 资金{g['fund']}")
        yield event.plain_result("\n".join(lines))

    @filter.command("好友")
    async def friends_cmd(self, event: AstrMessageEvent):
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        friends = player.get("friends", [])
        lines = [f"👥 好友（{len(friends)}）", sep()]
        for f in friends[:20]:
            data = player_mod.load(f)
            lines.append(f"· {data.get('name', f) if data else f}")
        lines.append("发送 /加好友 @玩家、/赠体力 @玩家、/切磋 @玩家")
        yield event.plain_result("\n".join(lines))

    @filter.command("加好友")
    async def add_friend_cmd(self, event: AstrMessageEvent):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        ats = self._at_ids(event)
        if not ats:
            yield event.plain_result("⚠️ 用法：/加好友 @玩家")
            return
        res = social_sys.add_friend(player, ats[0])
        if not res["ok"]:
            yield event.plain_result("⚠️ 已是好友或不能加自己。")
            return
        yield event.plain_result(f"👥 好友已添加，当前 {res['count']} 位。")

    @filter.command("赠体力")
    async def gift_stamina_cmd(self, event: AstrMessageEvent):
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        ats = self._at_ids(event)
        if not ats:
            yield event.plain_result("⚠️ 用法：/赠体力 @玩家")
            return
        res = social_sys.gift_stamina(player, ats[0])
        if not res["ok"]:
            yield event.plain_result("⚠️ 今天已赠送或对方不存在。")
            return
        yield event.plain_result(f"🎁 已赠送 {res['amount']} 行动力。")

    @filter.command("切磋")
    async def spar_cmd(self, event: AstrMessageEvent):
        guard = self._guard(event, cooldown=3)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, name = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        ats = self._at_ids(event)
        if not ats:
            yield event.plain_result("⚠️ 用法：/切磋 @玩家（友谊赛，不影响排名）")
            return
        target = player_mod.load(ats[0])
        if not target:
            yield event.plain_result("⚠️ 对方未注册。")
            return
        my_entry = self._duel_entry(player)
        target_entry = self._duel_entry(target)
        if not my_entry or not target_entry:
            yield event.plain_result("⚠️ 双方都需要有武将。")
            return
        res = battle_sys.simulate([my_entry], [target_entry],
                                  team.bonus(player)["bonus"], team.bonus(target)["bonus"])
        outcome = {"a": f"🎉 {name} 获胜！", "b": f"😢 {name} 落败。", "draw": "🤝 平局！"}[res["winner"]]
        yield event.plain_result(
            f"🤺 切磋（1v1 友谊赛）\n"
            f"🔵 {my_entry['name']} VS 🔴 {target_entry['name']}\n"
            f"{outcome}\n（不影响排行榜）"
        )

    # ------------------------------------------------------------------
    # 文转图卡牌
    # ------------------------------------------------------------------
    @filter.command("卡牌")
    async def card_cmd(self, event: AstrMessageEvent, name: str = ""):
        """生成武将卡牌图片：/卡牌 <武将>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not name:
            yield event.plain_result("⚠️ 用法：/卡牌 <武将名>")
            return
        info = player_mod.general_info(player, name)
        if not info:
            yield event.plain_result(f"⚠️ 找不到武将「{name}」。")
            return
        power = player_mod.general_power_of(player, name)
        fallback = (
            f"🎴 {name} {RARITY_LABEL.get(info.get('rarity', ''), '')}\n"
            f"武力{info.get('force')} 智力{info.get('intellect')} 统帅{info.get('lead')}\n"
            f"战力 {power}"
        )
        if not self.cfg.get("text_image.enable", True):
            yield event.plain_result(fallback)
            return
        try:
            tmpl = render_sys.load_template("general_card.html")
            data = render_sys.general_card_data(
                player, name, info, power,
                info.get("level", 1), info.get("star", 1),
            )
            url = await self.html_render(tmpl, data)
            yield event.image_result(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[三国] 卡牌渲染失败，回退文本: {exc}")
            yield event.plain_result(fallback)

    # ------------------------------------------------------------------
    # 任务 / 成就 / 邮件
    # ------------------------------------------------------------------
    @filter.command("任务")
    async def quest_cmd(self, event: AstrMessageEvent):
        """查看任务"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        data = quest_sys.quest_list(player)
        lines = ["📋 任务", sep()]
        for period, label in (("daily", "每日"), ("weekly", "每周"), ("growth", "成长")):
            lines.append(f"【{label}】")
            for q in data[period]:
                mark = "✅" if q["claimed"] else ("🎁" if q["progress"] >= q["target"] else "")
                lines.append(
                    f" {q['name']} {q['progress']}/{q['target']} {mark} ({q['id']})"
                )
        lines.append("达标后发送 /领取 <任务ID>")
        yield event.plain_result("\n".join(lines))

    @filter.command("成就")
    async def achievement_cmd(self, event: AstrMessageEvent):
        """查看成就"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        rows = quest_sys.achievement_list(player)
        lines = ["🏅 成就", sep()]
        for a in rows:
            mark = "✅" if a["claimed"] else ("🎁" if a["progress"] >= a["target"] else "")
            lines.append(f" {a['name']} {a['progress']}/{a['target']} {mark} ({a['id']})")
        lines.append("达标后发送 /领取 <成就ID>")
        yield event.plain_result("\n".join(lines))

    @filter.command("领取")
    async def claim_cmd(self, event: AstrMessageEvent, target_id: str = ""):
        """领取任务/成就奖励：/领取 <ID>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if not target_id:
            yield event.plain_result("⚠️ 用法：/领取 <任务或成就ID>（用 /任务、/成就 查看）")
            return
        res = quest_sys.claim_quest(player, target_id)
        kind = "任务"
        if not res["ok"] and res["reason"] == "not_found":
            res = quest_sys.claim_achievement(player, target_id)
            kind = "成就"
        if not res["ok"]:
            reasons = {"claimed": "已经领取过了。", "incomplete": "尚未达标。", "not_found": "ID 不存在。"}
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "领取失败。"))
            return
        yield event.plain_result(f"🎁 {kind}【{res['name']}】奖励领取成功：{'、'.join(res['logs']) or '已发放'}")

    @filter.command("邮件")
    async def mail_cmd(self, event: AstrMessageEvent):
        """查看邮件"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        if not player_mod.load(qq):
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        mails = mail_sys.inbox(qq)
        if not mails:
            yield event.plain_result("📮 暂无未领取邮件。")
            return
        lines = [f"📮 邮件（{len(mails)}）", sep()]
        for i, m in enumerate(mails):
            reward = "、".join(f"{k}x{v}" for k, v in m.get("reward", {}).items())
            lines.append(f"{i}. {m['title']}" + (f" [{reward}]" if reward else ""))
        lines.append("发送 /领邮件 <序号> 或 /领邮件 全部")
        yield event.plain_result("\n".join(lines))

    @filter.command("领邮件")
    async def claim_mail(self, event: AstrMessageEvent, index: str = ""):
        """领取邮件：/领邮件 <序号|全部>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        if not player_mod.load(qq):
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        if index in ("全部", "all", ""):
            res = mail_sys.claim_all(qq)
            if not res["ok"] or res["count"] == 0:
                yield event.plain_result("📮 没有可领取的邮件。")
                return
            yield event.plain_result(f"📮 已领取 {res['count']} 封邮件：{'、'.join(res['logs']) or '已发放'}")
            return
        try:
            i = int(index)
        except ValueError:
            yield event.plain_result("⚠️ 用法：/领邮件 <序号> 或 /领邮件 全部")
            return
        mails = mail_sys.inbox(qq)
        if not (0 <= i < len(mails)):
            yield event.plain_result("⚠️ 序号无效。")
            return
        res = mail_sys.claim(qq, mails[i]["id"])
        if not res["ok"]:
            yield event.plain_result("⚠️ 领取失败。")
            return
        yield event.plain_result(f"📮 已领取【{res['title']}】：{'、'.join(res['logs']) or '已发放'}")

    # ------------------------------------------------------------------
    # 世界BOSS / 战令 / 活动
    # ------------------------------------------------------------------
    @filter.command("世界boss", alias={"世界BOSS"})
    async def worldboss_cmd(self, event: AstrMessageEvent):
        """查看世界BOSS状态与排行"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        if not self.cfg.get("worldboss.enable", True):
            yield event.plain_result("⚠️ 世界BOSS功能已关闭。")
            return
        data = worldboss_sys.current()
        if not data.get("active"):
            yield event.plain_result("🐲 世界BOSS未开启，请等待管理员开启。")
            return
        boss = data["boss"]
        rows = worldboss_sys.ranking(10)
        lines = [
            f"🐲 世界BOSS【{boss['name']}】",
            f"HP {data['hp']}/{data['max_hp']}",
            progress_bar(int(data["hp"]), int(data["max_hp"])),
            sep(),
        ]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r['name']} 伤害 {r['damage']}（{r['count']}次）")
        if not rows:
            lines.append("（暂无讨伐记录，发送 /讨伐 参与）")
        yield event.plain_result("\n".join(lines))

    @filter.command("讨伐")
    async def raid_boss_cmd(self, event: AstrMessageEvent):
        """讨伐世界BOSS"""
        guard = self._guard(event, cooldown=2)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        if not self.cfg.get("worldboss.enable", True):
            yield event.plain_result("⚠️ 世界BOSS功能已关闭。")
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        team_entries = self._team_entries(player)
        if not team_entries:
            yield event.plain_result("⚠️ 你还没有武将，无法讨伐。")
            return
        power = sum(general_power(e["info"], e["level"], e["star"]) for e in team_entries)
        limit = int(self.cfg.get("worldboss.attack_limit", 3))
        res = worldboss_sys.attack(player, power, limit)
        if not res["ok"]:
            if res["reason"] == "inactive":
                yield event.plain_result("🐲 世界BOSS未开启。")
            elif res["reason"] == "limit":
                yield event.plain_result(f"⚠️ 今日讨伐次数已用完（{res['max']}次）。")
            else:
                yield event.plain_result("⚠️ 讨伐失败。")
            return
        text = (
            f"⚔️ 讨伐造成伤害 {res['damage']}！\n"
            f"🐲 BOSS HP {res['hp']}/{res['max_hp']}\n"
            f"剩余次数 {res['attacks_left']}"
        )
        if res.get("defeated"):
            text += "\n🎉 BOSS 已被讨伐！奖励将通过邮件发放。"
        self._progress(player, "battle")
        yield event.plain_result(text)

    @filter.command("战令")
    async def battlepass_cmd(self, event: AstrMessageEvent):
        """查看战令进度"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        p = battlepass_sys.progress(player)
        player_mod.save(player)
        premium_txt = "已解锁" if p["premium"] else f"未解锁（/战令购买 {p['premium_cost']}钻石）"
        lines = [
            f"🎖️ 战令 · {p['season_name']}（第{p['season']}赛季）",
            f"等级 {p['level']}/{p['max_level']}  经验 {p['exp_in_level']}"
            + (f"/{p['exp_in_level'] + p['need_next']}" if p["need_next"] else ""),
            f"进阶轨：{premium_txt}",
            sep(),
        ]
        for row in p["rows"]:
            if not row["reached"] and row["level"] > p["level"] + 2:
                lines.append(f"… 共 {p['max_level']} 级")
                break
            flag = "✓" if row["reached"] else "·"
            free = bool(row["free"])
            prem = bool(row["premium"])
            lines.append(f"{flag} Lv.{row['level']} 免费{'已领' if row['claimed_free'] else ('可领' if row['reached'] else '')} / 进阶{'已领' if row['claimed_premium'] else ('可领' if row['reached'] and p['premium'] else '')}")
        lines.append("发送 /战令领取 <等级> <免费|进阶>")
        yield event.plain_result("\n".join(lines))

    @filter.command("战令领取")
    async def battlepass_claim_cmd(self, event: AstrMessageEvent, level: int = 0, track: str = "免费"):
        """领取战令奖励：/战令领取 <等级> <免费|进阶>"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = battlepass_sys.claim(player, level, track)
        if not res["ok"]:
            reasons = {
                "not_reached": f"等级不足（当前 {res.get('level')}）。",
                "claimed": "该奖励已领取。", "no_premium": "尚未解锁进阶轨。",
                "no_level": "等级不存在。", "bad_track": "轨别只能是 免费 或 进阶。",
            }
            yield event.plain_result("⚠️ " + reasons.get(res["reason"], "领取失败。"))
            return
        yield event.plain_result(
            f"🎖️ 战令 Lv.{res['level']} {res['track']}奖励：{'、'.join(res['logs']) or '已发放'}"
        )

    @filter.command("战令购买")
    async def battlepass_buy_cmd(self, event: AstrMessageEvent):
        """解锁战令进阶轨"""
        guard = self._guard(event, cooldown=1)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        qq, _ = self._sender(event)
        player = player_mod.load(qq)
        if not player:
            yield event.plain_result("⚠️ 你还没有注册！发送 /注册。")
            return
        res = battlepass_sys.unlock_premium(player)
        if not res["ok"]:
            if res["reason"] == "already":
                yield event.plain_result("⚠️ 进阶轨已解锁。")
            else:
                yield event.plain_result(f"⚠️ 钻石不足！需要 {res['need']}，你有 {res['have']}。")
            return
        yield event.plain_result(f"🎖️ 进阶轨解锁成功！消耗 {res['cost']} 钻石。")

    @filter.command("活动")
    async def events_cmd(self, event: AstrMessageEvent):
        """查看进行中的活动"""
        guard = self._guard(event)
        if guard is not None:
            if guard:
                yield event.plain_result(guard)
            return
        active = events_sys.active_events()
        lines = ["🎉 限时活动", sep()]
        if active:
            for e in active:
                left = max(0, int(e.get("end_ts", 0)) - int(time.time()))
                lines.append(f"🔥 {e['name']}：{e['desc']}（剩余 {fmt_duration(left)}）")
        else:
            lines.append("（当前没有进行中的活动）")
        lines.append(sep())
        lines.append("可用活动：")
        for d in events_sys.defs():
            lines.append(f"· {d['name']}（{events_sys.BUFF_LABEL.get(d['buff_type'], d['buff_type'])}）")
        yield event.plain_result("\n".join(lines))

    # ------------------------------------------------------------------
    # GM 指令（仅管理员）
    # ------------------------------------------------------------------
    @filter.command_group("gm")
    def gm(self):
        pass

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("查询")
    async def gm_query(self, event: AstrMessageEvent):
        ats = self._at_ids(event)
        target_id = ats[0] if ats else str(event.get_sender_id())
        data = player_mod.load(target_id)
        if not data:
            yield event.plain_result(f"⚠️ 玩家 {target_id} 无存档。")
            return
        yield event.plain_result(
            f"👤 {data.get('name')} ({target_id})\n"
            f"💰 金币 {data.get('gold')} · 🧩 碎片 {data.get('fragments')}\n"
            f"💪 总战力 {player_mod.total_power(data)} · 武将 {len(player_mod.owned_names(data))}\n"
            f"🏆 {data.get('win')}胜{data.get('lose')}负 · 竞技分 {data.get('pvp', {}).get('rating')}"
        )

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("发放")
    async def gm_grant(self, event: AstrMessageEvent, amount: int = 0):
        ats = self._at_ids(event)
        if not ats:
            yield event.plain_result("⚠️ 用法：/gm 发放 @玩家 <金币数>")
            return
        target_id = ats[0]
        data = player_mod.load(target_id)
        if not data:
            yield event.plain_result("⚠️ 目标无存档。")
            return
        before = audit.snapshot(target_id, data)
        player_mod.add_gold(data, amount)
        player_mod.save(data)
        op = audit.log(
            operator=str(event.get_sender_id()), action="grant_gold",
            target=target_id, params={"amount": amount},
            result="ok", reversible=True, before_snapshot=before,
        )
        yield event.plain_result(f"✅ 已向 {data.get('name')} 发放 {amount} 金币。操作号 {op}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("维护")
    async def gm_maintenance(self, event: AstrMessageEvent, state: str = ""):
        if not self._is_super_admin(event):
            yield event.plain_result("⚠️ 该操作仅超级管理员可执行。")
            return
        if state in ("开", "on", "1", "true"):
            maintenance.set_on(True)
            yield event.plain_result("🛠️ 已开启维护模式。")
        elif state in ("关", "off", "0", "false"):
            maintenance.set_on(False)
            yield event.plain_result("✅ 已关闭维护模式。")
        else:
            yield event.plain_result(
                f"当前维护模式：{'开启' if maintenance.is_on() else '关闭'}\n用法：/gm 维护 开|关"
            )

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("审计")
    async def gm_audit(self, event: AstrMessageEvent):
        records = audit.recent(10)
        if not records:
            yield event.plain_result("📋 暂无审计记录。")
            return
        lines = ["📋 最近 GM 操作", sep()]
        for r in records:
            lines.append(
                f"[{r['op_id']}] {r['action']} → {r['target'] or '-'} by {r['operator']}"
                + ("（可回滚）" if r.get("reversible") else "")
                + ("（已回滚）" if r.get("rolled_back") else "")
            )
        yield event.plain_result("\n".join(lines))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("回滚")
    async def gm_rollback(self, event: AstrMessageEvent, op_id: str = ""):
        if not self._is_super_admin(event):
            yield event.plain_result("⚠️ 该操作仅超级管理员可执行。")
            return
        record = audit.find(op_id) if op_id else None
        if not record:
            yield event.plain_result("⚠️ 未找到该操作号。")
            return
        if not record.get("reversible") or not record.get("before"):
            yield event.plain_result("⚠️ 该操作不可回滚。")
            return
        snap = audit.load_snapshot(record["before"])
        if not snap:
            yield event.plain_result("⚠️ 快照缺失，无法回滚。")
            return
        player_mod.save(snap["data"])
        audit.mark_rolled_back(op_id)
        yield event.plain_result(f"✅ 已回滚操作 {op_id}。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("世界boss")
    async def gm_worldboss(self, event: AstrMessageEvent, action: str = "", boss_id: str = "", hours: int = 0):
        if not self._is_super_admin(event):
            yield event.plain_result("⚠️ 该操作仅超级管理员可执行。")
            return
        if action in ("开启", "开", "spawn"):
            if not self.cfg.get("worldboss.enable", True):
                yield event.plain_result("⚠️ 世界BOSS功能已关闭（可在插件配置中开启）。")
                return
            duration = hours * 3600 if hours > 0 else int(self.cfg.get("worldboss.duration", 21600))
            res = worldboss_sys.spawn(boss_id or None)
            if not res["ok"]:
                yield event.plain_result("⚠️ 开启失败（无BOSS配置）。")
                return
            # 覆盖时长
            data = worldboss_sys._load()
            data["end_ts"] = int(time.time()) + duration
            worldboss_sys._save(data)
            audit.log(str(event.get_sender_id()), "worldboss_spawn", boss_id or "random")
            yield event.plain_result(f"🐲 世界BOSS【{res['boss']['boss']['name']}】已开启。")
        elif action in ("结算", "settle"):
            res = worldboss_sys.settle()
            yield event.plain_result("✅ 已结算并发放奖励。" if res["ok"] else "⚠️ 当前无激活世界BOSS。")
        else:
            yield event.plain_result(f"当前：{worldboss_sys.status()}\n用法：/gm 世界boss 开启 [boss_id] [小时] | 结算")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("开活动")
    async def gm_open_event(self, event: AstrMessageEvent, event_id: str = "", hours: int = 0):
        if not self._is_super_admin(event):
            yield event.plain_result("⚠️ 该操作仅超级管理员可执行。")
            return
        duration = hours * 3600 if hours > 0 else None
        res = events_sys.open_event(event_id, duration)
        if not res["ok"]:
            yield event.plain_result("⚠️ 活动ID不存在。可用："
                                     + "、".join(d["id"] for d in events_sys.defs()))
            return
        audit.log(str(event.get_sender_id()), "event_open", event_id)
        yield event.plain_result(f"🎉 活动【{res['event']['name']}】已开启（{res['duration'] // 60}分钟）。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @gm.command("关活动")
    async def gm_close_event(self, event: AstrMessageEvent, event_id: str = ""):
        if not self._is_super_admin(event):
            yield event.plain_result("⚠️ 该操作仅超级管理员可执行。")
            return
        res = events_sys.close_event(event_id)
        if not res["ok"]:
            yield event.plain_result("⚠️ 该活动未开启。")
            return
        audit.log(str(event.get_sender_id()), "event_close", event_id)
        yield event.plain_result(f"🛑 活动 {event_id} 已关闭。")

    # ------------------------------------------------------------------
    # Web API（管理台，框架）
    # ------------------------------------------------------------------
    def _register_web_api(self):
        routes = [
            ("admin/stats", self._api_stats, ["GET"], "游戏统计"),
            ("admin/players", self._api_players, ["GET"], "玩家列表"),
            ("admin/player/<qq>", self._api_player, ["GET"], "玩家详情"),
            ("admin/generals", self._api_generals, ["GET", "POST"], "武将库/保存"),
            ("admin/generals/delete", self._api_generals_delete, ["POST"], "删除武将"),
            ("admin/generals/options", self._api_generals_options, ["GET"], "武将选项"),
            ("admin/config", self._api_config, ["GET"], "读取配置"),
            ("admin/broadcast", self._api_broadcast, ["POST"], "广播推送"),
            ("admin/items", self._api_items, ["GET", "POST"], "道具列表/保存"),
            ("admin/items/delete", self._api_item_delete, ["POST"], "删除道具"),
            ("admin/effects/schema", self._api_effects_schema, ["GET"], "效果schema"),
        ]
        for suffix, handler, methods, desc in routes:
            try:
                plugin_name = getattr(self, "name", "") or storage.PLUGIN_NAME
                self.context.register_web_api(
                    f"/{plugin_name}/{suffix}", handler, methods, desc
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[三国] 注册 Web API {suffix} 失败: {exc}")

    async def _api_stats(self):
        from astrbot.api.web import error_response, json_response

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        players = storage.list_players()
        return json_response({
            "players": len(players),
            "generals": len(tables().all_names()),
            "items": len(items_mod.all_items()),
            "version": "1.1.0",
            "maintenance": maintenance.is_on(),
        })

    async def _api_players(self):
        from astrbot.api.web import error_response, json_response

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        rows = []
        for qq, data in storage.iter_players():
            rows.append({
                "qq": qq,
                "name": data.get("name", qq),
                "gold": data.get("gold", 0),
                "fragments": data.get("fragments", 0),
                "generals": len(player_mod.owned_names(data)),
                "power": player_mod.total_power(data),
                "faction": data.get("faction", ""),
                "win": data.get("win", 0),
                "lose": data.get("lose", 0),
            })
        rows.sort(key=lambda r: r["power"], reverse=True)
        return json_response({"total": len(rows), "players": rows})

    async def _api_player(self, qq: str):
        from astrbot.api.web import error_response, json_response

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        data = player_mod.load(qq)
        if not data:
            return error_response("player not found", status_code=404)
        return json_response(data)

    async def _api_generals(self):
        from astrbot.api.web import error_response, json_response, request

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        if getattr(request, "method", "GET") == "POST":
            payload = await request.json(default={})
            res = generals_admin_mod.save_custom_general(payload)
            if not res["ok"]:
                return error_response(res.get("reason", "save failed"), status_code=400)
            audit.log("web:" + str(getattr(request, "username", "")), "save_general",
                      str(payload.get("name", "")))
            return json_response({"saved": True, "name": payload.get("name")})
        result = {}
        t = tables()
        for cat in ("historical", "obscure", "fictional", "custom"):
            table = getattr(t, cat, {})
            result[cat] = [g for lst in table.values() for g in lst]
        return json_response({"total": len(t.all_names()), "categories": result})

    async def _api_generals_delete(self):
        from astrbot.api.web import error_response, json_response, request

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        payload = await request.json(default={})
        name = str(payload.get("name", ""))
        res = generals_admin_mod.delete_custom_general(name)
        if not res["ok"]:
            return error_response("not found or not custom", status_code=404)
        audit.log("web:" + str(getattr(request, "username", "")), "delete_general", name)
        return json_response({"deleted": True})

    async def _api_generals_options(self):
        from astrbot.api.web import error_response, json_response

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        from .core.utils import ATTR_KEYS, ATTR_LABEL

        return json_response({
            "rarities": ["ssr", "sr", "r", "n"],
            "factions": ["wei", "shu", "wu", "qun", "custom"],
            "troops": ["cavalry", "infantry", "archer", "spear"],
            "attrs": [{"key": k, "label": ATTR_LABEL.get(k, k)} for k in ATTR_KEYS],
        })

    async def _api_config(self):
        from astrbot.api.web import error_response, json_response

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        return json_response(self.cfg.as_dict())

    async def _api_items(self):
        from astrbot.api.web import error_response, json_response, request

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        if getattr(request, "method", "GET") == "POST":
            payload = await request.json(default={})
            res = items_mod.save_custom_item(payload)
            if not res["ok"]:
                return error_response(res.get("reason", "save failed"), status_code=400)
            audit.log("web:" + str(getattr(request, "username", "")), "save_item",
                      str(payload.get("id", "")))
            return json_response({"saved": True, "item_id": payload.get("id")})
        return json_response({"items": list(items_mod.all_items().values())})

    async def _api_item_delete(self):
        from astrbot.api.web import error_response, json_response, request

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        payload = await request.json(default={})
        item_id = str(payload.get("id", ""))
        res = items_mod.delete_custom_item(item_id)
        if not res["ok"]:
            return error_response("not found", status_code=404)
        audit.log("web:" + str(getattr(request, "username", "")), "delete_item", item_id)
        return json_response({"deleted": True})

    async def _api_effects_schema(self):
        from astrbot.api.web import error_response, json_response

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        return json_response(items_mod.effect_schema())

    async def _api_broadcast(self):
        from astrbot.api.web import error_response, json_response, request

        if not self._admin_allowed():
            return error_response("forbidden", status_code=403)
        payload = await request.json(default={})
        text = str(payload.get("text", "")).strip()
        if not text:
            return error_response("text required", status_code=400)
        sent = 0
        try:
            from astrbot.api.event import MessageChain

            sessions = storage.load_global("session_index", {}) or {}
            for entry in sessions.values():
                if not self._supports_active_message(entry):
                    continue
                umo = entry.get("umo") if isinstance(entry, dict) else entry
                if not umo:
                    continue
                try:
                    await self.context.send_message(umo, MessageChain().message(text))
                    sent += 1
                except Exception:  # noqa: BLE001
                    continue
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[三国] 广播失败: {exc}")
        return json_response({"sent": sent})

    def _supports_active_message(self, entry: Any) -> bool:
        """按平台能力过滤：QQ 官方接口不支持主动消息，默认跳过。"""
        blocked = self.cfg.get(
            "system.blocked_push_platforms", ["qq_official", "qqofficial_webhook"]
        ) or []
        blocked_set = {str(x).lower() for x in blocked}
        if isinstance(entry, dict):
            platform = str(entry.get("platform", "")).lower()
            return platform not in blocked_set
        # 兼容旧结构（纯 umo 字符串）
        low = str(entry).lower()
        return not any(b and b in low for b in blocked_set)
