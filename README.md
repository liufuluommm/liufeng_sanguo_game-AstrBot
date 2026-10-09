# 柳弗罗三国演义 · AstrBot 插件

> 版本 `1.1.0`　AstrBot `>=4.17.0`　支持 `aiocqhttp` / `qq_official`
> 一款接入 QQ 群的三国题材**卡牌收集 / 养成 / 对战**游戏插件，自带 WebUI 管理台与 GM 工具。

**English:** LiuFeng Romance of the Three Kingdoms is an AstrBot plugin that turns a QQ group chat into a living Three Kingdoms world. It is a card-collection, character-development, and battle game: players register, sign in daily, recruit generals, and grow an army. It features 370 generals (historical, obscure, and fictional), each with six attributes—Force, Intellect, Vitality, Charisma, Eloquence, and Speed—that affect both power and combat. Players level up and star-up generals, collect equipment, challenge PVE dungeons, a world boss, or duel other players 1v1. Shops, currency exchange, an auction house, factions, guilds, quests, a season pass, and events keep communities engaged. The bot owner gets a WebUI admin console and GM tools.

**中文简介：** 柳弗罗三国演义把一个 QQ 群聊变成一个鲜活的三国世界。玩家注册、每日签到、招募武将，逐步壮大军团。插件收录 370 名武将（历史、冷门、架空），每位拥有六维能力——武力、智力、体力、魅力、口才、速度——计入战力并影响战斗。玩家升级升星、收集装备，挑战副本 PVE、世界BOSS，或与其他玩家 1v1 对决；商城、货币兑换、拍卖行、势力、军团、任务、战令与限时活动持续提供动力。机器人所有者配有 WebUI 管理台与 GM 工具。

## 功能总览

- **武将库**：历史 150 + 冷门 100 + 架空 120（共 370），**多维能力（武力/智力/体力/魅力/口才/速度）**，自动生成技能与羁绊；管理台可自定义增删武将
- **招募三线**：碎片兑换（15 通用碎片随机出历史/冷门武将）、架空招募（金币 5000/次，失败率 25%~30%）、自定义武将（无前缀 `自由武将招募 名字`）
- **养成**：升级、升星、技能、图鉴、合成、遣散
- **战斗**：PvP **1v1**（`/主将` 指定出战）/ PVE 3v3 回合制、兵种克制（骑→弓→枪→骑）、羁绊加成、竞技评分
- **装备**：武器/防具/坐骑/宝物，锻造、强化、穿戴
- **副本 PVE**：黄巾之乱 → 虎牢关 → 官渡 → 赤壁 → 夷陵 → 五丈原（六章 24 关），行动力、碎片掉落（5%~15%）、扫荡
- **经营**：系统商城（每日/每周/黑市/活动）、兑换所（单向）、拍卖行（一口价+竞拍+保证金+抽税）、道具效果引擎、背包、限时 buff
- **社交**：势力国战、军团、好友、切磋
- **运营**：任务、成就、邮件、战令、限时活动、世界BOSS、定时推送、维护模式
- **展示**：文转图武将卡牌（`/卡牌 <武将>`，无 Playwright 时自动回退纯文本）
- **管理台**：WebUI 页面（仪表盘 / 玩家 / **武将库增删改** / **道具工坊选项化编辑** / 广播）+ GM 指令（分级、审计、回滚）

## 多维能力（武将属性）

| 维度 | 战斗作用 |
|---|---|
| 武力 force | 物理攻击 |
| 体力 vitality | 生命上限 |
| 速度 speed | 出手顺序（先手） |
| 智力 intellect | 防御 + 暴击率 |
| 魅力 charisma | 团队光环（提升己方攻防） |
| 口才 eloquence | 概率“说服”削弱敌方攻击 |

战力 = `武力×2 + 智力×1.5 + 体力×1.5 + 魅力×1 + 口才×1 + 速度×1.2`，再叠加星级系数、等级成长与装备加成。
历史武将按史实生成，架空与自定义武将随机生成。

## 目录结构

```
liufeng_sanguo_game/
├── metadata.yaml  requirements.txt  _conf_schema.json  README.md
├── main.py                 # 插件入口：全部指令 handler + 无前缀监听 + 调度器 + Web API
├── core/                   # storage / config / utils / security / audit / maintenance / scheduler / event_bus
├── systems/                # 各玩法逻辑（纯 Python，可单元测试）
│   └── generals_admin.py   # 自定义武将增删改（写回数据目录并热重载）
├── tables/                 # 静态数据表（武将/技能/羁绊/装备/副本/道具/商店/兑换/任务/成就/效果/战令/活动/BOSS）
├── templates/              # 文转图 HTML 模板（武将六维卡、战报）
├── pages/admin/            # WebUI 管理台页面
├── tests/                  # pytest 单元测试
└── tools/                  # 数据表生成脚本（build_tables.py / build_battlepass.py）
```

## 数据存储

- 每个 QQ 号独立文件夹：`data/plugin_data/liufeng_sanguo_game/players/<QQ>/player.json`
- 跨群全局数据：`.../global/*.json`（排行榜、势力、军团、拍卖、世界BOSS、活动、战令、会话索引、审计、维护状态等）
- 管理台自定义数据：`.../generals_custom.json`（自定义武将）、`.../items_custom.json`（自定义道具）
- 原子写入 + 进程内加锁；AstrBot 官方数据目录 `get_astrbot_data_path()/plugin_data/<name>`

## 指令速查（无需 `sg` 前缀）

| 类别 | 指令 |
|---|---|
| 基础 | `/注册` `/签到` `/帮助` `/商城` `/碎片` |
| 招募 | `/兑换` `/架空招募` `/架空十连` `自由武将招募 <名字>`（无前缀） |
| 武将 | `/武将` `/培养` `/升星` `/技能` `/图鉴` `/合成` `/遣散` `/卡牌` |
| 建筑 | `/宿舍` `/宿舍升级` |
| 战斗 | `/阵容` `/上阵` `/下阵` `/主将` `/对战 @玩家` `/切磋 @玩家` `/排行` |
| 副本 | `/副本` `/挑战 <关卡>` `/扫荡 <关卡> [次数]` |
| 装备 | `/装备` `/锻造` `/强化 <序号>` `/穿戴 <序号> <武将>` `/卸下 <武将> <部位>` |
| 商店 | `/商店 每日\|每周\|黑市\|活动` `/商店 购买 <店> <商品ID> [数量]` `/商店 兑换所` `/商店 兑换 <规则ID> [次数]` |
| 拍卖 | `/拍卖 查看\|我的` `/拍卖 上架装备\|上架碎片 ...` `/拍卖 出价 <编号> <金额>` `/拍卖 一口价 <编号>` `/拍卖 下架 <编号>` |
| 背包 | `/背包` `/使用 <道具> [武将]` `/选择 <序号>` |
| 势力 | `/势力` `/加入 <魏\|蜀\|吴\|群>` `/捐献 <金币>` `/势力战` |
| 军团 | `/军团` `/创建军团 <名字>` `/加入军团 <ID>` `/军团捐献 <金币>` `/军团排行` |
| 好友 | `/好友` `/加好友 @玩家` `/赠体力 @玩家`（赠送行动力） |
| 任务 | `/任务` `/成就` `/领取 <ID>` `/邮件` `/领邮件 <序号\|全部>` |
| 战令 | `/战令` `/战令领取 <等级> <免费\|进阶>` `/战令购买` |
| 活动 | `/活动` |
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
python tools/build_tables.py        # 重新生成武将/技能/羁绊数据表
python tools/build_battlepass.py    # 重新生成战令数据表
python -m pytest -q                 # 运行单元测试（不需要 astrbot）
python -m compileall core systems main.py
```

## 配置

见 `_conf_schema.json`：初始金币、签到/对战奖励、招募概率与失败区间、宿舍参数、副本掉率、行动力、市场税率、文转图开关、维护模式、超管列表、世界BOSS/战令/活动开关等，均可在 WebUI 插件配置中调整。

## 管理台

插件详情页打开「三国管理台」：仪表盘 / 玩家管理 / 武将库（搜索筛选分页 + 自定义武将增删改，六维编辑）/ 道具工坊（类别/品质/货币/商店/效果全部下拉选项，写回数据目录）/ 广播推送。仅管理员可用（`admin.web_admins` 白名单）。

---

作者：柳弗罗　|　版本：1.1.0
