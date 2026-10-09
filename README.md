# 柳弗罗三国演义 · 插件开发版本说明

> ## 🆕 本次更新了什么（v1.1.0）
>
> | # | 更新内容 | 影响 |
> |---|---|---|
> | 1 | 武将属性 三维 → **多维能力**（武力/智力/体力/魅力/口才/速度） | 计入战力，并影响战斗 |
> | 2 | 玩家对战 3v3 → **1v1**，新增 `/主将 <武将>` | PvE 副本仍 3v3 |
> | 3 | 管理台**汉化 + 选项化**，武将库支持**自定义武将增删改**（六维编辑） | 后台可视化运营 |
> | 4 | 修复 AstrBot 加载失败（相对导入、指令组权限装饰器） | 已真实环境验证通过 |
>
> 详细变更见 `更新日志.md`；审计结论见 `代码审计报告.md`。

## 一、基本信息

| 项 | 内容 |
|---|---|
| 插件名 | `liufeng_sanguo_game` |
| 显示名 | 柳弗罗三国演义 |
| 版本 | `1.1.0` |
| 版本日期 | 2026-10-09 |
| 作者 | 柳弗罗 |
| AstrBot 版本要求 | `>=4.17.0` |
| 支持平台 | `aiocqhttp`（OneBot v11 / QQ 个人号）、`qq_official`（QQ 官方机器人） |
| 数据目录 | `data/plugin_data/liufeng_sanguo_game/` |

## 二、简介

一款接入 QQ 群的三国题材**卡牌收集 / 养成 / 对战**游戏插件，内置完整经济、经营、社交与运营体系，并提供 WebUI 管理台与 GM 工具。核心循环：**招募武将 → 养成变强 → 挑战副本 / 群友对战 → 收集更多武将**。

## 三、功能总览

| 模块 | 内容 |
|---|---|
| 武将体系 | 历史 150 / 冷门 100 / 架空 120（共 370），含**多维能力（武力/智力/体力/魅力/口才/速度）**、技能、称号、兵种、羁绊；管理台可自定义增删武将 |
| 多维能力 | 六维**计入战力**并**影响战斗**：武力→攻击、体力→生命、速度→先手、智力→防御/暴击、魅力→团队光环、口才→削弱敌方；历史武将按史实生成，架空/自定义随机生成 |
| 招募 | 碎片兑换（历史+冷门）、架空招募（金币，失败率 25%–30%）、自定义武将（无前缀 `自由武将招募 名字`） |
| 养成 | 升级、升星、技能、图鉴、合成、遣散、阵容、羁绊 |
| 战斗 | PvP **1v1**（出战主将）/ PVE 3v3 回合制、兵种克制（骑→弓→枪→骑）、羁绊加成、竞技评分 |
| 装备 | 武器/防具/坐骑/宝物，锻造、强化、穿戴、卸下 |
| 副本 PVE | 黄巾之乱 → 虎牢关 → 官渡 → 赤壁 → 夷陵 → 五丈原（六章 24 关），行动力、碎片掉落、扫荡 |
| 经营 | 系统商城（每日/每周/黑市/活动）、兑换所（单向）、拍卖行（一口价+竞拍+保证金+抽税） |
| 道具 | 效果引擎（schema 驱动）、背包、限时 buff、礼包开箱、自选礼包 |
| 社交 | 势力国战、军团（公会）、好友、切磋 |
| 运营 | 任务、成就、战令、限时活动（四类全局 buff）、邮件、定时推送 |
| 世界BOSS | 全服共战、伤害排行、邮件发奖（GM 控制开启） |
| 展示 | 文转图武将卡牌（`/卡牌`），无 Playwright 时自动回退纯文本 |
| 管理台 | WebUI 页面（仪表盘 / 玩家 / 武将库 / 道具工坊 / 广播）+ GM 指令（分级、审计、回滚） |

## 四、系统架构

```
liufeng_sanguo_game/
├── metadata.yaml            # 插件元数据
├── requirements.txt         # 依赖声明
├── _conf_schema.json        # 可视化配置项
├── main.py                  # 插件入口：全部指令 handler、无前缀监听、调度器、Web API
├── core/                    # 基础设施
│   ├── storage.py           # 按 QQ 分文件 + 全局跨群文件、原子写、加锁、数据目录解析
│   ├── config.py            # 配置默认值与读取
│   ├── utils.py             # 战力计算、时间、随机、文案格式化
│   ├── security.py          # 冷却、限流、防刷
│   ├── audit.py             # GM 审计与回滚快照
│   ├── maintenance.py       # 维护模式
│   ├── scheduler.py         # 异步定时任务引擎
│   └── event_bus.py         # 行为事件总线
├── systems/                 # 玩法逻辑（纯 Python，可单测）
│   ├── player.py  gacha.py  building.py  cultivate.py  collection.py  team.py
│   ├── battle.py  dungeon.py  equipment.py  ranking.py
│   ├── items.py  inventory.py  buff.py  shop.py  exchange.py  auction.py
│   ├── faction.py  guild.py  social.py
│   ├── quest.py  mail.py  battlepass.py  events.py  worldboss.py
│   ├── generals_admin.py    # 自定义武将增删改（写回数据目录并热重载）
│   └── tables.py  render.py
├── tables/                  # 静态数据表（武将/技能/羁绊/装备/副本/道具/商店/兑换/任务/成就/效果/战令/活动/BOSS）
├── templates/               # 文转图 HTML 模板（武将卡、战报）
├── pages/admin/             # WebUI 管理台页面（index.html / app.js / style.css）
├── tests/                   # pytest 单元测试
└── tools/                   # 数据表生成脚本
```

## 五、数据存储规范

- **按 QQ 号分文件**：`data/plugin_data/liufeng_sanguo_game/players/<QQ>/player.json`（QQ 号即唯一键）。
- **跨群全局数据**：`.../global/*.json`（排行榜、势力、军团、拍卖、世界BOSS、活动、战令、会话索引、审计、维护状态等）。
- **原子写入**：临时文件 + `os.replace`，进程内加锁，避免写坏存档。
- **数据目录**：优先使用 AstrBot 官方 `get_astrbot_data_path()/plugin_data/<name>`，兼容 `get_astrbot_plugin_data_path()`；开发环境回退 `local_data/`。
- 自定义道具（管理台上架）持久化于数据目录 `items_custom.json`；**自定义武将**持久化于 `generals_custom.json`，均不随插件更新丢失。

## 六、安装与部署

1. 将 `liufeng_sanguo_game/` 放入 `AstrBot/data/plugins/` 下。
2. 在 AstrBot WebUI 插件页刷新/重载插件。
3. 接入 QQ（推荐 QQ Official Bot WebSocket 或 OneBot v11）。
4. 群内发送 `/注册` 开始游戏。
5. 管理台：插件详情页 →「三国管理台」。

## 七、配置项（`_conf_schema.json`）

- `enable`：总开关
- `game`：初始金币、签到/对战奖励、战斗波动
- `gacha`：碎片兑换数、稀有度概率、架空招募花费与失败区间、自定义招募花费与多维区间、宿舍参数
- `dungeon`：碎片掉率区间
- `stamina`：行动力上限与恢复
- `text_image`：文转图开关与主题
- `system`：调度器、主动推送、维护模式、冷却
- `admin`：超管 QQ 列表、管理台用户名白名单
- `worldboss` / `battlepass` / `events`：对应系统开关与参数

## 八、管理台

插件详情页打开「三国管理台」（已全中文），仅管理员可用（`admin.web_admins` 白名单）：

- **仪表盘**：注册玩家 / 武将总数 / 道具总数 / 维护模式。
- **玩家管理**：按战力排序，势力等字段中文展示。
- **武将库**：搜索、品质/势力筛选、分页；**自定义武将新增/编辑/删除**（六维数值编辑）；内部键默认隐藏（可切换显示）。
- **道具工坊**：类别/品质/货币/商店/效果类型/枚举参数**全部下拉选项**；效果支持礼包（随机）与自选，写回数据目录并热重载。
- **广播推送**：向订阅会话群发公告（自动跳过不支持主动消息的平台）。

## 九、运行环境与依赖

- Python 3.10+（开发环境 3.11）
- AstrBot `>=4.17.0`
- `requirements.txt`：`aiofiles>=23.0.0`
- 文转图依赖 AstrBot 的 Playwright 渲染能力；不可用时自动回退纯文本

## 十、已知限制

- QQ 官方接口**不支持 At 消息段**：`@` 类指令需改用 QQ 号；且**不支持主动消息**，定时推送/广播自动跳过该类会话。
- 定时任务需 AstrBot 运行事件循环；调度器在 `on_astrbot_loaded` 钩子中启动。
- GM 权限基于 AstrBot 管理员 + 插件超管白名单，建议上线前实测。

