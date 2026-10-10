# 柳弗罗三国演义 · AstrBot 插件

> 版本 `1.2.0`　AstrBot `>=4.17.0`　支持 `aiocqhttp` / `qq_official`
> 一款接入 QQ 群的三国题材**卡牌收集 / 养成 / 对战**游戏插件，自带 WebUI 管理台（14 页）与 GM 工具。

**English:** LiuFeng Romance of the Three Kingdoms is an AstrBot plugin that turns a QQ group chat into a living Three Kingdoms world. It is a card-collection, character-development, and battle game: players register, sign in daily, recruit generals, and grow an army. It features 370 generals (historical, obscure, and fictional), each with six attributes—Force, Intellect, Vitality, Charisma, Eloquence, and Speed—that affect both power and combat. Combat uses a dual-defense, penetration-based damage model with crit, attack speed, CDR, tenacity, damage reduction and mana; every general has a passive and up to three active skills, and a three-tier troop system (basic/elite/special, 16 troops) with counter relations and carried effects. Players level up and star-up generals, learn/upgrade skills, forge and enhance equipment, challenge PVE dungeons, a world boss, or duel other players 1v1. Shops, currency exchange, an auction house, factions, guilds, quests, a season pass, and events keep communities engaged. The bot owner gets a WebUI admin console (dashboard, players, general/skill/troop libraries, guilds, equipment, auction, events, scheduled jobs, world boss, broadcast) and GM tools.

**中文简介：** 柳弗罗三国演义把一个 QQ 群聊变成一个鲜活的三国世界。玩家注册、每日签到、招募武将，逐步壮大军团。插件收录 370 名武将（历史、冷门、架空），每位拥有六维能力——武力、智力、体力、魅力、口才、速度——计入战力并影响战斗。战斗采用**双防 + 穿透**伤害模型，含暴击、攻速、冷却缩减、韧性、免伤与**法力**；每名武将拥有**被动 1 + 主动 1/2/3** 技能槽，并有**基础/精锐/特殊三级共 16 种兵种**（含克制与携带效果）。玩家升级升星、学习升级技能、锻造强化装备，挑战副本 PVE、世界BOSS，或与其他玩家 1v1 对决；商城、货币兑换、拍卖行、势力、军团、任务、战令与限时活动持续提供动力。机器人所有者配有 WebUI 管理台（仪表盘、玩家、武将库、技能工坊、兵种库、道具工坊、军团、装备、拍卖行、活动、定时任务、世界BOSS、广播）与 GM 工具。

## 功能总览

- **武将库**：历史 150 + 冷门 100 + 架空 120（共 370），**多维能力（武力/智力/体力/魅力/口才/速度）**，自动生成技能与羁绊；管理台可自定义增删武将
- **招募三线**：碎片兑换（通用碎片随机出历史/冷门武将）、架空招募（金币，有失败率）与架空十连、自定义武将（无前缀 `自由武将招募 名字`，随机基础兵种）
- **养成**：升级（培养）、升星、技能、图鉴、合成、遣散、阵容
- **技能系统**：被动 1 + 主动 1/2/3 王者式技能槽；**350 技能效果库** + 按名生成；**内置 30 技能**；技能书 + 技能书碎片（`/技能店` `/兑换技能书` `/学技能`）
- **兵种系统**：基础/精锐/特殊**三级 16 兵种**，克制关系 + 携带效果（属性加成 / 特殊机制 / 开局效果）；**100 兵种效果库**；历史按史实、架空随机
- **战斗**：PvP **1v1**（`/主将` 指定出战）/ PVE 3v3 回合制；**双防 + 固定/百分比穿透**伤害公式，暴击/暴伤/攻速/CDR/韧性/免伤/吸血/**法力**；兵种克制、羁绊加成、竞技评分
- **装备**：武器/防具/坐骑/宝物，锻造、强化、穿戴、卸下
- **副本 PVE**：黄巾之乱 → 虎牢关 → 官渡 → 赤壁 → 夷陵 → 五丈原（六章 24 关），行动力、碎片掉落、扫荡
- **经营**：系统商城（每日/每周/黑市/活动）、兑换所（单向）、拍卖行（一口价+竞拍+保证金+抽税）、道具效果引擎、背包、限时 buff
- **社交**：势力国战、军团、好友、切磋
- **运营**：任务、成就、邮件、战令、限时活动、世界BOSS、定时推送、维护模式
- **展示**：文转图武将卡牌（`/卡牌 <武将>`，无 Playwright 时自动回退纯文本）
- **管理台（14 页）**：仪表盘 / 玩家 / 武将库 / **技能工坊** / **兵种库** / **兵种效果库** / 道具工坊 / **军团管理** / **装备管理** / **拍卖行** / **活动管理** / **定时任务（中文名 + 自定义任务）** / **世界BOSS** / 广播；GM 指令（分级、审计、回滚）

## 多维能力（武将属性）

| 维度 | 战斗作用 |
|---|---|
| 武力 force | 物理攻击 |
| 体力 vitality | 生命上限 |
| 速度 speed | 出手顺序（先手） |
| 智力 intellect | 防御 + 暴击率 + 法力上限 |
| 魅力 charisma | 团队光环（提升己方攻防） |
| 口才 eloquence | 概率“说服”削弱敌方攻击 |

战力 = `武力×2 + 智力×1.5 + 体力×1.5 + 魅力×1 + 口才×1 + 速度×1.2`，再叠加星级系数、等级成长与装备加成。
历史武将按史实生成，架空与自定义武将随机生成。

## 技能与兵种（v1.2.0）

- **技能**：效果原子涵盖 伤害（兵刃/谋略/真实）、治疗/回复、增益/减益、持续伤害、控制、护盾、净化、驱散、无敌、斩杀、复活等，每个效果可设**概率随机抽取**；技能等级影响伤害公式；主动技能消耗**法力**、受冷却与沉默影响。
- **兵种**：基础（步兵/骑兵/弓兵/枪兵）、精锐（重步兵/铁骑/强弩兵/长枪兵）、特殊（虎豹骑/白毦兵/陷阵营/锦帆军/无当飞军/藤甲兵/象兵/白马义从）；携带效果在战斗开场与战斗中生效。

## 目录结构

```
liufeng_sanguo_game/
├── metadata.yaml  requirements.txt  _conf_schema.json  README.md
├── main.py                 # 插件入口：全部指令 handler + 无前缀监听 + 调度器 + Web API
├── core/                   # storage / config / utils / security / audit / maintenance / scheduler / event_bus
├── systems/                # 各玩法逻辑（纯 Python，可单元测试）
│   ├── skillgen.py  skills.py  skills_admin.py       # 技能生成 / 技能书 / 技能增删改
│   ├── troops.py  troops_admin.py                    # 兵种与兵种效果
│   ├── generals_admin.py  player_admin.py            # 自定义武将 / 玩家管理操作
│   └── guild_admin.py  equipment_admin.py  auction_admin.py   # 运营管理
├── tables/                 # 静态数据表（武将/技能/技能效果/内置技能/兵种/兵种效果/羁绊/装备/副本/道具/商店/兑换/任务/成就/活动/BOSS）
├── templates/              # 文转图 HTML 模板（武将六维卡、战报）
├── pages/admin/            # WebUI 管理台页面（index.html / app.js / style.css）
├── tests/                  # pytest 单元测试
└── tools/                  # 数据表生成脚本（build_tables / build_skill_effects / build_troop_effects / build_battlepass）
```

## 数据存储

- 每个 QQ 号独立文件夹：`data/plugin_data/liufeng_sanguo_game/players/<QQ>/player.json`
- 跨群全局数据：`.../global/*.json`（排行榜、势力、军团、拍卖、世界BOSS、活动状态、战令、会话索引、审计、维护状态、封禁名单等）
- 管理台自定义数据（不随插件更新丢失）：`generals_custom.json`、`items_custom.json`、`skills_custom.json`、`troops_custom.json`、`troop_effects_custom.json`、`equipments_custom.json`、`events_custom.json`、`bosses_custom.json`
- 原子写入 + 进程内加锁；AstrBot 官方数据目录 `get_astrbot_data_path()/plugin_data/<name>`

## 指令速查（无需前缀）

| 类别 | 指令 |
|---|---|
| 基础 | `/注册` `/签到` `/帮助` `/商城` `/碎片` `/主将 <武将>` |
| 招募 | `/兑换` `/架空招募` `/架空十连` `自由武将招募 <名字>`（无前缀） |
| 建筑 | `/宿舍` `/宿舍升级` |
| 武将 | `/武将` `/图鉴` `/合成 n\|r\|sr` `/遣散 <武将>` `/卡牌 <武将>` |
| 养成 | `/培养 <武将> [次数]` `/升星 <武将>` `/技能 <武将> [槽]` |
| 技能 | `/技能店 [主动\|被动]` `/兑换技能书 <技能名>` `/学技能 <武将> <技能名>` |
| 阵容/战斗 | `/阵容` `/上阵 <武将>` `/下阵 <武将>` `/主将 <武将>` `/对战 <玩家>` `/切磋 <玩家>` `/排行` |
| 副本 | `/副本 [章节]` `/挑战 <关卡>` `/扫荡 <关卡> [次数]` |
| 装备 | `/装备` `/锻造` `/强化 <序号>` `/穿戴 <序号> <武将>` `/卸下 <武将> <部位>` |
| 商店 | `/商店 每日\|每周\|黑市\|活动` `/商店 购买 <商品ID> [数量]` `/商店 锁定\|解锁` `/商店 兑换所 [分类]` `/商店 兑换 <规则ID> [次数]` |
| 拍卖 | `/拍卖 查看\|我的` `/拍卖 上架装备\|上架碎片 ...` `/拍卖 出价 <编号> <金额>` `/拍卖 一口价 <编号>` `/拍卖 下架 <编号>` |
| 背包 | `/背包` `/使用 <道具> [数量]` `/选择 <礼盒> <选项>` |
| 势力 | `/势力` `/加入 <魏\|蜀\|吴\|群>` `/捐献 <数量>` `/势力战` |
| 军团 | `/军团` `/创建军团 <名字>` `/加入军团 <ID>` `/退出军团` `/军团捐献 <金币>` `/军团排行` |
| 好友 | `/好友` `/加好友 <QQ>` `/赠体力 <QQ>`（赠送行动力） |
| 运营 | `/任务` `/成就` `/领取` `/邮件` `/领邮件 [编号]` `/战令` `/战令领取` `/战令购买` `/活动` |
| 世界BOSS | `/世界boss`（别名 `/世界BOSS`）`/讨伐` |
| GM | `/gm 查询\|发放\|维护\|审计\|回滚\|世界boss\|开活动\|关活动`（仅管理员） |

> QQ 官方接口不支持 At 消息段：`@玩家` 类指令可改为直接输入 QQ 号，如 `/对战 123456789`。

## 部署

1. 将 `liufeng_sanguo_game/` 放入 `AstrBot/data/plugins/`
2. 在 AstrBot WebUI 插件页刷新/重载插件
3. 接入 QQ（推荐 QQ Official Bot WebSocket 或 OneBot v11）
4. 群内发送 `/注册` 开始游戏
5. 管理台：插件详情页 →「三国管理台」

## 开发

```bash
python tools/build_tables.py            # 重新生成武将/技能/羁绊数据表
python tools/build_skill_effects.py     # 重新生成 350 技能效果库
python tools/build_troop_effects.py     # 重新生成 100 兵种效果库
python tools/build_battlepass.py        # 重新生成战令数据表
python -m pytest -q                     # 运行单元测试（82 项，不需要 astrbot）
python -m compileall core systems main.py
```

## 配置

见 `_conf_schema.json`：初始金币、签到/对战奖励、招募概率与失败区间、宿舍参数、副本掉率、行动力、文转图开关、维护模式、超管/管理台白名单、世界BOSS/战令/活动开关、**技能系统开关与技能书参数**等，均可在 WebUI 插件配置中调整。

## 管理台

插件详情页打开「三国管理台」（全中文，**14 页**）：仪表盘（多维指标 + 维护模式一键开关）/ 玩家管理（资料、货币资源、邮件发放、武将道具增删、封禁、删除连带清理）/ 武将库（搜索筛选分页 + 自定义武将增删改）/ 技能工坊（技能与公式/效果编辑）/ 兵种库 / 兵种效果库 / 道具工坊 / 军团管理 / 装备管理（蓝图 + 玩家装备）/ 拍卖行 / 活动管理 / 定时任务（**中文任务名，支持自定义定时任务**：12 类动作 + 中文参数、固定间隔、持久化热重载）/ 世界BOSS / 广播推送（**群聊广播**：目标可选群聊/私聊/全部，默认群聊，回显成功/失败/跳过；**当前默认已临时禁用**，可在配置 `system.enable_broadcast` 开启）。仅管理员可用（`admin.web_admins` 白名单）。

---

作者：柳弗罗　|　版本：1.2.0
