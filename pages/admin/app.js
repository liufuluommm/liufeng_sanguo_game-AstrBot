const bridge = window.AstrBotPluginPage;
const view = document.getElementById("view");

// ---------------- 标签映射（内部键 -> 中文） ----------------
const FACTION = { wei: "魏", shu: "蜀", wu: "吴", qun: "群", custom: "自定义", "": "-" };
const CATEGORY = { historical: "历史武将", obscure: "冷门武将", fictional: "架空武将", custom: "自定义武将" };
const ITEM_CAT = { resource: "资源", consume: "消耗品", buff: "增益", gift: "礼包", functional: "功能", equipment: "装备" };
const CURRENCY = { gold: "金币", diamond: "元宝", merit: "功勋", soul: "将魂", repute: "声望",
  event_ticket: "活动券", challenge: "挑战令", skill_frag: "技能书碎片", fragments: "通用碎片", stamina: "行动力" };
const SHOP = { daily: "每日", weekly: "每周", black: "黑市", event: "活动" };
const RARITY = { ssr: "超稀有", sr: "史诗", r: "稀有", n: "普通", custom: "自定义", any: "任意" };
const BUFF = { double_drop: "双倍掉落", double_gold: "双倍金币", double_exp: "双倍经验", free_stamina: "免行动力" };
const TROOP = {
  infantry: "步兵", cavalry: "骑兵", archer: "弓兵", spear: "枪兵",
  heavy_infantry: "重步兵", iron_cavalry: "铁骑", heavy_archer: "强弩兵", pike: "长枪兵",
  hubaoqi: "虎豹骑", baier: "白毦兵", xianzhen: "陷阵营", jinfan: "锦帆军",
  wudang: "无当飞军", tengjia: "藤甲兵", xiangbing: "象兵", baima: "白马义从",
};
const TIER = { basic: "基础兵种", elite: "精锐兵种", special: "特殊兵种" };
const STAT_ATTR_LABEL = {
  atk: "攻击", def: "物防", mag_def: "法防", hp: "生命", speed: "速度", crit: "暴击",
  crit_dmg: "暴伤", dodge: "闪避", lifesteal: "吸血", spellvamp: "法术吸血",
  reduction: "免伤", tenacity: "韧性", reflect: "反伤", cdr: "冷却缩减",
  atkspeed: "攻速", pen_flat: "固定穿透", mana: "法力",
};
const MECH_LABEL = {
  magic_vuln: "受谋略伤害提升", extra_hit_chance: "普攻概率追加一击",
  knockup_chance: "普攻概率击飞", first_strike: "首回合先手", low_hp_atk: "生命越低攻击越高",
};
const OPTION_LABELS = Object.assign({}, RARITY, CURRENCY, BUFF, TROOP,
  { historical: "历史", obscure: "冷门", fictional: "架空" });

function lbl(map, key) { return key == null ? "" : (map[key] || key); }
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
  }[c]));
}
function opts(items, sel, labelFn) {
  return items.map((v) => `<option value="${esc(v)}" ${String(v) === String(sel) ? "selected" : ""}>${esc(labelFn ? labelFn(v) : v)}</option>`).join("");
}
function troopOptions(troops, tiers, sel, labels) {
  const byTier = {};
  (troops || []).forEach((t) => {
    const tier = (tiers && tiers[t]) || "basic";
    (byTier[tier] = byTier[tier] || []).push(t);
  });
  const order = ["basic", "elite", "special"];
  return order.filter((k) => byTier[k]).map((k) =>
    `<optgroup label="${esc(lbl(TIER, k))}">` +
    byTier[k].map((t) => `<option value="${esc(t)}" ${String(t) === String(sel) ? "selected" : ""}>${esc((labels && labels[t]) || TROOP[t] || t)}</option>`).join("") +
    `</optgroup>`).join("");
}

async function ready() {
  try {
    const ctx = await bridge.ready();
    if (ctx && ctx.displayName) document.title = ctx.displayName;
  } catch (e) { /* ignore */ }
}
async function api(endpoint, params) {
  try { return await bridge.apiGet(endpoint, params || {}); }
  catch (e) { return { __error: e.message || String(e) }; }
}
async function post(endpoint, body) {
  return bridge.apiPost(endpoint, body || {});
}

// ---------------- 仪表盘 ----------------
function num(n) {
  const v = Number(n || 0);
  return v.toLocaleString("en-US");
}
function fmtTs(ts) {
  const n = Number(ts || 0);
  return n > 0 ? new Date(n * 1000).toLocaleString("zh-CN") : "-";
}
async function renderDashboard() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const s = await api("admin/stats");
  if (s.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(s.__error)}</div>`; return; }
  document.getElementById("version").textContent = "v" + (s.version || "-");
  const mnt = s.maintenance || {};
  const wb = s.worldboss || {};
  const wbText = wb.active ? `${wb.name || "进行中"}（${num(wb.hp)}/${num(wb.max_hp)}）` : "未开启";
  const card = (k, v) => `<div class="card"><div class="k">${esc(k)}</div><div class="v">${esc(String(v))}</div></div>`;
  view.innerHTML = `
    <div class="muted">游戏概况（实时统计）</div>
    <div class="cards">
      ${card("注册玩家", num(s.players))}
      ${card("今日签到", num(s.sign_today))}
      ${card("累计金币", num(s.total_gold))}
      ${card("自定义武将", num(s.custom_generals))}
      ${card("武将总数", num(s.generals))}
      ${card("兵种数", num(s.troops))}
      ${card("兵种效果", num(s.troop_effects))}
      ${card("技能总数", num(s.skills))}
      ${card("道具总数", num(s.items))}
      ${card("装备总数", num(s.equipment))}
      ${card("军团数", num(s.guilds))}
      ${card("拍卖挂牌", num(s.auction))}
      ${card("活跃活动", num(s.active_events))}
      ${card("定时任务", num(s.jobs))}
    </div>
    <div class="cards" style="margin-top:14px">
      <div class="card"><div class="k">世界BOSS</div><div class="v" style="font-size:18px">${esc(wbText)}</div></div>
      <div class="card"><div class="k">维护模式</div><div class="v" style="font-size:20px;color:${mnt.on ? "#e5484d" : "var(--accent)"}">${mnt.on ? "开启" : "关闭"}</div></div>
    </div>
    <div class="card" id="mntPanel" style="margin-top:14px">
      <div class="muted">维护模式：<b>${mnt.on ? "开启" : "关闭"}</b>${mnt.reason ? `（原因：${esc(mnt.reason)}）` : ""}${mnt.ts ? ` · ${esc(fmtTs(mnt.ts))}` : ""}</div>
      <div class="row" style="margin-top:8px">
        <div class="col muted">维护原因（可选）<input id="mntReason" value="${esc(mnt.reason || "")}" placeholder="例如：版本更新维护，预计 10 分钟" /></div>
        <div class="col" style="display:flex;align-items:flex-end">
          <button class="${mnt.on ? "tab" : "primary"}" id="mntToggle">${mnt.on ? "关闭维护模式" : "开启维护模式"}</button>
        </div>
      </div>
      <div id="mntMsg" class="muted"></div>
    </div>`;
  document.getElementById("mntToggle").addEventListener("click", async () => {
    const on = !mnt.on;
    const reason = document.getElementById("mntReason").value.trim();
    if (!confirm(on ? "确认开启维护模式？开启后玩家将无法使用游戏指令。" : "确认关闭维护模式？")) return;
    try {
      await post("admin/maintenance", { on, reason });
      renderDashboard();
    } catch (e) {
      document.getElementById("mntMsg").textContent = "操作失败：" + (e.message || e);
    }
  });
}

// ---------------- 玩家管理 ----------------
let playerSearch = "";
async function renderPlayers() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/players", playerSearch ? { q: playerSearch } : {});
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const rows = (data.players || []).map((p) => `
    <tr>
      <td>${esc(p.name)}${p.banned ? ' <span class="badge" style="background:#e5484d;color:#fff">封禁</span>' : ""}<div class="muted">${esc(p.qq)}</div></td>
      <td>${p.power}</td>
      <td>${p.generals}<span class="muted">/${p.custom}自定义</span></td>
      <td>${p.gold}</td>
      <td>${esc(lbl(FACTION, p.faction))}</td>
      <td>${p.win}胜${p.lose}负</td>
      <td>
        <button class="tab" data-player="${esc(p.qq)}">详情/编辑</button>
        <button class="tab" data-ban="${esc(p.qq)}" data-banned="${p.banned ? 1 : 0}">${p.banned ? "解封" : "封禁"}</button>
        <button class="tab" data-delplayer="${esc(p.qq)}" data-name="${esc(p.name)}">删除</button>
      </td>
    </tr>`).join("");
  view.innerHTML = `
    <div class="row" style="margin-top:4px">
      <div class="col muted">搜索（玩家名或 QQ）<input id="pq" value="${esc(playerSearch)}" placeholder="输入后自动筛选" /></div>
    </div>
    <div class="muted">共 ${data.total} 名玩家，按战力排序</div>
    <table>
      <thead><tr><th>玩家</th><th>战力</th><th>武将</th><th>金币</th><th>势力</th><th>战绩</th><th>操作</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="7" class="muted">无</td></tr>'}</tbody>
    </table>
    <div id="playerHost" style="margin-top:16px"></div>`;
  const inp = document.getElementById("pq");
  inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { playerSearch = e.target.value.trim(); renderPlayers(); } });
  inp.addEventListener("change", () => { playerSearch = inp.value.trim(); renderPlayers(); });
  view.querySelectorAll("[data-player]").forEach((b) => b.addEventListener("click", () => renderPlayerDetail(b.dataset.player)));
  view.querySelectorAll("[data-ban]").forEach((b) => b.addEventListener("click", async () => {
    const banned = b.dataset.banned === "1";
    const reason = banned ? "" : (prompt("封禁原因（可选）", "") || "");
    if (!banned && reason === null) return;
    if (!confirm(banned ? "确认解封该玩家？" : "确认封禁该玩家？")) return;
    try { await post("admin/player/ban", { qq: b.dataset.ban, banned: !banned, reason }); renderPlayers(); } catch (e) { /* ignore */ }
  }));
  view.querySelectorAll("[data-delplayer]").forEach((b) => b.addEventListener("click", async () => {
    const qq = b.dataset.delplayer;
    if (!confirm("确认删除玩家【" + b.dataset.name + " / " + qq + "】？\n将连带清理军团/国战/拍卖/世界BOSS等关联数据，且不可恢复！")) return;
    const typed = prompt("危险操作：请输入该玩家 QQ 以确认删除", "");
    if (typed !== qq) { alert("QQ 不匹配，已取消。"); return; }
    try { const res = await post("admin/player/delete", { qq }); alert("已删除" + (res.guild_dissolved ? "；解散军团「" + res.guild_dissolved + "」" : "")); renderPlayers(); }
    catch (e) { alert("删除失败：" + (e.message || e)); }
  }));
}

async function renderPlayerDetail(qq) {
  const host = document.getElementById("playerHost");
  host.innerHTML = '<div class="loading">加载中…</div>';
  const o = await ensureGenOptions();
  const data = await api("admin/player/" + encodeURIComponent(qq));
  if (data.__error) { host.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const genData = await api("admin/generals");
  const itemData = await api("admin/items");
  const allGeneralNames = [];
  if (genData && genData.categories) Object.values(genData.categories).forEach((lst) => (lst || []).forEach((g) => allGeneralNames.push(g.name)));
  const allItems = (itemData && itemData.items) || [];
  const customs = Object.values(data.custom_generals || {});
  const owned = Object.keys(data.generals || {});
  const inventory = data.inventory || {};
  const wallet = data.wallet || {};
  const troopSel = (sel) => troopOptions(o.troops || [], o.troop_tiers, sel || "infantry", o.troop_labels);
  const attrInputs = (g) => (o.attrs || []).map((a) =>
    `<div class="col muted">${esc(a.label)}<input id="cg_${esc(g.name)}_${esc(a.key)}" type="number" value="${esc(g[a.key] != null ? g[a.key] : 50)}" /></div>`).join("");
  const balance = (c) => c === "gold" ? (data.gold || 0) : (c === "fragments" ? (data.fragments || 0) : (c === "stamina" ? (data.stamina || 0) : (wallet[c] || 0)));
  const curChips = Object.keys(CURRENCY).map((c) => `<span class="muted" style="margin-right:10px">${esc(lbl(CURRENCY, c))} <b>${balance(c)}</b></span>`).join("");
  const curOpts = Object.keys(CURRENCY).map((c) => `<option value="${esc(c)}">${esc(lbl(CURRENCY, c))}</option>`).join("");
  const genOpts = allGeneralNames.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
  const itemOpts = allItems.map((i) => `<option value="${esc(i.id)}">${esc(i.name)}（${esc(i.id)}）</option>`).join("");
  const invRows = Object.entries(inventory).map(([id, c]) => {
    const it = allItems.find((x) => x.id === id);
    return `<tr><td>${esc(it ? it.name : id)}<div class="muted">${esc(id)}</div></td><td>${c}</td>
      <td><button class="tab item_del" data-id="${esc(id)}">移除1个</button></td></tr>`;
  }).join("");

  const customCards = customs.map((g) => `
    <div class="card" data-cg="${esc(g.name)}">
      <div class="muted"><b>${esc(g.name)}</b> · 自定义武将</div>
      <div class="row">
        <div class="col muted">等级<input class="cg_level" type="number" value="${esc(g.level || 1)}" /></div>
        <div class="col muted">星级<input class="cg_star" type="number" value="${esc(g.star || 1)}" /></div>
        <div class="col muted">兵种<select class="cg_troop">${troopSel(g.troop)}</select></div>
      </div>
      <div class="row">${attrInputs(g)}</div>
      <button class="primary cg_save" data-name="${esc(g.name)}">保存</button>
      <button class="tab cg_del" data-name="${esc(g.name)}">删除</button>
      <span class="muted cg_msg"></span>
    </div>`).join("");

  const ownedRows = owned.map((n) => `
    <tr><td>${esc(n)}</td>
      <td><input class="og_level" data-name="${esc(n)}" type="number" value="${esc((data.generals[n].level) || 1)}" /></td>
      <td><input class="og_star" data-name="${esc(n)}" type="number" value="${esc((data.generals[n].star) || 1)}" /></td>
      <td><button class="tab og_save" data-name="${esc(n)}">保存</button>
          <button class="tab og_del" data-name="${esc(n)}">移除</button></td>
    </tr>`).join("");

  host.innerHTML = `
    <div class="card">
      <div class="muted">玩家：<b>${esc(data.name || qq)}</b>（${esc(qq)}）　等级 ${data.level || 1}　宿舍容量 ${((data.buildings || {}).dormitory || {}).capacity || "-"}</div>
    </div>

    <div class="card">
      <div class="muted"><b>资料修改</b>（直接生效）</div>
      <div class="row">
        <div class="col muted">名称<input id="pf_name" value="${esc(data.name || "")}" /></div>
        <div class="col muted">等级<input id="pf_level" type="number" value="${esc(data.level || 1)}" /></div>
        <div class="col muted">经验<input id="pf_exp" type="number" value="${esc(data.exp || 0)}" /></div>
        <div class="col muted">势力<select id="pf_faction">${opts(["wei","shu","wu","qun","custom","fictional",""], data.faction || "", (v)=>v?lbl(FACTION,v):"（无）")}</select></div>
      </div>
      <div class="row">
        <div class="col muted">胜<input id="pf_win" type="number" value="${esc(data.win || 0)}" /></div>
        <div class="col muted">负<input id="pf_lose" type="number" value="${esc(data.lose || 0)}" /></div>
        <div class="col muted">竞技分<input id="pf_rating" type="number" value="${esc((data.pvp || {}).rating || 1000)}" /></div>
        <div class="col muted">行动力<input id="pf_stamina" type="number" value="${esc(data.stamina || 0)}" /></div>
        <div class="col muted">宿舍容量<input id="pf_dorm" type="number" value="${esc(((data.buildings || {}).dormitory || {}).capacity || 15)}" /></div>
      </div>
      <button class="primary" id="pf_save">保存资料</button>
      <span class="muted" id="pf_msg"></span>
    </div>

    <div class="card">
      <div class="muted"><b>货币与资源</b>（直接修正）</div>
      <div style="margin:6px 0">${curChips}</div>
      <div class="row">
        <div class="col muted">项目<select id="cur_kind">${curOpts}</select></div>
        <div class="col muted">方式<select id="cur_mode"><option value="add">增加</option><option value="sub">减少</option><option value="set">设定为</option></select></div>
        <div class="col muted">数量<input id="cur_amount" type="number" value="1000" /></div>
        <div class="col" style="display:flex;align-items:flex-end"><button class="primary" id="cur_apply">应用</button></div>
      </div>
      <span class="muted" id="cur_msg"></span>
    </div>

    <div class="card">
      <div class="muted"><b>邮件发放奖励</b>（货币/资源/道具/武将，统一走邮件附件）</div>
      <div class="row">
        <div class="col muted">邮件标题<input id="gv_title" value="系统奖励" /></div>
        <div class="col muted">正文<input id="gv_body" value="" /></div>
      </div>
      <div class="muted" style="margin-top:6px">资源（留空即不发）</div>
      <div class="row" id="gv_res">${Object.keys(CURRENCY).map((c) => `<div class="col muted" style="min-width:150px">${esc(lbl(CURRENCY, c))}<input class="gv_res" data-c="${esc(c)}" type="number" placeholder="0" /></div>`).join("")}</div>
      <div class="muted" style="margin-top:6px">道具</div>
      <div class="row">
        <div class="col muted">选择道具<select id="gv_item">${itemOpts}</select></div>
        <div class="col muted">数量<input id="gv_item_n" type="number" value="1" /></div>
      </div>
      <div class="muted" style="margin-top:6px">武将</div>
      <div class="row">
        <div class="col muted">选择武将<select id="gv_general">${genOpts}</select></div>
      </div>
      <button class="primary" id="gv_send">发送邮件发放</button>
      <span class="muted" id="gv_msg"></span>
    </div>

    <div class="card">
      <div class="muted"><b>自定义武将</b>（可修改全部属性与兵种）</div>
      ${customCards || '<div class="muted">无</div>'}
      <div class="muted" style="margin-top:10px"><b>其余持有武将</b>（可改等级/星级或移除）</div>
      <table><thead><tr><th>武将</th><th>等级</th><th>星级</th><th>操作</th></tr></thead><tbody>${ownedRows || '<tr><td colspan="4" class="muted">无</td></tr>'}</tbody></table>
    </div>

    <div class="card">
      <div class="muted"><b>道具背包</b></div>
      <table><thead><tr><th>道具</th><th>数量</th><th>操作</th></tr></thead><tbody>${invRows || '<tr><td colspan="3" class="muted">无</td></tr>'}</tbody></table>
    </div>

    <div class="card">
      <div class="muted"><b>批量清空</b></div>
      <button class="tab clr" data-target="inventory">清空背包</button>
      <button class="tab clr" data-target="custom_generals">清空自定义武将</button>
      <button class="tab clr" data-target="team">重置阵容</button>
      <span class="muted" id="clr_msg"></span>
    </div>

    <div class="card">
      <div class="muted"><b>封禁 / 解封</b></div>
      <div class="row">
        <div class="col muted">原因（可选）<input id="ban_reason" value="" /></div>
        <div class="col" style="display:flex;align-items:flex-end">
          <button class="tab" id="ban_btn">封禁该玩家</button>
        </div>
      </div>
      <span class="muted" id="ban_msg"></span>
    </div>

    <div class="card" style="border:1px solid #e5484d">
      <div class="muted"><b style="color:#e5484d">危险操作：删除玩家</b>（连带清理军团/国战/拍卖/世界BOSS；若为军团长则解散军团）</div>
      <div class="row">
        <div class="col muted">输入 QQ「${esc(qq)}」确认<input id="del_confirm" placeholder="请输入该玩家 QQ" /></div>
        <div class="col" style="display:flex;align-items:flex-end">
          <button class="tab" id="del_btn" style="color:#e5484d;border-color:#e5484d">确认删除</button>
        </div>
      </div>
      <span class="muted" id="del_msg"></span>
    </div>

    <div id="pdMsg" class="muted"></div>`;

  const postMsg = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };

  host.querySelector("#pf_save").addEventListener("click", async () => {
    const body = { qq,
      name: host.querySelector("#pf_name").value.trim(),
      level: parseInt(host.querySelector("#pf_level").value || "1", 10),
      exp: parseInt(host.querySelector("#pf_exp").value || "0", 10),
      faction: host.querySelector("#pf_faction").value,
      win: parseInt(host.querySelector("#pf_win").value || "0", 10),
      lose: parseInt(host.querySelector("#pf_lose").value || "0", 10),
      rating: parseInt(host.querySelector("#pf_rating").value || "1000", 10),
      stamina: parseInt(host.querySelector("#pf_stamina").value || "0", 10),
      dorm_capacity: parseInt(host.querySelector("#pf_dorm").value || "15", 10) };
    try { await post("admin/player/profile", body); postMsg("pf_msg", "✅ 已保存"); }
    catch (e) { postMsg("pf_msg", "保存失败：" + (e.message || e)); }
  });

  host.querySelector("#cur_apply").addEventListener("click", async () => {
    const body = { qq, currency: host.querySelector("#cur_kind").value,
      mode: host.querySelector("#cur_mode").value,
      amount: parseInt(host.querySelector("#cur_amount").value || "0", 10) };
    try { const r = await post("admin/player/currency", body); postMsg("cur_msg", "✅ 已更新，当前值 " + r.value); }
    catch (e) { postMsg("cur_msg", "操作失败：" + (e.message || e)); }
  });

  host.querySelector("#gv_send").addEventListener("click", async () => {
    const reward = {};
    host.querySelectorAll(".gv_res").forEach((el) => {
      const v = parseInt(el.value || "0", 10);
      if (v) reward[el.dataset.c] = v;
    });
    const itemId = host.querySelector("#gv_item").value;
    const itemN = parseInt(host.querySelector("#gv_item_n").value || "0", 10);
    if (itemId && itemN > 0) reward.items = { [itemId]: itemN };
    const gname = host.querySelector("#gv_general").value;
    if (gname) reward.generals = [gname];
    if (!Object.keys(reward).length) { postMsg("gv_msg", "⚠️ 奖励为空"); return; }
    const body = { qq, title: host.querySelector("#gv_title").value, body: host.querySelector("#gv_body").value, reward };
    try { await post("admin/player/give", body); postMsg("gv_msg", "✅ 已通过邮件发放"); }
    catch (e) { postMsg("gv_msg", "发放失败：" + (e.message || e)); }
  });

  host.querySelectorAll(".cg_save").forEach((b) => b.addEventListener("click", async () => {
    const name = b.dataset.name;
    const card = host.querySelector(`[data-cg="${CSS.escape(name)}"]`);
    const body = { qq, name, level: parseInt(card.querySelector(".cg_level").value || "1", 10),
      star: parseInt(card.querySelector(".cg_star").value || "1", 10), troop: card.querySelector(".cg_troop").value };
    (o.attrs || []).forEach((a) => {
      const el = card.querySelector(`#cg_${CSS.escape(name)}_${a.key}`);
      if (el) body[a.key] = parseInt(el.value || "50", 10);
    });
    try { await post("admin/player-general", body); card.querySelector(".cg_msg").textContent = "✅ 已保存"; }
    catch (e) { card.querySelector(".cg_msg").textContent = "保存失败：" + (e.message || e); }
  }));
  host.querySelectorAll(".cg_del, .og_del").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认移除武将「" + b.dataset.name + "」？")) return;
    try { await post("admin/player-general/delete", { qq, name: b.dataset.name }); renderPlayerDetail(qq); } catch (e) { /* ignore */ }
  }));
  host.querySelectorAll(".og_save").forEach((b) => b.addEventListener("click", async () => {
    const name = b.dataset.name;
    const body = { qq, name,
      level: parseInt(host.querySelector(`.og_level[data-name="${CSS.escape(name)}"]`).value || "1", 10),
      star: parseInt(host.querySelector(`.og_star[data-name="${CSS.escape(name)}"]`).value || "1", 10) };
    try { await post("admin/player-general", body); renderPlayerDetail(qq); }
    catch (e) { postMsg("pdMsg", "保存失败：" + (e.message || e)); }
  }));
  host.querySelectorAll(".item_del").forEach((b) => b.addEventListener("click", async () => {
    try { await post("admin/player/items", { qq, item_id: b.dataset.id, count: 1 }); renderPlayerDetail(qq); }
    catch (e) { postMsg("pdMsg", "移除失败：" + (e.message || e)); }
  }));
  host.querySelectorAll(".clr").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认清空「" + b.textContent + "」？")) return;
    try { await post("admin/player/clear", { qq, target: b.dataset.target }); renderPlayerDetail(qq); }
    catch (e) { postMsg("clr_msg", "失败：" + (e.message || e)); }
  }));
  host.querySelector("#ban_btn").addEventListener("click", async () => {
    const reason = host.querySelector("#ban_reason").value.trim();
    if (!confirm("确认封禁该玩家？")) return;
    try { await post("admin/player/ban", { qq, banned: true, reason }); postMsg("ban_msg", "✅ 已封禁"); }
    catch (e) { postMsg("ban_msg", "失败：" + (e.message || e)); }
  });
  host.querySelector("#del_btn").addEventListener("click", async () => {
    const typed = host.querySelector("#del_confirm").value.trim();
    if (typed !== qq) { postMsg("del_msg", "QQ 不匹配"); return; }
    if (!confirm("确认删除玩家 " + qq + " ？不可恢复！")) return;
    try { const res = await post("admin/player/delete", { qq }); postMsg("del_msg", "✅ 已删除" + (res.guild_dissolved ? "；解散军团「" + res.guild_dissolved + "」" : "")); setTimeout(renderPlayers, 800); }
    catch (e) { postMsg("del_msg", "删除失败：" + (e.message || e)); }
  });
}

// ---------------- 武将库（增删改 + 多维） ----------------
let genOptions = null;
let genFilter = { q: "", rarity: "", faction: "", page: 1 };
let showTech = false;

function techId(id) {
  return showTech && id ? `<div class="muted">${esc(id)}</div>` : "";
}

async function ensureGenOptions() {
  if (genOptions) return genOptions;
  const o = await api("admin/generals/options");
  genOptions = o.__error ? {} : o;
  if (genOptions.troop_labels) Object.assign(TROOP, genOptions.troop_labels);
  return genOptions;
}

function renderGeneralEditor(g, o) {
  const attrs = o.attrs || [];
  const attrInputs = attrs.map((a) => `
    <div class="col muted">${esc(a.label)}<input id="g_${esc(a.key)}" type="number" value="${esc((g && g[a.key]) != null ? g[a.key] : 50)}" /></div>
  `).join("");
  const idName = o.skill_id_name || {};
  const curActive = (g && g.skill && g.skill.active) ? (idName[g.skill.active] || g.skill.active) : "";
  const curPassive = (g && g.skill && g.skill.passive) ? (idName[g.skill.passive] || g.skill.passive) : "";
  const activeList = (o.skill_names && o.skill_names.active) || [];
  const passiveList = (o.skill_names && o.skill_names.passive) || [];
  const activeSel = `<option value="">（默认/自动）</option>` +
    activeList.map((n) => `<option value="${esc(n)}" ${n === curActive ? "selected" : ""}>${esc(n)}</option>`).join("");
  const passiveSel = `<option value="">（默认/自动）</option>` +
    passiveList.map((n) => `<option value="${esc(n)}" ${n === curPassive ? "selected" : ""}>${esc(n)}</option>`).join("");
  return `
    <div class="card" id="genEditor">
      <div class="row">
        <div class="col muted">名称<input id="g_name" value="${esc((g && g.name) || "")}" /></div>
        <div class="col muted">称号<input id="g_title" value="${esc((g && g.title) || "")}" /></div>
      </div>
      <div class="row">
        <div class="col muted">品质<select id="g_rarity">${opts(o.rarities || ["ssr","sr","r","n"], (g && g.rarity) || "sr", (v)=>lbl(RARITY,v))}</select></div>
        <div class="col muted">势力<select id="g_faction">${opts(o.factions || ["wei","shu","wu","qun","custom"], (g && g.faction) || "wei", (v)=>lbl(FACTION,v))}</select></div>
        <div class="col muted">兵种<select id="g_troop">${troopOptions(o.troops || ["cavalry","infantry","archer","spear"], o.troop_tiers, (g && g.troop) || "infantry", o.troop_labels)}</select></div>
      </div>
      <div class="row">${attrInputs}</div>
      <div class="row">
        <div class="col muted">主动技能<select id="g_active">${activeSel}</select></div>
        <div class="col muted">被动技能<select id="g_passive">${passiveSel}</select></div>
      </div>
      <div class="muted">描述<input id="g_desc" value="${esc((g && g.desc) || "")}" /></div>
      <button class="primary" id="saveGen">保存武将</button>
      <button class="tab" id="cancelGen">取消</button>
      <div id="genMsg" class="muted"></div>
    </div>`;
}

function collectGeneral(root, o) {
  const g = {
    name: root.querySelector("#g_name").value.trim(),
    title: root.querySelector("#g_title").value.trim(),
    rarity: root.querySelector("#g_rarity").value,
    faction: root.querySelector("#g_faction").value,
    troop: root.querySelector("#g_troop").value,
    skill: {
      active: root.querySelector("#g_active").value.trim(),
      passive: root.querySelector("#g_passive").value.trim(),
    },
    desc: root.querySelector("#g_desc").value,
  };
  (o.attrs || []).forEach((a) => {
    const el = root.querySelector("#g_" + a.key);
    g[a.key] = parseInt(el ? el.value || "50" : "50", 10);
  });
  return g;
}

async function renderGenerals() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const o = await ensureGenOptions();
  const data = await api("admin/generals");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const cats = data.categories || {};
  const all = [];
  Object.keys(cats).forEach((k) => cats[k].forEach((g) => all.push(g)));

  const counts = Object.keys(CATEGORY).filter((k) => cats[k]).map((k) =>
    `<div class="card"><div class="k">${CATEGORY[k]}</div><div class="v">${cats[k].length}</div></div>`).join("");

  const rarityOpts = `<option value="">全部品质</option>` + opts(o.rarities || ["ssr","sr","r","n"], "", (v)=>lbl(RARITY,v));
  const factionOpts = `<option value="">全部势力</option>` + opts(o.factions || ["wei","shu","wu","qun","custom"], "", (v)=>lbl(FACTION,v));

  function filtered() {
    const q = genFilter.q.trim();
    return all.filter((g) => {
      if (q && !String(g.name).includes(q)) return false;
      if (genFilter.rarity && g.rarity !== genFilter.rarity) return false;
      if (genFilter.faction && g.faction !== genFilter.faction) return false;
      return true;
    });
  }

  function listHtml() {
    const rowsAll = filtered();
    const pageSize = 20;
    const pages = Math.max(1, Math.ceil(rowsAll.length / pageSize));
    genFilter.page = Math.min(genFilter.page, pages);
    const start = (genFilter.page - 1) * pageSize;
    const pageRows = rowsAll.slice(start, start + pageSize);
    const rows = pageRows.map((g) => {
      const idx = all.indexOf(g);
      const custom = g.category === "custom";
      return `<tr>
        <td><span class="badge ${esc(g.rarity)}">${esc(lbl(RARITY, g.rarity))}</span> ${esc(g.name)}<div class="muted">${esc(g.title || "")}</div></td>
        <td>${esc(lbl(FACTION, g.faction))}</td>
        <td>${esc(lbl(TROOP, g.troop))}</td>
        <td>${["force","intellect","vitality","charisma","eloquence","speed"].map((k)=>g[k]).join("/")}</td>
        <td>
          ${custom ? `<button class="tab" data-edit="${idx}">编辑</button>
            <button class="tab" data-del="${esc(g.name)}">删除</button>`
            : `<span class="muted">历史数据</span>`}
        </td>
      </tr>`;
    }).join("");
    return { rows, pages, total: rowsAll.length };
  }

  function draw() {
    const { rows, pages, total } = listHtml();
    view.innerHTML = `
      <div class="cards">${counts}<div class="card"><div class="k">总计</div><div class="v">${data.total}</div></div></div>
      <div class="row" style="margin-top:14px">
        <div class="col muted">搜索<input id="gfq" value="${esc(genFilter.q)}" placeholder="武将名" /></div>
        <div class="col muted">品质<select id="gfr">${rarityOpts}</select></div>
        <div class="col muted">势力<select id="gff">${factionOpts}</select></div>
        <div class="col"><button class="primary" id="newGen">+ 新建武将</button>
          <label class="muted" style="margin-left:10px"><input type="checkbox" id="genTech" ${showTech ? "checked" : ""}/> 显示技术字段(ID)</label></div>
      </div>
      <div class="muted">共 ${total} 条，第 ${genFilter.page}/${pages} 页（仅“自定义武将”可编辑/删除）</div>
      <table><thead><tr><th>武将</th><th>势力</th><th>兵种</th><th>武力/智力/体力/魅力/口才/速度</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table>
      <div class="row" style="margin-top:8px">
        <button class="tab" id="prevPage">上一页</button>
        <button class="tab" id="nextPage">下一页</button>
      </div>
      <div id="genHost" style="margin-top:16px"></div>`;
    // restore selects
    document.getElementById("gfr").value = genFilter.rarity;
    document.getElementById("gff").value = genFilter.faction;
    document.getElementById("gfq").addEventListener("input", (e) => { genFilter.q = e.target.value; genFilter.page = 1; draw(); });
    document.getElementById("gfr").addEventListener("change", (e) => { genFilter.rarity = e.target.value; genFilter.page = 1; draw(); });
    document.getElementById("gff").addEventListener("change", (e) => { genFilter.faction = e.target.value; genFilter.page = 1; draw(); });
    document.getElementById("prevPage").addEventListener("click", () => { genFilter.page = Math.max(1, genFilter.page - 1); draw(); });
    document.getElementById("nextPage").addEventListener("click", () => { genFilter.page = Math.min(pages, genFilter.page + 1); draw(); });
    document.getElementById("newGen").addEventListener("click", () => openEditor(null));
    document.getElementById("genTech").addEventListener("change", (e) => { showTech = e.target.checked; draw(); });
    view.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openEditor(all[parseInt(b.dataset.edit, 10)])));
    view.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("确认删除自定义武将「" + b.dataset.del + "」？")) return;
      try { await post("admin/generals/delete", { name: b.dataset.del }); renderGenerals(); } catch (e) { /* ignore */ }
    }));
  }

  function openEditor(g) {
    const host = document.getElementById("genHost");
    host.innerHTML = renderGeneralEditor(g, o);
    host.querySelector("#cancelGen").addEventListener("click", () => {
      document.getElementById("genHost").innerHTML = "";
    });
    host.querySelector("#saveGen").addEventListener("click", async () => {
      const gen = collectGeneral(host, o);
      try {
        await post("admin/generals", gen);
        document.getElementById("genMsg").textContent = "✅ 已保存武将 " + gen.name;
        setTimeout(renderGenerals, 600);
      } catch (e) {
        document.getElementById("genMsg").textContent = "保存失败：" + (e.message || e);
      }
    });
  }

  draw();
}

// ---------------- 道具工坊（汉化 + 下拉） ----------------
let itemSchema = null;
async function ensureSchema() {
  if (itemSchema) return itemSchema;
  const s = await api("admin/effects/schema");
  itemSchema = s.__error ? {} : s;
  return itemSchema;
}

function effectParamInputs(effect, schema, idx) {
  const def = schema[effect.type] || { params: [] };
  return (def.params || []).map((p) => {
    const val = (effect.params || {})[p.key] != null ? (effect.params || {})[p.key] : (p.default != null ? p.default : "");
    const dataAttrs = `data-ef="${idx}" data-key="${p.key}"`;
    if (p.type === "enum") {
      const items = (p.options || []);
      const o = items.map((v) => `<option value="${esc(v)}" ${String(val) === String(v) ? "selected" : ""}>${esc(OPTION_LABELS[v] || v)}</option>`).join("");
      return `<div class="muted">${esc(p.label)}<select ${dataAttrs}>${o}</select></div>`;
    }
    if (p.type === "loot_table" || p.type === "choice_list") {
      const text = typeof val === "string" ? val : JSON.stringify(val);
      const hint = p.type === "loot_table"
        ? "奖池：每项 {weight:权重, effect:{type:效果类型, params:{参数}}}，按权重随机产出"
        : "选项：每项 {label:显示名, effect:{type:效果类型, params:{参数}}}，玩家从中选择";
      return `<div class="muted">${esc(p.label)}（JSON 高级编辑）
        <div class="muted" style="font-size:12px;opacity:.75">${hint}（type/params 取值见上方“效果”说明）</div>
        <textarea rows="4" ${dataAttrs}>${esc(text)}</textarea></div>`;
    }
    const inputType = p.type === "int" || p.type === "float" ? "number" : "text";
    return `<div class="muted">${esc(p.label)}<input type="${inputType}" ${dataAttrs} value="${esc(val)}" /></div>`;
  }).join("");
}

function renderItemEditor(item, schema) {
  const typeSelect = `<select data-ef-type="0">${Object.keys(schema).map((t) => `<option value="${esc(t)}">${esc(schema[t].name || t)}</option>`).join("")}</select>`;
  const effects = (item.effects || []).map((ef, i) => `
    <div class="card" style="margin-top:8px">
      <div class="muted">效果 ${i + 1}
        <select data-ef-type="${i}">${Object.keys(schema).map((t) => `<option value="${esc(t)}" ${t === ef.type ? "selected" : ""}>${esc(schema[t].name || t)}</option>`).join("")}</select>
      </div>
      ${effectParamInputs(ef, schema, i)}
      <button class="tab" data-remove-ef="${i}">删除效果</button>
    </div>`).join("");
  const shopChecks = ["daily","weekly","black","event"].map((s) =>
    `<label class="muted" style="margin-right:10px"><input type="checkbox" class="it_shop" value="${s}" ${(item.shops||[]).includes(s) ? "checked" : ""}/> ${SHOP[s]}</label>`).join("");
  return `
    <div class="card" id="editor">
      <div class="row">
        <div class="col muted">道具ID<input id="it_id" value="${esc(item.id || "")}" /></div>
        <div class="col muted">名称<input id="it_name" value="${esc(item.name || "")}" /></div>
      </div>
      <div class="row">
        <div class="col muted">类别<select id="it_category">${opts(["resource","consume","buff","gift","functional","equipment"], item.category || "resource", (v)=>lbl(ITEM_CAT,v))}</select></div>
        <div class="col muted">品质<select id="it_rarity">${opts(["ssr","sr","r","n"], item.rarity || "n", (v)=>lbl(RARITY,v))}</select></div>
      </div>
      <div class="row">
        <div class="col muted">价格货币<select id="it_currency">${opts(["gold","diamond","merit","soul","repute","event_ticket","challenge"], (item.price||{}).currency || "gold", (v)=>lbl(CURRENCY,v))}</select></div>
        <div class="col muted">价格数量<input id="it_price" type="number" value="${esc((item.price || {}).amount || 0)}" /></div>
      </div>
      <div class="muted">上架商店：${shopChecks}</div>
      <div class="muted">描述<input id="it_desc" value="${esc(item.desc || "")}" /></div>
      <div style="margin-top:12px"><b>效果</b> <button class="tab" id="addEff">+ 添加效果</button></div>
      <div id="effects">${effects}</div>
      <button class="primary" id="saveItem">保存道具</button>
      <button class="tab" id="cancelItem">取消</button>
      <div id="saveResult" class="muted"></div>
    </div>`;
}

function collectItem(root) {
  const shops = [];
  root.querySelectorAll(".it_shop").forEach((c) => { if (c.checked) shops.push(c.value); });
  const item = {
    id: root.querySelector("#it_id").value.trim(),
    name: root.querySelector("#it_name").value.trim(),
    category: root.querySelector("#it_category").value,
    rarity: root.querySelector("#it_rarity").value,
    desc: root.querySelector("#it_desc").value,
    price: {
      currency: root.querySelector("#it_currency").value,
      amount: parseInt(root.querySelector("#it_price").value || "0", 10),
    },
    shops,
    usable: true,
    target: "self",
    effects: [],
  };
  const groups = {};
  root.querySelectorAll("#effects .card").forEach((card, i) => {
    const typeSel = card.querySelector("[data-ef-type]");
    groups[i] = { type: typeSel ? typeSel.value : "", params: {} };
  });
  root.querySelectorAll("#effects [data-ef]").forEach((el) => {
    const i = parseInt(el.dataset.ef, 10);
    const key = el.dataset.key;
    if (!groups[i]) return;
    let v = el.value;
    const schema = itemSchema || {};
    const t = groups[i].type;
    const pdef = ((schema[t] || {}).params || []).find((p) => p.key === key) || {};
    if (pdef.type === "int") v = parseInt(v || "0", 10);
    else if (pdef.type === "float") v = parseFloat(v || "0");
    else if (pdef.type === "loot_table" || pdef.type === "choice_list") {
      try { v = JSON.parse(v || "[]"); } catch (e) { v = []; }
    }
    groups[i].params[key] = v;
  });
  Object.keys(groups).forEach((i) => item.effects.push(groups[i]));
  return item;
}

async function renderItems() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const schema = await ensureSchema();
  const data = await api("admin/items");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const rows = (data.items || []).map((it, i) => `
    <tr>
      <td>${esc(it.name)}${techId(it.id)}</td>
      <td>${esc(lbl(ITEM_CAT, it.category))}</td>
      <td>${(it.effects || []).map((e) => esc((schema[e.type] && schema[e.type].name) || e.type)).join("、")}</td>
      <td><button class="tab" data-edit="${i}">编辑</button>
          <button class="tab" data-del="${esc(it.id)}">删除</button></td>
    </tr>`).join("");
  view.innerHTML = `
    <div class="row">
      <button class="primary" id="newItem">+ 新建道具</button>
      <label class="muted" style="margin-left:12px"><input type="checkbox" id="itemTech" ${showTech ? "checked" : ""}/> 显示技术字段(ID)</label>
    </div>
    <table><thead><tr><th>道具</th><th>类别</th><th>效果</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table>
    <div id="editorHost" style="margin-top:16px"></div>`;

  const items = data.items || [];
  let current = { effects: [] };
  function openEditor(item) {
    current = JSON.parse(JSON.stringify(item || { effects: [] }));
    const host = document.getElementById("editorHost");
    host.innerHTML = renderItemEditor(current, schema);
    host.querySelector("#cancelItem").addEventListener("click", () => {
      document.getElementById("editorHost").innerHTML = "";
    });
    host.querySelector("#addEff").addEventListener("click", () => {
      current = collectItem(host);
      current.effects.push({ type: Object.keys(schema)[0] || "", params: {} });
      openEditor(current);
    });
    host.querySelectorAll("[data-remove-ef]").forEach((b) => b.addEventListener("click", () => {
      current = collectItem(host);
      current.effects.splice(parseInt(b.dataset.removeEf, 10), 1);
      openEditor(current);
    }));
    host.querySelectorAll("[data-ef-type]").forEach((sel) => sel.addEventListener("change", () => {
      current = collectItem(host);
      const i = parseInt(sel.dataset.efType, 10);
      current.effects[i] = { type: sel.value, params: {} };
      openEditor(current);
    }));
    host.querySelector("#saveItem").addEventListener("click", async () => {
      const item = collectItem(host);
      try {
        await post("admin/items", item);
        document.getElementById("saveResult").textContent = "✅ 已保存道具 " + item.id;
        setTimeout(renderItems, 600);
      } catch (e) {
        document.getElementById("saveResult").textContent = "保存失败：" + (e.message || e);
      }
    });
  }
  document.getElementById("newItem").addEventListener("click", () => openEditor({ effects: [] }));
  document.getElementById("itemTech").addEventListener("change", (e) => { showTech = e.target.checked; renderItems(); });
  view.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openEditor(items[parseInt(b.dataset.edit, 10)])));
  view.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除道具「" + b.dataset.del + "」？")) return;
    try { await post("admin/items/delete", { id: b.dataset.del }); renderItems(); } catch (e) { /* ignore */ }
  }));
}

// ---------------- 技能工坊 ----------------
const SKILL_TYPES = ["active", "passive", "command", "assault", "formation"];
const SKILL_CATS = ["damage", "control", "buff", "debuff", "heal", "special"];
const SKILL_TARGETS = ["self", "ally_single", "ally_all", "lowest_hp_ally",
  "enemy_single", "enemy_all", "lowest_hp_enemy", "random_enemy"];
const SKILL_TRIGGERS = ["attack", "when_attacked", "round_start", "on_kill", "hp_below", "always"];
const EFFECT_TYPES = ["dmg_physical", "dmg_magic", "dmg_true", "heal", "regen", "buff",
  "debuff", "dot", "control", "shield", "cleanse", "dispel", "revive", "execute",
  "invulnerable", "untargetable", "combo", "pursuit", "counter", "summon"];
const SKILL_ATTRS = ["force", "intellect", "vitality", "charisma", "eloquence", "speed"];

const SKILL_TYPE_LABEL = { active: "主动", passive: "被动", command: "指挥", assault: "突击", formation: "阵法" };
const SKILL_CAT_LABEL = { damage: "伤害", control: "控制", buff: "增益", debuff: "减益", heal: "治疗", special: "特殊" };
const TARGET_LABEL = { self: "自身", ally_single: "己方单体", ally_all: "己方全体", lowest_hp_ally: "己方残血",
  enemy_single: "敌方单体", enemy_all: "敌方全体", lowest_hp_enemy: "敌方残血", random_enemy: "随机敌人" };
const TRIGGER_LABEL = { attack: "攻击时", when_attacked: "受击时", round_start: "回合开始", on_kill: "击杀时", hp_below: "残血时", always: "常驻" };
const EFFECT_TYPE_LABEL = { dmg_physical: "兵刃伤害", dmg_magic: "谋略伤害", dmg_true: "真实伤害",
  heal: "治疗", regen: "持续回复", buff: "增益", debuff: "减益", dot: "持续伤害", control: "控制",
  shield: "护盾", cleanse: "净化", dispel: "驱散增益", revive: "复活", execute: "斩杀",
  invulnerable: "无敌", untargetable: "不可选中", combo: "连击", pursuit: "追击", counter: "反击", summon: "召唤" };
const ATTR_LABEL = { force: "武力", intellect: "智力", vitality: "体力", charisma: "魅力", eloquence: "口才", speed: "速度" };
const EFFECT_OPTION_LABELS = { atk: "攻击", def: "防御", mag_def: "法防", speed: "速度", atkspeed: "攻速",
  crit: "暴击", crit_dmg: "暴伤", dodge: "闪避", lifesteal: "吸血", spellvamp: "法术吸血",
  shield: "护盾", reflect: "反伤", tenacity: "韧性", cdr: "冷却缩减", reduction: "免伤", armor: "护甲",
  shred_def: "破甲", shred_mag: "破魔", weaken: "虚弱", grievous: "重伤", mark: "标记",
  poison: "中毒", burn: "灼烧", bleed: "流血",
  stun: "眩晕", knockup: "击飞", knockback: "击退", frozen: "冻结", silence: "沉默",
  taunt: "嘲讽", disarm: "缴械", fear: "恐惧", blind: "致盲", charm: "魅惑", suppress: "压制", slow: "减速" };

let skillLibrary = null;

async function ensureSkillLibrary() {
  if (skillLibrary) return skillLibrary;
  const d = await api("admin/skill-effects");
  skillLibrary = d.__error ? { effects: [] } : d;
  return skillLibrary;
}

function scaleAttr(s) {
  const sc = (s && s.scale) || {};
  if (sc.attrs && Object.keys(sc.attrs).length) return Object.keys(sc.attrs)[0];
  return sc.attr || "force";
}
function scaleCoef(s) {
  const sc = (s && s.scale) || {};
  if (sc.attrs && Object.keys(sc.attrs).length) return sc.attrs[Object.keys(sc.attrs)[0]];
  return sc.coef != null ? sc.coef : 1.0;
}

function skillEffectParamInputs(ef, i) {
  const ps = (skillLibrary && skillLibrary.param_schema && skillLibrary.param_schema[ef.type]) || { params: [] };
  const params = ef.params || {};
  if (!(ps.params || []).length) {
    return `<div class="muted" style="font-size:12px;opacity:.7">该效果无需参数</div>`;
  }
  return (ps.params || []).map((p) => {
    const val = params[p.key] != null ? params[p.key] : (p.default != null ? p.default : "");
    const attrs = `data-skef="${i}" data-key="${p.key}" data-ptype="${p.type}"`;
    if (p.type === "enum") {
      const o = (p.options || []).map((v) =>
        `<option value="${esc(v)}" ${String(val) === String(v) ? "selected" : ""}>${esc(EFFECT_OPTION_LABELS[v] || v)}</option>`).join("");
      return `<div class="col muted">${esc(p.label)}<select ${attrs}>${o}</select></div>`;
    }
    const it = (p.type === "int" || p.type === "float") ? "number" : "text";
    const extra = p.type === "float" ? ` step="0.05"` : "";
    return `<div class="col muted">${esc(p.label)}<input type="${it}"${extra} ${attrs} value="${esc(val)}" /></div>`;
  }).join("");
}

function buildEffectParams(card) {
  const params = {};
  card.querySelectorAll("[data-skef]").forEach((el) => {
    const key = el.dataset.key;
    const pt = el.dataset.ptype;
    let v = el.value;
    if (pt === "int") v = parseInt(v || "0", 10);
    else if (pt === "float") v = parseFloat(v || "0");
    params[key] = v;
  });
  return params;
}

function renderSkillEffectRow(ef, i) {
  const typeSel = opts(EFFECT_TYPES, ef.type || "dmg_physical", (v) => lbl(EFFECT_TYPE_LABEL, v));
  const jsonText = esc(JSON.stringify(ef.params || {}));
  return `
    <div class="card" style="margin-top:6px">
      <div class="muted">效果 ${i + 1}
        <select class="sk_ef_type" data-i="${i}">${typeSel}</select>
        <button class="tab" data-del-ef="${i}">删除</button>
      </div>
      <div class="row">${skillEffectParamInputs(ef, i)}</div>
      <details class="muted" style="margin-top:6px"><summary>高级(JSON，可手改覆盖)</summary>
        <textarea class="sk_ef_json" data-i="${i}" rows="2">${jsonText}</textarea></details>
    </div>`;
}

function attachSkillParamSync(host) {
  host.querySelectorAll("#sk_effects .card").forEach((card) => {
    card.querySelectorAll("[data-skef]").forEach((el) => el.addEventListener("input", () => {
      const jt = card.querySelector(".sk_ef_json");
      if (jt) jt.value = JSON.stringify(buildEffectParams(card));
    }));
  });
}

function renderSkillEditor(s, lib) {
  s = s || { effects: [{}], type: "active", category: "damage", target: "enemy_single",
             trigger: "attack", chance: 0.35, cooldown: 0, scale: { attr: "force" }, book_cost: 40 };
  const tplOptions = `<option value="">（选择效果模板）</option>` +
    (lib.effects || []).map((e) => `<option value="${esc(e.name)}">${esc(e.name)}·${esc(lbl(SKILL_CAT_LABEL, e.category))}</option>`).join("");
  return `
    <div class="card" id="skillEditor">
      <div class="row">
        <div class="col muted">技能名<input id="sk_name" value="${esc(s.name || "")}" /></div>
        <div class="col muted">类型<select id="sk_type">${opts(SKILL_TYPES, s.type, (v)=>lbl(SKILL_TYPE_LABEL,v))}</select></div>
        <div class="col muted">类别<select id="sk_category">${opts(SKILL_CATS, s.category, (v)=>lbl(SKILL_CAT_LABEL,v))}</select></div>
      </div>
      <div class="row">
        <div class="col muted">目标<select id="sk_target">${opts(SKILL_TARGETS, s.target, (v)=>lbl(TARGET_LABEL,v))}</select></div>
        <div class="col muted">触发<select id="sk_trigger">${opts(SKILL_TRIGGERS, s.trigger, (v)=>lbl(TRIGGER_LABEL,v))}</select></div>
      </div>
      <div class="row">
        <div class="col muted">发动概率<input id="sk_chance" type="number" step="0.05" value="${esc(s.chance != null ? s.chance : 0.35)}" /></div>
        <div class="col muted">冷却(回合)<input id="sk_cd" type="number" value="${esc(s.cooldown || 0)}" /></div>
        <div class="col muted">技能书碎片价<input id="sk_cost" type="number" value="${esc(s.book_cost || 40)}" /></div>
      </div>
      <div class="muted" style="margin-top:4px"><b>战斗属性与公式</b></div>
      <div class="row">
        <div class="col muted">基础值<input id="sk_base" type="number" value="${esc((s.formula || {}).base || 0)}" /></div>
        <div class="col muted">法力消耗<input id="sk_mana" type="number" value="${esc((s.formula || {}).mana_cost || 30)}" /></div>
        <div class="col muted">固定穿透<input id="sk_penf" type="number" value="${esc((s.formula || {}).pen_flat || 0)}" /></div>
        <div class="col muted">百分比穿透<input id="sk_penpct" type="number" step="0.05" value="${esc((s.formula || {}).pen_pct || 0)}" /></div>
      </div>
      <div class="row">
        <div class="col muted">缩放属性<select id="sk_scale_attr">${opts(SKILL_ATTRS, scaleAttr(s), (v)=>lbl(ATTR_LABEL,v))}</select></div>
        <div class="col muted">缩放系数<input id="sk_scale_coef" type="number" step="0.1" value="${esc(scaleCoef(s))}" /></div>
      </div>
      <div class="row">
        <div class="col muted">描述<input id="sk_desc" value="${esc(s.desc || "")}" /></div>
        <div class="col muted">效果模板<select id="sk_tpl">${tplOptions}</select></div>
      </div>
      <div style="margin-top:10px"><b>效果</b> <button class="tab" id="sk_add_ef">+ 添加效果</button></div>
      <div id="sk_effects">${(s.effects || []).map((ef, i) => renderSkillEffectRow(ef, i)).join("")}</div>
      <button class="primary" id="sk_save">保存技能</button>
      <button class="tab" id="sk_cancel">取消</button>
      <div id="sk_msg" class="muted"></div>
    </div>`;
}

function collectSkill(root) {
  const effects = [];
  root.querySelectorAll("#sk_effects .card").forEach((card) => {
    const t = card.querySelector(".sk_ef_type").value;
    let params = buildEffectParams(card);
    const jt = card.querySelector(".sk_ef_json");
    if (jt) {
      const raw = jt.value.trim();
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object" && JSON.stringify(parsed) !== JSON.stringify(params)) {
            params = parsed;
          }
        } catch (e) { /* ignore invalid json */ }
      }
    }
    effects.push({ type: t, params });
  });
  return {
    name: root.querySelector("#sk_name").value.trim(),
    type: root.querySelector("#sk_type").value,
    category: root.querySelector("#sk_category").value,
    target: root.querySelector("#sk_target").value,
    trigger: root.querySelector("#sk_trigger").value,
    chance: parseFloat(root.querySelector("#sk_chance").value || "0.35"),
    cooldown: parseInt(root.querySelector("#sk_cd").value || "0", 10),
    book_cost: parseInt(root.querySelector("#sk_cost").value || "40", 10),
    scale: { attrs: { [root.querySelector("#sk_scale_attr").value]: parseFloat(root.querySelector("#sk_scale_coef").value || "1") } },
    formula: {
      base: parseFloat(root.querySelector("#sk_base").value || "0"),
      mana_cost: parseInt(root.querySelector("#sk_mana").value || "30", 10),
      pen_flat: parseFloat(root.querySelector("#sk_penf").value || "0"),
      pen_pct: parseFloat(root.querySelector("#sk_penpct").value || "0"),
    },
    desc: root.querySelector("#sk_desc").value,
    effects,
  };
}

async function renderSkills() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const lib = await ensureSkillLibrary();
  const data = await api("admin/skills");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const all = data.skills || [];
  const custom = data.custom || [];
  const rows = all.slice(0, 60).map((s) => `
    <tr><td>${esc(s.name)}</td><td>${esc(lbl(SKILL_TYPE_LABEL, s.type))}</td><td>${esc(lbl(SKILL_CAT_LABEL, s.category))}</td>
        <td>${s.cost}</td><td>${s.source === "custom" ? "自定义" : "内置"}</td></tr>`).join("");
  const customRows = custom.map((s) => `
    <tr><td>${esc(s.name)}</td><td>${esc(lbl(SKILL_TYPE_LABEL, s.type))}</td><td>${esc(lbl(SKILL_CAT_LABEL, s.category))}</td>
        <td><button class="tab" data-edit-skill="${esc(s.name)}">编辑</button>
            <button class="tab" data-del-skill="${esc(s.name)}">删除</button></td></tr>`).join("");
  view.innerHTML = `
    <div class="muted">技能效果库：${(lib.effects || []).length} 个模板；内置技能 ${all.length - custom.length} 项，自定义 ${custom.length} 项。</div>
    <button class="primary" id="newSkill">+ 新建技能</button>
    <div class="muted" style="margin-top:10px">自定义技能</div>
    <table><thead><tr><th>技能</th><th>类型</th><th>类别</th><th>操作</th></tr></thead><tbody>${customRows || '<tr><td colspan="4" class="muted">暂无</td></tr>'}</tbody></table>
    <div class="muted" style="margin-top:10px">全部技能（部分展示，只读）</div>
    <table><thead><tr><th>技能</th><th>类型</th><th>类别</th><th>碎片价</th><th>来源</th></tr></thead><tbody>${rows}</tbody></table>
    <div id="skillHost" style="margin-top:16px"></div>`;

  function openEditor(s) {
    const host = document.getElementById("skillHost");
    host.innerHTML = renderSkillEditor(s, lib);
    attachSkillParamSync(host);
    host.querySelector("#sk_cancel").addEventListener("click", () => {
      document.getElementById("skillHost").innerHTML = "";
    });
    host.querySelector("#sk_add_ef").addEventListener("click", () => {
      const cur = collectSkill(host); cur.effects.push({ type: "dmg_physical", params: { coef: 1.0, hits: 1 } });
      openEditor(cur);
    });
    host.querySelectorAll("[data-del-ef]").forEach((b) => b.addEventListener("click", () => {
      const cur = collectSkill(host); cur.effects.splice(parseInt(b.dataset.delEf, 10), 1); openEditor(cur);
    }));
    host.querySelector("#sk_tpl").addEventListener("change", (e) => {
      const t = (lib.effects || []).find((x) => x.name === e.target.value);
      if (!t) return;
      const cur = collectSkill(host);
      cur.category = t.category; cur.target = t.target; cur.trigger = t.trigger;
      cur.chance = t.chance; cur.cooldown = t.cooldown; cur.scale = t.scale || cur.scale;
      cur.effects = JSON.parse(JSON.stringify(t.effects || []));
      cur.desc = cur.desc || t.desc;
      openEditor(cur);
    });
    host.querySelector("#sk_save").addEventListener("click", async () => {
      const sk = collectSkill(host);
      try {
        await post("admin/skills", sk);
        document.getElementById("sk_msg").textContent = "✅ 已保存技能 " + sk.name;
        setTimeout(renderSkills, 600);
      } catch (e) {
        document.getElementById("sk_msg").textContent = "保存失败：" + (e.message || e);
      }
    });
  }

  document.getElementById("newSkill").addEventListener("click", () => openEditor(null));
  view.querySelectorAll("[data-edit-skill]").forEach((b) => b.addEventListener("click", () => {
    openEditor(custom.find((s) => s.name === b.dataset.editSkill));
  }));
  view.querySelectorAll("[data-del-skill]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除自定义技能「" + b.dataset.delSkill + "」？")) return;
    try { await post("admin/skills/delete", { name: b.dataset.delSkill }); renderSkills(); } catch (e) { /* ignore */ }
  }));
}

// ---------------- 广播 ----------------
async function renderBroadcast() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const info = await api("admin/broadcast");
  const s = (info && info.sessions) || { total: 0, group: 0, friend: 0 };
  const disabled = !!(info && info.disabled);
  if (disabled) {
    view.innerHTML = `
      <div class="card" style="border:1px solid #e5484d">
        <div class="muted" style="color:#e5484d"><b>⛔ 广播推送已临时禁用</b></div>
        <div class="muted" style="margin-top:6px">如需开启，请在插件配置中将 <b>system.enable_broadcast</b> 设为开启后重载插件。</div>
        <div class="muted" style="margin-top:6px">已记录会话：共 ${s.total}（群 ${s.group} / 私 ${s.friend}）。</div>
      </div>`;
    return;
  }
  view.innerHTML = `
    <div class="col">
      <label class="muted">广播目标</label>
      <select id="bcTarget">
        <option value="group" selected>群聊（默认）</option>
        <option value="private">私聊</option>
        <option value="all">全部会话</option>
      </select>
      <div class="muted" style="margin:6px 0">已记录会话：共 ${s.total}（群 ${s.group} / 私 ${s.friend}）。仅广播「已记录」的会话；若目标群无记录，请先在该群发送一次指令（如 /帮助）。</div>
      <label class="muted">广播内容</label>
      <textarea id="bcText" rows="4" placeholder="输入要推送到目标群聊的公告…"></textarea>
      <button class="primary" id="bcSend">发送广播</button>
      <div id="bcResult" class="muted" style="margin-top:10px"></div>
    </div>`;
  document.getElementById("bcSend").addEventListener("click", async () => {
    const text = document.getElementById("bcText").value.trim();
    if (!text) return;
    const target = document.getElementById("bcTarget").value;
    try {
      const res = await post("admin/broadcast", { text, target });
      let line = `成功 ${res.sent} / 失败 ${res.failed} / 跳过 ${res.skipped}（目标会话 ${res.total}）`;
      if (res.hint) line += `\n提示：${res.hint}`;
      if (res.errors && res.errors.length) line += `\n错误：${res.errors.join("；")}`;
      document.getElementById("bcResult").textContent = line;
    } catch (e) {
      document.getElementById("bcResult").textContent = "发送失败：" + (e.message || e);
    }
  });
}

// ---------------- 兵种库 / 兵种效果库 ----------------
const STAT_ATTRS = Object.keys(STAT_ATTR_LABEL);
const ITEM_TYPE_LABEL = { stat: "属性", mechanic: "机制", opening: "开局" };
const OPENING_ATOM_LABEL = { shield: "护盾", buff: "增益", regen: "持续回复", heal: "治疗",
  cleanse: "净化", invulnerable: "无敌", untargetable: "不可选中" };
const OPENING_ATOMS = {
  shield: { label: "护盾", fields: [
    { k: "value", label: "生命比例(0-1)", type: "float", def: 0.2 },
    { k: "rounds", label: "回合", type: "int", def: 2 }] },
  buff: { label: "增益", fields: [
    { k: "attr", label: "属性", type: "enum", opts: STAT_ATTRS, def: "atk", labelMap: STAT_ATTR_LABEL },
    { k: "value", label: "数值(比例)", type: "float", def: 0.15 },
    { k: "rounds", label: "回合", type: "int", def: 2 }] },
  regen: { label: "持续回复", fields: [
    { k: "value", label: "生命比例(0-1)", type: "float", def: 0.06 },
    { k: "rounds", label: "回合", type: "int", def: 3 }] },
  heal: { label: "治疗", fields: [
    { k: "base", label: "基础治疗", type: "int", def: 60 }] },
  cleanse: { label: "净化", fields: [] },
  invulnerable: { label: "无敌", fields: [{ k: "rounds", label: "回合", type: "int", def: 1 }] },
  untargetable: { label: "不可选中", fields: [{ k: "rounds", label: "回合", type: "int", def: 1 }] },
};

function openingFieldsHtml(atom) {
  atom = atom || {};
  const cfg = OPENING_ATOMS[atom.type || "shield"] || { fields: [] };
  const params = atom.params || {};
  if (!(cfg.fields || []).length) {
    return '<div class="muted" style="font-size:12px;opacity:.7">该类型无需参数</div>';
  }
  return (cfg.fields || []).map((f) => {
    const val = params[f.k] != null ? params[f.k] : f.def;
    if (f.type === "enum") {
      return `<div class="col muted">${esc(f.label)}<select class="tr_oatom_f" data-k="${esc(f.k)}" data-pt="enum">${opts(f.opts, val, (v) => lbl(f.labelMap || {}, v))}</select></div>`;
    }
    const step = f.type === "float" ? ' step="0.05"' : "";
    return `<div class="col muted">${esc(f.label)}<input class="tr_oatom_f" data-k="${esc(f.k)}" data-pt="${esc(f.type)}" type="number"${step} value="${esc(val)}" /></div>`;
  }).join("");
}

function openingAtomText(it) {
  const a = (it && it.atom) || {};
  const label = OPENING_ATOM_LABEL[a.type] || a.type || "";
  const p = a.params || {};
  let extra = "";
  if (a.type === "shield" || a.type === "regen") extra = `${Math.round((p.value || 0) * 100)}%/${p.rounds || 1}回合`;
  else if (a.type === "buff") extra = `${lbl(STAT_ATTR_LABEL, p.attr)}+${Math.round((p.value || 0) * 100)}%/${p.rounds || 1}回合`;
  else if (a.type === "heal") extra = `${p.base || 0}`;
  else if (p.rounds) extra = `${p.rounds}回合`;
  return "开局·" + label + (extra ? `（${extra}）` : "");
}

function itemRowHtml(it) {
  it = it || {};
  const t = it.type || "stat";
  if (t === "opening") {
    const atom = it.atom || { type: "shield", params: {} };
    const typeSel = opts(Object.keys(OPENING_ATOMS), atom.type || "shield", (v) => lbl(OPENING_ATOM_LABEL, v));
    return `<div class="row" data-item data-type="opening" style="margin-top:4px;flex-wrap:wrap">
      <div class="col muted">开局类型<select class="tr_oatom">${typeSel}</select></div>
      ${openingFieldsHtml(atom)}
      <div class="col"><button class="tab" data-del-item>删除条目</button></div>
      <details class="muted" style="width:100%"><summary>高级(JSON，可手改覆盖)</summary>
        <textarea class="tr_atom_json" rows="2">${esc(JSON.stringify(atom))}</textarea></details>
    </div>`;
  }
  const isStat = t === "stat";
  const sel = isStat
    ? `<select class="tr_attr">${opts(STAT_ATTRS, it.attr || "def", (v) => lbl(STAT_ATTR_LABEL, v))}</select>`
    : `<select class="tr_key">${opts(Object.keys(MECH_LABEL), it.key || "first_strike", (v) => lbl(MECH_LABEL, v))}</select>`;
  return `<div class="row" data-item data-type="${esc(t)}" style="margin-top:4px">
    <div class="col muted">${isStat ? "属性" : "机制"}${sel}</div>
    <div class="col muted">数值<input class="tr_val" type="number" step="0.05" value="${esc(it.value != null ? it.value : (isStat ? 0.1 : 1))}" /></div>
    <div class="col"><button class="tab" data-del-item>删除条目</button></div></div>`;
}

function effectCardHtml(eff) {
  const items = (eff.items || []).map((it) => itemRowHtml(it)).join("");
  return `<div class="card" data-eff-card style="margin-top:6px">
    <div class="muted">效果名 <input class="tr_eff_name" value="${esc(eff.name || "")}" style="width:160px" />
      <button class="tab" data-del-eff>删除效果</button></div>
    ${items || '<div class="muted">（无条目）</div>'}
    <button class="tab" data-add-item="stat">+属性</button>
    <button class="tab" data-add-item="mechanic">+机制</button>
    <button class="tab" data-add-item="opening">+开局</button>
  </div>`;
}

function collectItems(scope) {
  const items = [];
  scope.querySelectorAll("[data-item]").forEach((row) => {
    const t = row.dataset.type;
    if (t === "opening") {
      const ty = row.querySelector(".tr_oatom") ? row.querySelector(".tr_oatom").value : "shield";
      const params = {};
      row.querySelectorAll(".tr_oatom_f").forEach((el) => {
        let v = el.value;
        if (el.dataset.pt === "int") v = parseInt(v || "0", 10);
        else if (el.dataset.pt === "float") v = parseFloat(v || "0");
        params[el.dataset.k] = v;
      });
      let atom = { type: ty, params };
      const jt = row.querySelector(".tr_atom_json");
      if (jt) {
        const raw = jt.value.trim();
        if (raw) {
          try { const p = JSON.parse(raw); if (p && p.type) atom = p; } catch (e) { /* ignore */ }
        }
      }
      items.push({ type: "opening", atom });
    } else if (t === "stat") {
      items.push({ type: "stat", attr: row.querySelector(".tr_attr").value, value: parseFloat(row.querySelector(".tr_val").value || "0") });
    } else if (t === "mechanic") {
      items.push({ type: "mechanic", key: row.querySelector(".tr_key").value, value: parseFloat(row.querySelector(".tr_val").value || "0") });
    }
  });
  return items;
}

function collectEffects(container) {
  const effects = [];
  container.querySelectorAll("[data-eff-card]").forEach((card) => {
    const items = collectItems(card);
    if (items.length) effects.push({ name: card.querySelector(".tr_eff_name").value.trim() || "效果", items });
  });
  return effects;
}

function renderTroopEditor(lib, t) {
  t = t || { tier: "basic", counter: [], effects: [] };
  const ids = lib.all_ids || [];
  const tiers = lib.tiers || [{ key: "basic" }, { key: "elite" }, { key: "special" }];
  const counters = ids.map((id) =>
    `<label class="muted" style="margin-right:8px"><input type="checkbox" class="tr_cnt" value="${esc(id)}" ${(t.counter || []).includes(id) ? "checked" : ""}> ${esc(TROOP[id] || id)}</label>`).join("");
  const libOpts = `<option value="">（从效果库添加）</option>` +
    (lib.effects_library || []).map((e, i) => `<option value="${i}">${esc(e.name)}·${esc(e.desc || "")}</option>`).join("");
  return `
    <div class="card" id="troopEditor">
      <div class="row">
        <div class="col muted">名称<input id="tr_name" value="${esc(t.name || "")}" /></div>
        <div class="col muted">分级<select id="tr_tier">${opts(tiers.map((x) => x.key), t.tier || "basic", (v) => lbl(TIER, v))}</select></div>
      </div>
      <div class="muted">描述<input id="tr_desc" value="${esc(t.desc || "")}" /></div>
      <div class="muted" style="margin-top:6px"><b>克制兵种</b></div>
      <div class="row" style="flex-wrap:wrap">${counters}</div>
      <div class="muted" style="margin-top:8px"><b>携带效果</b>
        <select id="tr_lib">${libOpts}</select>
        <button class="tab" id="tr_add_eff">+ 空效果</button></div>
      <div id="tr_effects">${(t.effects || []).map((e) => effectCardHtml(e)).join("")}</div>
      <button class="primary" id="tr_save">保存兵种</button>
      <button class="tab" id="tr_cancel">取消</button>
      <div id="tr_msg" class="muted"></div>
    </div>`;
}

function collectTroop(host) {
  const name = host.querySelector("#tr_name").value.trim();
  return {
    id: name,
    name,
    tier: host.querySelector("#tr_tier").value,
    desc: host.querySelector("#tr_desc").value,
    counter: Array.from(host.querySelectorAll(".tr_cnt:checked")).map((c) => c.value),
    effects: collectEffects(host.querySelector("#tr_effects")),
  };
}

function openTroopEditor(lib, t) {
  const host = document.getElementById("troopHost");
  host.innerHTML = renderTroopEditor(lib, t);
  const rerender = (mut) => { const cur = collectTroop(host); mut(cur); openTroopEditor(lib, cur); };
  host.querySelector("#tr_cancel").addEventListener("click", () => { host.innerHTML = ""; });
  host.querySelector("#tr_add_eff").addEventListener("click", () => rerender((c) => c.effects.push({ name: "新效果", items: [{ type: "stat", attr: "def", value: 0.1 }] })));
  host.querySelector("#tr_lib").addEventListener("change", (e) => {
    const i = parseInt(e.target.value, 10);
    if (isNaN(i)) return;
    const src = (lib.effects_library || [])[i];
    if (!src) return;
    rerender((c) => c.effects.push({ name: src.name, items: JSON.parse(JSON.stringify(src.items || [])) }));
  });
  host.querySelectorAll("[data-del-eff]").forEach((b) => {
    const card = b.closest("[data-eff-card]");
    const idx = Array.from(host.querySelectorAll("[data-eff-card]")).indexOf(card);
    b.addEventListener("click", () => rerender((c) => c.effects.splice(idx, 1)));
  });
  host.querySelectorAll("[data-add-item]").forEach((b) => {
    const card = b.closest("[data-eff-card]");
    const idx = Array.from(host.querySelectorAll("[data-eff-card]")).indexOf(card);
    b.addEventListener("click", () => {
      const kind = b.dataset.addItem;
      const it = kind === "opening" ? { type: "opening", atom: { type: "shield", params: { value: 0.2, rounds: 2 } } }
        : kind === "mechanic" ? { type: "mechanic", key: "first_strike", value: 1 }
          : { type: "stat", attr: "def", value: 0.1 };
      rerender((c) => c.effects[idx].items.push(it));
    });
  });
  host.querySelectorAll("[data-del-item]").forEach((b) => {
    const card = b.closest("[data-eff-card]");
    const idx = Array.from(host.querySelectorAll("[data-eff-card]")).indexOf(card);
    const iidx = Array.from(card.querySelectorAll("[data-item]")).indexOf(b.closest("[data-item]"));
    b.addEventListener("click", () => rerender((c) => c.effects[idx].items.splice(iidx, 1)));
  });
  host.querySelectorAll(".tr_oatom").forEach((sel) => {
    const card = sel.closest("[data-eff-card]");
    const idx = Array.from(host.querySelectorAll("[data-eff-card]")).indexOf(card);
    const iidx = Array.from(card.querySelectorAll("[data-item]")).indexOf(sel.closest("[data-item]"));
    sel.addEventListener("change", () => rerender((c) => {
      c.effects[idx].items[iidx] = { type: "opening", atom: { type: sel.value, params: {} } };
    }));
  });
  host.querySelector("#tr_save").addEventListener("click", async () => {
    const t2 = collectTroop(host);
    try {
      await post("admin/troops", t2);
      document.getElementById("tr_msg").textContent = "✅ 已保存兵种 " + t2.name;
      setTimeout(renderTroops, 500);
    } catch (e) {
      document.getElementById("tr_msg").textContent = "保存失败：" + (e.message || e);
    }
  });
}

async function renderTroops() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/troops");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  (data.builtin || []).concat(data.custom || []).forEach((t) => { TROOP[t.id] = t.name; });
  const cnt = (t) => (t.counter || []).map((c) => TROOP[c] || c).join("、") || "-";
  const rowsBuiltin = (data.builtin || []).map((t) => `
    <tr><td>${esc(t.name)}</td><td>${esc(lbl(TIER, t.tier))}</td>
        <td>${esc((t.effects || []).map((e) => e.name).join("、"))}</td><td>${esc(cnt(t))}</td></tr>`).join("");
  const rowsCustom = (data.custom || []).map((t) => `
    <tr><td>${esc(t.name)}</td><td>${esc(lbl(TIER, t.tier))}</td>
        <td>${esc((t.effects || []).map((e) => e.name).join("、"))}</td>
        <td><button class="tab" data-edit-troop="${esc(t.id)}">编辑</button>
            <button class="tab" data-del-troop="${esc(t.id)}">删除</button></td></tr>`).join("");
  view.innerHTML = `
    <div class="muted">内置兵种 ${(data.builtin || []).length} 项（只读，不可修改）；自定义 ${(data.custom || []).length} 项；兵种效果库 ${(data.effects_library || []).length} 项。</div>
    <button class="primary" id="newTroop">+ 新建兵种</button>
    <div class="muted" style="margin-top:10px">自定义兵种（携带效果可自由设置）</div>
    <table><thead><tr><th>兵种</th><th>分级</th><th>携带效果</th><th>操作</th></tr></thead>
      <tbody>${rowsCustom || '<tr><td colspan="4" class="muted">暂无，点击「新建兵种」创建</td></tr>'}</tbody></table>
    <div class="muted" style="margin-top:10px">内置兵种（只读）</div>
    <table><thead><tr><th>兵种</th><th>分级</th><th>携带效果</th><th>克制</th></tr></thead>
      <tbody>${rowsBuiltin}</tbody></table>
    <div id="troopHost" style="margin-top:16px"></div>`;
  document.getElementById("newTroop").addEventListener("click", () => openTroopEditor(data, null));
  view.querySelectorAll("[data-edit-troop]").forEach((b) => b.addEventListener("click", () =>
    openTroopEditor(data, (data.custom || []).find((t) => t.id === b.dataset.editTroop))));
  view.querySelectorAll("[data-del-troop]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除自定义兵种「" + b.dataset.delTroop + "」？")) return;
    try { await post("admin/troops/delete", { id: b.dataset.delTroop }); renderTroops(); } catch (e) { /* ignore */ }
  }));
}

function renderTroopEffectEditor(data, e) {
  e = e || { items: [{ type: "stat", attr: "def", value: 0.1 }] };
  return `
    <div class="card" id="teEditor">
      <div class="row">
        <div class="col muted">效果名<input id="te_name" value="${esc(e.name || "")}" /></div>
      </div>
      <div class="muted">描述<input id="te_desc" value="${esc(e.desc || "")}" /></div>
      <div style="margin-top:8px"><b>效果条目</b>
        <button class="tab" id="te_add_stat">+属性</button>
        <button class="tab" id="te_add_mech">+机制</button>
        <button class="tab" id="te_add_open">+开局</button></div>
      <div id="te_items">${(e.items || []).map((it) => itemRowHtml(it)).join("")}</div>
      <button class="primary" id="te_save">保存效果</button>
      <button class="tab" id="te_cancel">取消</button>
      <div id="te_msg" class="muted"></div>
    </div>`;
}

function collectTroopEffect(host) {
  return {
    name: host.querySelector("#te_name").value.trim(),
    desc: host.querySelector("#te_desc").value,
    items: collectItems(host.querySelector("#te_items")),
  };
}

function openTroopEffectEditor(data, e) {
  const host = document.getElementById("teHost");
  host.innerHTML = renderTroopEffectEditor(data, e);
  const rerender = (mut) => { const cur = collectTroopEffect(host); mut(cur); openTroopEffectEditor(data, cur); };
  host.querySelector("#te_cancel").addEventListener("click", () => { host.innerHTML = ""; });
  host.querySelector("#te_add_stat").addEventListener("click", () => rerender((c) => c.items.push({ type: "stat", attr: "def", value: 0.1 })));
  host.querySelector("#te_add_mech").addEventListener("click", () => rerender((c) => c.items.push({ type: "mechanic", key: "first_strike", value: 1 })));
  host.querySelector("#te_add_open").addEventListener("click", () => rerender((c) => c.items.push({ type: "opening", atom: { type: "shield", params: { value: 0.2, rounds: 2 } } })));
  host.querySelectorAll("[data-del-item]").forEach((b) => {
    const iidx = Array.from(host.querySelectorAll("[data-item]")).indexOf(b.closest("[data-item]"));
    b.addEventListener("click", () => rerender((c) => c.items.splice(iidx, 1)));
  });
  host.querySelectorAll(".tr_oatom").forEach((sel) => {
    const iidx = Array.from(host.querySelectorAll("[data-item]")).indexOf(sel.closest("[data-item]"));
    sel.addEventListener("change", () => rerender((c) => {
      c.items[iidx] = { type: "opening", atom: { type: sel.value, params: {} } };
    }));
  });
  host.querySelector("#te_save").addEventListener("click", async () => {
    const e2 = collectTroopEffect(host);
    try {
      await post("admin/troop-effects", e2);
      document.getElementById("te_msg").textContent = "✅ 已保存效果 " + e2.name;
      setTimeout(renderTroopEffects, 500);
    } catch (err) {
      document.getElementById("te_msg").textContent = "保存失败：" + (err.message || err);
    }
  });
}

async function renderTroopEffects() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/troop-effects");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const fmtItems = (e) => (e.items || []).map((it) =>
    it.type === "stat" ? `${lbl(STAT_ATTR_LABEL, it.attr)}+${it.attr === "pen_flat" || it.attr === "mana" ? it.value : Math.round((it.value || 0) * 100) + "%"}`
      : it.type === "mechanic" ? lbl(MECH_LABEL, it.key) : openingAtomText(it)).join("、");
  const rowsB = (data.builtin || []).map((e) => `
    <tr><td>${esc(e.name)}</td><td>${esc(fmtItems(e))}</td><td>${esc(e.desc || "")}</td></tr>`).join("");
  const rowsC = (data.custom || []).map((e) => `
    <tr><td>${esc(e.name)}</td><td>${esc(fmtItems(e))}</td><td>${esc(e.desc || "")}</td>
        <td><button class="tab" data-edit-te="${esc(e.id)}">编辑</button>
            <button class="tab" data-del-te="${esc(e.id)}">删除</button></td></tr>`).join("");
  view.innerHTML = `
    <div class="muted">内置兵种效果 ${(data.builtin || []).length} 项；自定义 ${(data.custom || []).length} 项。效果名随机化/架空化，供设计兵种时选择。</div>
    <button class="primary" id="newTe">+ 新建效果</button>
    <div class="muted" style="margin-top:10px">自定义效果</div>
    <table><thead><tr><th>名称</th><th>效果</th><th>描述</th><th>操作</th></tr></thead>
      <tbody>${rowsC || '<tr><td colspan="4" class="muted">暂无</td></tr>'}</tbody></table>
    <div class="muted" style="margin-top:10px">内置效果库（只读，100 项）</div>
    <table><thead><tr><th>名称</th><th>效果</th><th>描述</th></tr></thead><tbody>${rowsB}</tbody></table>
    <div id="teHost" style="margin-top:16px"></div>`;
  document.getElementById("newTe").addEventListener("click", () => openTroopEffectEditor(data, null));
  view.querySelectorAll("[data-edit-te]").forEach((b) => b.addEventListener("click", () =>
    openTroopEffectEditor(data, (data.custom || []).find((e) => e.id === b.dataset.editTe))));
  view.querySelectorAll("[data-del-te]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除自定义兵种效果？")) return;
    try { await post("admin/troop-effects/delete", { id: b.dataset.delTe }); renderTroopEffects(); } catch (e) { /* ignore */ }
  }));
}

// ---------------- 军团管理 ----------------
async function renderGuilds() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/guilds");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const rows = (data.guilds || []).map((g) => `
    <tr><td>${esc(g.name)}<div class="muted">${esc(g.id)}</div></td>
      <td>${esc(g.leader_name)}<div class="muted">${esc(g.leader)}</div></td>
      <td>${g.members}</td><td>${g.level}</td><td>${g.fund}</td><td>${g.exp}</td>
      <td><button class="tab" data-guild="${esc(g.id)}">管理</button></td></tr>`).join("");
  view.innerHTML = `
    <div class="muted">共 ${(data.guilds || []).length} 个军团</div>
    <table><thead><tr><th>军团</th><th>军团长</th><th>人数</th><th>等级</th><th>资金</th><th>经验</th><th>操作</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="7" class="muted">暂无军团</td></tr>'}</tbody></table>
    <div id="guildHost" style="margin-top:16px"></div>`;
  view.querySelectorAll("[data-guild]").forEach((b) => b.addEventListener("click", () => openGuild(b.dataset.guild)));
}
async function openGuild(gid) {
  const host = document.getElementById("guildHost");
  host.innerHTML = '<div class="loading">加载中…</div>';
  const d = await api("admin/guilds", { gid });
  if (!d || d.__error || !d.ok) { host.innerHTML = '<div class="loading">军团不存在</div>'; return; }
  const g = d.guild;
  const memberRows = (g.members || []).map((m) => `
    <tr><td>${esc(m.name)}<div class="muted">${esc(m.qq)}</div></td>
      <td>${m.role === "leader" ? "军团长" : "成员"}</td>
      <td>${m.role !== "leader" ? `<button class="tab g_kick" data-qq="${esc(m.qq)}">踢出</button>` : ""}
          <button class="tab g_leader" data-qq="${esc(m.qq)}">设为军团长</button></td></tr>`).join("");
  host.innerHTML = `
    <div class="card">
      <div class="muted"><b>${esc(g.name)}</b>（${esc(gid)}）</div>
      <div class="row">
        <div class="col muted">名称<input id="g_name" value="${esc(g.name)}" /></div>
        <div class="col muted">等级<input id="g_level" type="number" value="${esc(g.level)}" /></div>
        <div class="col muted">资金<input id="g_fund" type="number" value="${esc(g.fund)}" /></div>
        <div class="col muted">经验<input id="g_exp" type="number" value="${esc(g.exp)}" /></div>
      </div>
      <button class="primary" id="g_save">保存</button>
      <button class="tab" id="g_dissolve" style="color:#e5484d;border-color:#e5484d">解散军团</button>
      <span class="muted" id="g_msg"></span>
      <div class="muted" style="margin-top:10px"><b>成员（${(g.members || []).length}）</b></div>
      <table><thead><tr><th>成员</th><th>职位</th><th>操作</th></tr></thead>
        <tbody>${memberRows || '<tr><td colspan="3" class="muted">无</td></tr>'}</tbody></table>
    </div>`;
  const msg = (t) => { document.getElementById("g_msg").textContent = t; };
  host.querySelector("#g_save").addEventListener("click", async () => {
    try {
      await post("admin/guilds/action", { action: "rename", gid, name: host.querySelector("#g_name").value.trim() });
      await post("admin/guilds/action", { action: "set", gid,
        level: parseInt(host.querySelector("#g_level").value || "1", 10),
        fund: parseInt(host.querySelector("#g_fund").value || "0", 10),
        exp: parseInt(host.querySelector("#g_exp").value || "0", 10) });
      msg("✅ 已保存");
    } catch (e) { msg("保存失败：" + (e.message || e)); }
  });
  host.querySelector("#g_dissolve").addEventListener("click", async () => {
    if (!confirm("确认解散军团「" + g.name + "」？成员将失去军团归属。")) return;
    try { await post("admin/guilds/action", { action: "dissolve", gid }); renderGuilds(); }
    catch (e) { msg("失败：" + (e.message || e)); }
  });
  host.querySelectorAll(".g_kick").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认踢出该成员？")) return;
    try { await post("admin/guilds/action", { action: "kick", gid, qq: b.dataset.qq }); openGuild(gid); } catch (e) { /* ignore */ }
  }));
  host.querySelectorAll(".g_leader").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认将其设为军团长？")) return;
    try { await post("admin/guilds/action", { action: "leader", gid, qq: b.dataset.qq }); openGuild(gid); } catch (e) { /* ignore */ }
  }));
}

// ---------------- 装备管理 ----------------
let equipDefs = { defs: [], slots: {}, rarities: [] };
async function renderEquipments() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/equipments");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  equipDefs = data;
  const slotLabel = (s) => esc((data.slots || {})[s] || s);
  const rows = (data.defs || []).map((d) => `
    <tr><td>${esc(d.name)}<div class="muted">${esc(d.id)}</div></td>
      <td>${slotLabel(d.slot)}</td><td>${esc(lbl(RARITY, d.rarity))}</td>
      <td>${d.force}/${d.intellect}/${d.lead}</td>
      <td>${d.source === "custom"
        ? `<button class="tab" data-edit-eq="${esc(d.id)}">编辑</button><button class="tab" data-del-eq="${esc(d.id)}">删除</button>`
        : '<span class="muted">内置</span>'}</td></tr>`).join("");
  view.innerHTML = `
    <div class="card">
      <div class="muted"><b>装备库（蓝图）</b>　内置 ${(data.defs || []).filter((d) => d.source !== "custom").length} 项只读，自定义 ${(data.defs || []).filter((d) => d.source === "custom").length} 项。</div>
      <button class="primary" id="newEq">+ 新建装备</button>
      <table><thead><tr><th>装备</th><th>部位</th><th>品质</th><th>武/智/统</th><th>操作</th></tr></thead>
        <tbody>${rows}</tbody></table>
      <div id="eqHost" style="margin-top:12px"></div>
    </div>
    <div class="card">
      <div class="muted"><b>玩家装备</b></div>
      <div class="row">
        <div class="col muted">玩家 QQ<input id="pe_qq" placeholder="输入 QQ 后加载" /></div>
        <div class="col" style="display:flex;align-items:flex-end"><button class="tab" id="pe_load">加载</button></div>
      </div>
      <div id="peHost" class="muted" style="margin-top:8px"></div>
    </div>`;
  view.querySelector("#newEq").addEventListener("click", () => openEquipDef(null));
  view.querySelectorAll("[data-edit-eq]").forEach((b) => b.addEventListener("click", () =>
    openEquipDef((data.defs || []).find((d) => d.id === b.dataset.editEq))));
  view.querySelectorAll("[data-del-eq]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除装备蓝图「" + b.dataset.delEq + "」？")) return;
    try { await post("admin/equipments/delete", { id: b.dataset.delEq }); renderEquipments(); } catch (e) { /* ignore */ }
  }));
  view.querySelector("#pe_load").addEventListener("click", () => loadPlayerEquip(view.querySelector("#pe_qq").value.trim()));

  function openEquipDef(d) {
    const host = document.getElementById("eqHost");
    const slots = data.slots || {};
    d = d || { slot: "weapon", rarity: "n" };
    host.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col muted">ID<input id="eq_id" value="${esc(d.id || "")}" ${d.source === "custom" ? "" : ""} /></div>
          <div class="col muted">名称<input id="eq_name" value="${esc(d.name || "")}" /></div>
          <div class="col muted">部位<select id="eq_slot">${opts(Object.keys(slots), d.slot, (v) => lbl(slots, v))}</select></div>
          <div class="col muted">品质<select id="eq_rarity">${opts(data.rarities || ["ssr","sr","r","n"], d.rarity, (v) => lbl(RARITY, v))}</select></div>
        </div>
        <div class="row">
          <div class="col muted">武力<input id="eq_force" type="number" value="${esc(d.force || 0)}" /></div>
          <div class="col muted">智力<input id="eq_intellect" type="number" value="${esc(d.intellect || 0)}" /></div>
          <div class="col muted">统率<input id="eq_lead" type="number" value="${esc(d.lead || 0)}" /></div>
        </div>
        <button class="primary" id="eq_save">保存</button>
        <button class="tab" id="eq_cancel">取消</button>
        <span class="muted" id="eq_msg"></span>
      </div>`;
    host.querySelector("#eq_cancel").addEventListener("click", () => { host.innerHTML = ""; });
    host.querySelector("#eq_save").addEventListener("click", async () => {
      const body = { id: host.querySelector("#eq_id").value.trim(), name: host.querySelector("#eq_name").value.trim(),
        slot: host.querySelector("#eq_slot").value, rarity: host.querySelector("#eq_rarity").value,
        force: parseInt(host.querySelector("#eq_force").value || "0", 10),
        intellect: parseInt(host.querySelector("#eq_intellect").value || "0", 10),
        lead: parseInt(host.querySelector("#eq_lead").value || "0", 10) };
      try { await post("admin/equipments", body); host.querySelector("#eq_msg").textContent = "✅ 已保存"; setTimeout(renderEquipments, 500); }
      catch (e) { host.querySelector("#eq_msg").textContent = "保存失败：" + (e.message || e); }
    });
  }

  async function loadPlayerEquip(qq) {
    const host = document.getElementById("peHost");
    if (!qq) { host.textContent = "请输入 QQ"; return; }
    host.textContent = "加载中…";
    const d = await api("admin/player-equipment", { qq });
    if (!d || d.__error) { host.textContent = "加载失败"; return; }
    const defOpts = (data.defs || []).map((x) => `<option value="${esc(x.id)}">${esc(x.name)}（${esc(x.id)}）</option>`).join("");
    const rows = (d.equipment || []).map((it) => `
      <tr><td>${esc(it.name)}<div class="muted">${esc(it.uid)}</div></td>
        <td>${esc((data.slots || {})[it.slot] || it.slot)}</td><td>${esc(lbl(RARITY, it.rarity))}</td><td>+${it.level}</td>
        <td>${it.equipped_by ? esc(it.equipped_by) : "-"}</td>
        <td><button class="tab pe_up" data-uid="${esc(it.uid)}">强化+1</button>
            <button class="tab pe_rm" data-uid="${esc(it.uid)}">移除</button></td></tr>`).join("");
    host.innerHTML = `
      <div class="row">
        <div class="col muted">发放装备<select id="pe_give_id">${defOpts}</select></div>
        <div class="col muted">等级<input id="pe_give_lv" type="number" value="1" /></div>
        <div class="col" style="display:flex;align-items:flex-end"><button class="primary" id="pe_give">发放</button></div>
      </div>
      <table><thead><tr><th>装备</th><th>部位</th><th>品质</th><th>等级</th><th>穿戴</th><th>操作</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="6" class="muted">该玩家无装备</td></tr>'}</tbody></table>
      <span class="muted" id="pe_msg"></span>`;
    host.querySelector("#pe_give").addEventListener("click", async () => {
      try { await post("admin/player-equipment", { qq, action: "give", id: host.querySelector("#pe_give_id").value, level: parseInt(host.querySelector("#pe_give_lv").value || "1", 10) }); loadPlayerEquip(qq); }
      catch (e) { host.querySelector("#pe_msg").textContent = "失败：" + (e.message || e); }
    });
    host.querySelectorAll(".pe_up").forEach((b) => b.addEventListener("click", async () => {
      try { await post("admin/player-equipment", { qq, action: "enhance", uid: b.dataset.uid, delta: 1 }); loadPlayerEquip(qq); } catch (e) { /* ignore */ }
    }));
    host.querySelectorAll(".pe_rm").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("确认移除该装备？")) return;
      try { await post("admin/player-equipment", { qq, action: "remove", uid: b.dataset.uid }); loadPlayerEquip(qq); } catch (e) { /* ignore */ }
    }));
  }
}

// ---------------- 拍卖行 ----------------
async function renderAuctions() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/auctions");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const ST = { active: "进行中", sold: "已成交", expired: "流拍", defaulted: "违约", cancelled: "已取消" };
  const rows = (data.listings || []).map((l) => `
    <tr><td>${esc(l.id)}</td><td>${esc(l.summary)}</td>
      <td>${esc(l.seller_name)}<div class="muted">${esc(l.seller)}</div></td>
      <td>${l.mode === "bid" ? `竞拍 起${l.price}${l.current_bid ? " 现" + l.current_bid + "(" + esc(l.current_bidder) + ")" : ""}` : `一口价 ${l.price}`}</td>
      <td>${esc(ST[l.status] || l.status)}</td>
      <td>${l.status === "active" ? `<button class="tab au_cancel" data-id="${esc(l.id)}">强制下架</button>
            <button class="tab au_settle" data-id="${esc(l.id)}">强制结算</button>` : ""}
          <button class="tab au_rm" data-id="${esc(l.id)}">删除</button></td></tr>`).join("");
  view.innerHTML = `
    <div class="muted">共 ${(data.listings || []).length} 条挂单</div>
    <button class="primary" id="au_settle_all">手动结算全部到期挂单</button>
    <table><thead><tr><th>编号</th><th>物品</th><th>卖家</th><th>价格</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="6" class="muted">无</td></tr>'}</tbody></table>
    <div id="au_msg" class="muted"></div>`;
  const msg = (t) => { document.getElementById("au_msg").textContent = t; };
  document.getElementById("au_settle_all").addEventListener("click", async () => {
    try { const r = await post("admin/auctions/action", { action: "settle-all" }); msg("✅ 结算 " + r.count + " 条"); renderAuctions(); }
    catch (e) { msg("失败：" + (e.message || e)); }
  });
  view.querySelectorAll(".au_cancel").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("强制下架并返还卖家？")) return;
    try { await post("admin/auctions/action", { action: "cancel", id: b.dataset.id }); renderAuctions(); } catch (e) { /* ignore */ }
  }));
  view.querySelectorAll(".au_settle").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("强制结算该挂单？")) return;
    try { await post("admin/auctions/action", { action: "settle", id: b.dataset.id }); renderAuctions(); } catch (e) { /* ignore */ }
  }));
  view.querySelectorAll(".au_rm").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("删除该挂单（进行中将返还卖家）？")) return;
    try { await post("admin/auctions/action", { action: "remove", id: b.dataset.id }); renderAuctions(); } catch (e) { /* ignore */ }
  }));
}

// ---------------- 活动管理 ----------------
async function renderEvents() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/events");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const bl = data.buff_types || {};
  const defRows = (data.defs || []).map((e) => `
    <tr><td>${esc(e.name)}<div class="muted">${esc(e.id)}</div></td>
      <td>${esc(lbl(bl, e.buff_type))}</td><td>${e.duration}s</td>
      <td>${e.source === "custom"
        ? `<button class="tab" data-edit-ev="${esc(e.id)}">编辑</button><button class="tab" data-del-ev="${esc(e.id)}">删除</button>`
        : '<span class="muted">内置</span>'}</td></tr>`).join("");
  const activeRows = (data.active || []).map((e) => `
    <tr><td>${esc(e.name)}</td><td>${esc(lbl(bl, e.buff_type))}</td><td>${esc(fmtTs(e.end_ts))}</td>
      <td><button class="tab ev_close" data-id="${esc(e.id)}">关闭</button></td></tr>`).join("");
  view.innerHTML = `
    <div class="card">
      <div class="muted">活动全局启用：<b>${data.enabled ? "开启" : "关闭"}</b>
        <button class="tab" id="ev_toggle">${data.enabled ? "关闭活动系统" : "开启活动系统"}</button></div>
    </div>
    <div class="card">
      <div class="muted"><b>活动定义</b></div>
      <button class="primary" id="newEv">+ 新建活动</button>
      <table><thead><tr><th>活动</th><th>效果</th><th>时长</th><th>操作</th></tr></thead><tbody>${defRows}</tbody></table>
      <div id="evHost" style="margin-top:12px"></div>
    </div>
    <div class="card">
      <div class="muted"><b>开启活动</b></div>
      <div class="row">
        <div class="col muted">选择活动<select id="ev_open_id">${(data.defs || []).map((e) => `<option value="${esc(e.id)}">${esc(e.name)}</option>`).join("")}</select></div>
        <div class="col muted">时长(秒，0=默认)<input id="ev_open_dur" type="number" value="0" /></div>
        <div class="col" style="display:flex;align-items:flex-end"><button class="primary" id="ev_open">开启</button></div>
      </div>
      <div class="muted" style="margin-top:10px"><b>进行中</b></div>
      <table><thead><tr><th>活动</th><th>效果</th><th>结束时间</th><th>操作</th></tr></thead>
        <tbody>${activeRows || '<tr><td colspan="4" class="muted">无</td></tr>'}</tbody></table>
      <span class="muted" id="ev_msg"></span>
    </div>`;
  const msg = (t) => { document.getElementById("ev_msg").textContent = t; };
  document.getElementById("ev_toggle").addEventListener("click", async () => {
    try { await post("admin/events/action", { action: "enable", enabled: !data.enabled }); renderEvents(); } catch (e) { /* ignore */ }
  });
  document.getElementById("ev_open").addEventListener("click", async () => {
    const dur = parseInt(document.getElementById("ev_open_dur").value || "0", 10);
    try { await post("admin/events/action", { action: "open", id: document.getElementById("ev_open_id").value, duration: dur > 0 ? dur : null }); renderEvents(); }
    catch (e) { msg("失败：" + (e.message || e)); }
  });
  view.querySelectorAll(".ev_close").forEach((b) => b.addEventListener("click", async () => {
    try { await post("admin/events/action", { action: "close", id: b.dataset.id }); renderEvents(); } catch (e) { /* ignore */ }
  }));
  function openEventDef(e) {
    const host = document.getElementById("evHost");
    e = e || { buff_type: "double_gold", duration: 7200 };
    host.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col muted">ID<input id="ev_id" value="${esc(e.id || "")}" /></div>
          <div class="col muted">名称<input id="ev_name" value="${esc(e.name || "")}" /></div>
          <div class="col muted">效果类型<select id="ev_buff">${opts(Object.keys(bl), e.buff_type, (v) => lbl(bl, v))}</select></div>
          <div class="col muted">时长(秒)<input id="ev_dur" type="number" value="${esc(e.duration || 7200)}" /></div>
        </div>
        <div class="muted">描述<input id="ev_desc" value="${esc(e.desc || "")}" /></div>
        <button class="primary" id="ev_save">保存</button>
        <button class="tab" id="ev_cancel">取消</button>
        <span class="muted" id="evd_msg"></span>
      </div>`;
    host.querySelector("#ev_cancel").addEventListener("click", () => { host.innerHTML = ""; });
    host.querySelector("#ev_save").addEventListener("click", async () => {
      const body = { id: host.querySelector("#ev_id").value.trim(), name: host.querySelector("#ev_name").value.trim(),
        buff_type: host.querySelector("#ev_buff").value, duration: parseInt(host.querySelector("#ev_dur").value || "7200", 10),
        desc: host.querySelector("#ev_desc").value };
      try { await post("admin/events/defs", body); host.querySelector("#evd_msg").textContent = "✅ 已保存"; setTimeout(renderEvents, 500); }
      catch (err) { host.querySelector("#evd_msg").textContent = "保存失败：" + (err.message || err); }
    });
  }
  document.getElementById("newEv").addEventListener("click", () => openEventDef(null));
  view.querySelectorAll("[data-edit-ev]").forEach((b) => b.addEventListener("click", () =>
    openEventDef((data.defs || []).find((e) => e.id === b.dataset.editEv))));
  view.querySelectorAll("[data-del-ev]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除活动定义？")) return;
    try { await post("admin/events/defs/delete", { id: b.dataset.delEv }); renderEvents(); } catch (e) { /* ignore */ }
  }));
}

// ---------------- 定时任务 ----------------
function jobActionParamInputs(field, params, options) {
  const val = params[field.key] != null ? params[field.key] : (field.default != null ? field.default : "");
  const attrs = `data-jp="${esc(field.key)}" data-jpt="${esc(field.type)}"`;
  if (field.type === "enum") {
    let src = [];
    if (field.source && options) {
      src = (options[field.source] || []).map((o) => ({ value: o.id, label: o.name }));
    } else if (Array.isArray(field.options)) {
      src = field.options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
    }
    const defaultOpt = field.default != null ? field.default : "";
    const list = src.map((o) => `<option value="${esc(o.value)}" ${String(o.value) === String(val) ? "selected" : ""}>${esc(o.label)}</option>`).join("");
    return `<div class="col muted">${esc(field.label)}<select ${attrs}>${defaultOpt === "" ? '<option value="">（默认）</option>' : ""}${list}</select></div>`;
  }
  if (field.type === "json") {
    const txt = typeof val === "string" ? val : JSON.stringify(val || {});
    return `<div class="col muted">${esc(field.label)}<textarea ${attrs} rows="2">${esc(txt)}</textarea></div>`;
  }
  const it = "text";
  return `<div class="col muted">${esc(field.label)}<input type="${it}" ${attrs} value="${esc(val)}" /></div>`;
}
function collectActionParams(host, fields) {
  const params = {};
  (fields || []).forEach((f) => {
    const el = host.querySelector(`[data-jp="${CSS.escape(f.key)}"]`);
    if (!el) return;
    let v = el.value;
    if (f.type === "int") v = parseInt(v || "0", 10);
    else if (f.type === "float") v = parseFloat(v || "0");
    else if (f.type === "json") {
      const raw = (v || "").trim();
      if (!raw) return;
      try { v = JSON.parse(raw); } catch (e) { v = {}; }
    }
    if (v === "" || v == null) return;
    params[f.key] = v;
  });
  return params;
}
async function renderJobs() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/jobs");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const jobs = data.jobs || [];
  const custom = data.custom || [];
  const actions = data.actions || [];
  const options = data.options || {};
  const actLabel = {};
  actions.forEach((a) => { actLabel[a.id] = a.label; });
  const byName = {};
  jobs.forEach((j) => { byName[j.name] = j; });

  const builtinRows = jobs.filter((j) => !String(j.name).startsWith("custom:")).map((j) => `
    <tr><td>${esc(j.label || j.name)}<div class="muted">${esc(j.name)}</div></td>
      <td><input class="jb_interval" data-name="${esc(j.name)}" type="number" value="${esc(j.interval)}" /></td>
      <td>${j.enabled ? "✅ 运行" : "⏸ 暂停"}</td>
      <td>${j.last_run ? esc(fmtTs(j.last_run)) : "-"}</td>
      <td>${j.run_count}</td><td>${j.error_count}</td>
      <td>${j.next_run ? esc(fmtTs(j.next_run)) : "-"}</td>
      <td><button class="tab jb_run" data-name="${esc(j.name)}">立即执行</button>
          <button class="tab jb_iv" data-name="${esc(j.name)}">保存间隔</button>
          <button class="tab jb_toggle" data-name="${esc(j.name)}" data-on="${j.enabled ? 1 : 0}">${j.enabled ? "暂停" : "恢复"}</button></td></tr>`).join("");

  const customRows = custom.map((c) => {
    const rt = byName["custom:" + c.id] || {};
    return `<tr><td>${esc(c.label)}<div class="muted">${esc(c.id)}</div></td>
      <td>${esc(actLabel[c.action] || c.action)}</td><td>${c.interval}s</td>
      <td>${rt.enabled === false ? "⏸ 暂停" : "✅ 运行"}</td>
      <td>${rt.run_count || 0}</td>
      <td><button class="tab cj_run" data-name="custom:${esc(c.id)}">立即执行</button>
          <button class="tab cj_edit" data-id="${esc(c.id)}">编辑</button>
          <button class="tab cj_del" data-id="${esc(c.id)}">删除</button></td></tr>`;
  }).join("");

  view.innerHTML = `
    <div class="card">
      <div class="muted"><b>内置定时任务</b></div>
      <table><thead><tr><th>任务</th><th>间隔(秒)</th><th>状态</th><th>上次运行</th><th>运行次数</th><th>错误数</th><th>下次运行</th><th>操作</th></tr></thead>
        <tbody>${builtinRows}</tbody></table>
    </div>
    <div class="card">
      <div class="muted"><b>自定义定时任务</b>（固定间隔，按秒调度）</div>
      <button class="primary" id="newJob">+ 新建定时任务</button>
      <table><thead><tr><th>名称</th><th>动作</th><th>间隔</th><th>状态</th><th>运行次数</th><th>操作</th></tr></thead>
        <tbody>${customRows || '<tr><td colspan="6" class="muted">暂无自定义任务</td></tr>'}</tbody></table>
      <div id="jobHost" style="margin-top:12px"></div>
    </div>
    <div id="jb_msg" class="muted"></div>`;
  const msg = (t) => { document.getElementById("jb_msg").textContent = t; };

  function openJobEditor(c) {
    const host = document.getElementById("jobHost");
    c = c || { action: "broadcast", interval: 3600, enabled: true, params: {} };
    const actOpts = actions.map((a) => `<option value="${esc(a.id)}" ${a.id === c.action ? "selected" : ""}>${esc(a.label)}</option>`).join("");
    host.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col muted">名称<input id="cj_label" value="${esc(c.label || "")}" /></div>
          <div class="col muted">动作<select id="cj_action">${actOpts}</select></div>
          <div class="col muted">间隔(秒)<input id="cj_interval" type="number" value="${esc(c.interval || 3600)}" /></div>
          <div class="col muted">启用<select id="cj_enabled"><option value="1" ${c.enabled !== false ? "selected" : ""}>是</option><option value="0" ${c.enabled === false ? "selected" : ""}>否</option></select></div>
        </div>
        <div class="muted" style="margin-top:6px">动作参数</div>
        <div class="row" id="cj_params"></div>
        <button class="primary" id="cj_save">保存</button>
        <button class="tab" id="cj_cancel">取消</button>
        <span class="muted" id="cj_msg"></span>
      </div>`;
    const drawParams = (actionId, params) => {
      const act = actions.find((a) => a.id === actionId);
      host.querySelector("#cj_params").innerHTML = (act && act.params || []).map((f) => jobActionParamInputs(f, params || {}, options)).join("") || '<span class="muted">该动作无需参数</span>';
    };
    drawParams(c.action, c.params);
    host.querySelector("#cj_action").addEventListener("change", (e) => drawParams(e.target.value, {}));
    host.querySelector("#cj_cancel").addEventListener("click", () => { host.innerHTML = ""; });
    host.querySelector("#cj_save").addEventListener("click", async () => {
      const actionId = host.querySelector("#cj_action").value;
      const act = actions.find((a) => a.id === actionId);
      const body = { id: c.id, label: host.querySelector("#cj_label").value.trim(),
        action: actionId, interval: parseInt(host.querySelector("#cj_interval").value || "3600", 10),
        enabled: host.querySelector("#cj_enabled").value === "1",
        params: collectActionParams(host, act ? act.params : []) };
      try { await post("admin/jobs/save", body); msg("✅ 已保存"); renderJobs(); }
      catch (e) { host.querySelector("#cj_msg").textContent = "保存失败：" + (e.message || e); }
    });
  }

  document.getElementById("newJob").addEventListener("click", () => openJobEditor(null));
  view.querySelectorAll(".cj_edit").forEach((b) => b.addEventListener("click", () =>
    openJobEditor(custom.find((x) => x.id === b.dataset.id))));
  view.querySelectorAll(".cj_del").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除该自定义定时任务？")) return;
    try { await post("admin/jobs/delete", { id: b.dataset.id }); renderJobs(); } catch (e) { /* ignore */ }
  }));
  view.querySelectorAll(".cj_run").forEach((b) => b.addEventListener("click", async () => {
    try { await post("admin/jobs/action", { action: "run", name: b.dataset.name }); msg("✅ 已执行"); setTimeout(renderJobs, 500); }
    catch (e) { msg("失败：" + (e.message || e)); }
  }));

  view.querySelectorAll(".jb_run").forEach((b) => b.addEventListener("click", async () => {
    try { await post("admin/jobs/action", { action: "run", name: b.dataset.name }); msg("✅ 已执行 " + b.dataset.name); setTimeout(renderJobs, 500); }
    catch (e) { msg("失败：" + (e.message || e)); }
  }));
  view.querySelectorAll(".jb_iv").forEach((b) => b.addEventListener("click", async () => {
    const iv = parseInt(view.querySelector(`.jb_interval[data-name="${CSS.escape(b.dataset.name)}"]`).value || "60", 10);
    try { await post("admin/jobs/action", { action: "interval", name: b.dataset.name, interval: iv }); msg("✅ 已改间隔"); renderJobs(); }
    catch (e) { msg("失败：" + (e.message || e)); }
  }));
  view.querySelectorAll(".jb_toggle").forEach((b) => b.addEventListener("click", async () => {
    const on = b.dataset.on === "1";
    try { await post("admin/jobs/action", { action: on ? "pause" : "resume", name: b.dataset.name }); renderJobs(); }
    catch (e) { /* ignore */ }
  }));
}


// ---------------- 世界BOSS ----------------
async function renderWorldboss() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/worldboss");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const cur = data.current || {};
  const boss = cur.boss || {};
  const statusText = data.active ? `${esc(boss.name || "")} HP ${esc(cur.hp)}/${esc(cur.max_hp)}（结束 ${esc(fmtTs(cur.end_ts))}）` : "未开启";
  const rankRows = (data.ranking || []).map((r, i) => `<tr><td>${i + 1}</td><td>${esc(r.name)}<div class="muted">${esc(r.qq)}</div></td><td>${r.damage}</td><td>${r.count}</td></tr>`).join("");
  const defRows = (data.defs || []).map((b) => `
    <tr><td>${esc(b.name)}<div class="muted">${esc(b.id)}</div></td><td>${b.hp}</td><td>${b.atk}</td><td>${b.def}</td>
      <td>${b.source === "custom"
        ? `<button class="tab" data-edit-boss="${esc(b.id)}">编辑</button><button class="tab" data-del-boss="${esc(b.id)}">删除</button>`
        : '<span class="muted">内置</span>'}</td></tr>`).join("");
  view.innerHTML = `
    <div class="card">
      <div class="muted"><b>当前世界BOSS：</b>${statusText}</div>
      <div class="row" style="margin-top:8px">
        <div class="col muted">选择BOSS<select id="wb_boss">${(data.defs || []).map((b) => `<option value="${esc(b.id)}">${esc(b.name)}</option>`).join("")}</select></div>
        <div class="col muted">时长(秒，0=默认)<input id="wb_dur" type="number" value="0" /></div>
        <div class="col" style="display:flex;align-items:flex-end">
          <button class="primary" id="wb_spawn">开启</button>
          <button class="tab" id="wb_settle">提前结算</button>
          <button class="tab" id="wb_close" style="color:#e5484d;border-color:#e5484d">强制关闭</button>
        </div>
      </div>
      <span class="muted" id="wb_msg"></span>
    </div>
    <div class="card">
      <div class="muted"><b>伤害排行</b></div>
      <table><thead><tr><th>#</th><th>玩家</th><th>伤害</th><th>次数</th></tr></thead>
        <tbody>${rankRows || '<tr><td colspan="4" class="muted">无</td></tr>'}</tbody></table>
    </div>
    <div class="card">
      <div class="muted"><b>BOSS 定义</b>（内置只读，可新建自定义）</div>
      <button class="primary" id="newBoss">+ 新建BOSS</button>
      <table><thead><tr><th>BOSS</th><th>生命</th><th>攻击</th><th>防御</th><th>操作</th></tr></thead><tbody>${defRows}</tbody></table>
      <div id="wbHost" style="margin-top:12px"></div>
    </div>`;
  const msg = (t) => { document.getElementById("wb_msg").textContent = t; };
  document.getElementById("wb_spawn").addEventListener("click", async () => {
    const dur = parseInt(document.getElementById("wb_dur").value || "0", 10);
    try { await post("admin/worldboss/action", { action: "spawn", boss_id: document.getElementById("wb_boss").value, duration: dur > 0 ? dur : null }); renderWorldboss(); }
    catch (e) { msg("失败：" + (e.message || e)); }
  });
  document.getElementById("wb_settle").addEventListener("click", async () => {
    if (!confirm("提前结算并发放奖励？")) return;
    try { await post("admin/worldboss/action", { action: "settle" }); renderWorldboss(); } catch (e) { msg("失败：" + (e.message || e)); }
  });
  document.getElementById("wb_close").addEventListener("click", async () => {
    if (!confirm("强制关闭（不结算）？")) return;
    try { await post("admin/worldboss/action", { action: "close" }); renderWorldboss(); } catch (e) { msg("失败：" + (e.message || e)); }
  });
  function openBossDef(b) {
    const host = document.getElementById("wbHost");
    b = b || { hp: 1000000, atk: 800, def: 300 };
    host.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col muted">ID<input id="wb_id" value="${esc(b.id || "")}" /></div>
          <div class="col muted">名称<input id="wb_name" value="${esc(b.name || "")}" /></div>
        </div>
        <div class="row">
          <div class="col muted">生命<input id="wb_hp" type="number" value="${esc(b.hp || 1000000)}" /></div>
          <div class="col muted">攻击<input id="wb_atk" type="number" value="${esc(b.atk || 0)}" /></div>
          <div class="col muted">防御<input id="wb_def" type="number" value="${esc(b.def || 0)}" /></div>
        </div>
        <button class="primary" id="wb_save">保存</button>
        <button class="tab" id="wb_cancel">取消</button>
        <span class="muted" id="wbd_msg"></span>
      </div>`;
    host.querySelector("#wb_cancel").addEventListener("click", () => { host.innerHTML = ""; });
    host.querySelector("#wb_save").addEventListener("click", async () => {
      const body = { id: host.querySelector("#wb_id").value.trim(), name: host.querySelector("#wb_name").value.trim(),
        hp: parseInt(host.querySelector("#wb_hp").value || "1000000", 10),
        atk: parseInt(host.querySelector("#wb_atk").value || "0", 10),
        def: parseInt(host.querySelector("#wb_def").value || "0", 10) };
      try { await post("admin/worldboss/defs", body); host.querySelector("#wbd_msg").textContent = "✅ 已保存"; setTimeout(renderWorldboss, 500); }
      catch (e) { host.querySelector("#wbd_msg").textContent = "保存失败：" + (e.message || e); }
    });
  }
  document.getElementById("newBoss").addEventListener("click", () => openBossDef(null));
  view.querySelectorAll("[data-edit-boss]").forEach((b) => b.addEventListener("click", () =>
    openBossDef((data.defs || []).find((x) => x.id === b.dataset.editBoss))));
  view.querySelectorAll("[data-del-boss]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("确认删除BOSS定义？")) return;
    try { await post("admin/worldboss/defs/delete", { id: b.dataset.delBoss }); renderWorldboss(); } catch (e) { /* ignore */ }
  }));
}

const renderers = {
  dashboard: renderDashboard,
  players: renderPlayers,
  generals: renderGenerals,
  skills: renderSkills,
  troops: renderTroops,
  troopEffects: renderTroopEffects,
  guilds: renderGuilds,
  equipments: renderEquipments,
  auctions: renderAuctions,
  events: renderEvents,
  jobs: renderJobs,
  worldboss: renderWorldboss,
  items: renderItems,
  broadcast: renderBroadcast,
};

document.getElementById("tabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab");
  if (!tab || !tab.dataset.view) return;
  document.querySelectorAll(".tab[data-view]").forEach((t) => t.classList.remove("active"));
  tab.classList.add("active");
  const fn = renderers[tab.dataset.view] || renderDashboard;
  fn();
});

await ready();
renderDashboard();
