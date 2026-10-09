const bridge = window.AstrBotPluginPage;
const view = document.getElementById("view");

// ---------------- 标签映射（内部键 -> 中文） ----------------
const FACTION = { wei: "魏", shu: "蜀", wu: "吴", qun: "群", custom: "自定义", "": "-" };
const CATEGORY = { historical: "历史武将", obscure: "冷门武将", fictional: "架空武将", custom: "自定义武将" };
const ITEM_CAT = { resource: "资源", consume: "消耗品", buff: "增益", gift: "礼包", functional: "功能", equipment: "装备" };
const CURRENCY = { gold: "金币", diamond: "元宝", merit: "功勋", soul: "将魂", repute: "声望", event_ticket: "活动券", challenge: "挑战令" };
const SHOP = { daily: "每日", weekly: "每周", black: "黑市", event: "活动" };
const RARITY = { ssr: "超稀有", sr: "史诗", r: "稀有", n: "普通", custom: "自定义", any: "任意" };
const BUFF = { double_drop: "双倍掉落", double_gold: "双倍金币", double_exp: "双倍经验", free_stamina: "免行动力" };
const TROOP = { cavalry: "骑兵", infantry: "步兵", archer: "弓兵", spear: "枪兵" };
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
async function renderDashboard() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const s = await api("admin/stats");
  if (s.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(s.__error)}</div>`; return; }
  document.getElementById("version").textContent = "v" + (s.version || "-");
  view.innerHTML = `
    <div class="cards">
      <div class="card"><div class="k">注册玩家</div><div class="v">${s.players}</div></div>
      <div class="card"><div class="k">武将总数</div><div class="v">${s.generals}</div></div>
      <div class="card"><div class="k">道具总数</div><div class="v">${s.items}</div></div>
      <div class="card"><div class="k">维护模式</div><div class="v">${s.maintenance ? "开启" : "关闭"}</div></div>
    </div>`;
}

// ---------------- 玩家管理 ----------------
async function renderPlayers() {
  view.innerHTML = '<div class="loading">加载中…</div>';
  const data = await api("admin/players");
  if (data.__error) { view.innerHTML = `<div class="loading">加载失败：${esc(data.__error)}</div>`; return; }
  const rows = (data.players || []).map((p) => `
    <tr>
      <td>${esc(p.name)}<div class="muted">${esc(p.qq)}</div></td>
      <td>${p.power}</td>
      <td>${p.generals}</td>
      <td>${p.gold}</td>
      <td>${esc(lbl(FACTION, p.faction))}</td>
      <td>${p.win}胜${p.lose}负</td>
    </tr>`).join("");
  view.innerHTML = `
    <div class="muted">共 ${data.total} 名玩家，按战力排序</div>
    <table>
      <thead><tr><th>玩家</th><th>战力</th><th>武将</th><th>金币</th><th>势力</th><th>战绩</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
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
  return genOptions;
}

function renderGeneralEditor(g, o) {
  const attrs = o.attrs || [];
  const attrInputs = attrs.map((a) => `
    <div class="col muted">${esc(a.label)}<input id="g_${esc(a.key)}" type="number" value="${esc((g && g[a.key]) != null ? g[a.key] : 50)}" /></div>
  `).join("");
  return `
    <div class="card" id="genEditor">
      <div class="row">
        <div class="col muted">名称<input id="g_name" value="${esc((g && g.name) || "")}" /></div>
        <div class="col muted">称号<input id="g_title" value="${esc((g && g.title) || "")}" /></div>
      </div>
      <div class="row">
        <div class="col muted">品质<select id="g_rarity">${opts(o.rarities || ["ssr","sr","r","n"], (g && g.rarity) || "sr", (v)=>lbl(RARITY,v))}</select></div>
        <div class="col muted">势力<select id="g_faction">${opts(o.factions || ["wei","shu","wu","qun","custom"], (g && g.faction) || "wei", (v)=>lbl(FACTION,v))}</select></div>
        <div class="col muted">兵种<select id="g_troop">${opts(o.troops || ["cavalry","infantry","archer","spear"], (g && g.troop) || "infantry", (v)=>lbl(TROOP,v))}</select></div>
      </div>
      <div class="row">${attrInputs}</div>
      <div class="row">
        <div class="col muted">主动技能<input id="g_active" value="${esc((g && g.skill && g.skill.active) || "")}" /></div>
        <div class="col muted">被动技能<input id="g_passive" value="${esc((g && g.skill && g.skill.passive) || "")}" /></div>
      </div>
      <div class="muted" style="font-size:12px;opacity:.75">技能字段为技术ID，可留空由系统自动生成（勾选“显示技术字段(ID)”查看）。</div>
      <div class="muted">描述<input id="g_desc" value="${esc((g && g.desc) || "")}" /></div>
      <button class="primary" id="saveGen">保存武将</button>
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

// ---------------- 广播 ----------------
async function renderBroadcast() {
  view.innerHTML = `
    <div class="col">
      <label class="muted">全体广播内容</label>
      <textarea id="bcText" rows="4" placeholder="输入要推送到所有已订阅会话的公告…"></textarea>
      <button class="primary" id="bcSend">发送广播</button>
      <div id="bcResult" class="muted" style="margin-top:10px"></div>
    </div>`;
  document.getElementById("bcSend").addEventListener("click", async () => {
    const text = document.getElementById("bcText").value.trim();
    if (!text) return;
    try {
      const res = await post("admin/broadcast", { text });
      document.getElementById("bcResult").textContent = `已发送到 ${res.sent} 个会话`;
    } catch (e) {
      document.getElementById("bcResult").textContent = "发送失败：" + (e.message || e);
    }
  });
}

const renderers = {
  dashboard: renderDashboard,
  players: renderPlayers,
  generals: renderGenerals,
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
