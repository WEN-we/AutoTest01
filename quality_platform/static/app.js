/* 质量工程平台前端交互
 * 约定：
 * - window._user 由 base.html 服务端注入（全站可用）：{id, username, role}
 * - admin-only 操作（取消执行/删除/启停/导入）：按钮仅对 admin 渲染，与后端 RBAC 对齐
 * - 执行历史状态：finished/running/cancelled/timeout 全量展示，运行中可取消
 */

function isAdmin() {
  return (window._user && window._user.role) === "admin";
}

async function getJSON(url, options) {
  const resp = await fetch(url, options);
  if (resp.status === 401) { location.href = "/login"; throw new Error("未登录"); }
  if (!resp.ok) {
    // 优先解析后端标准错误结构 {"error": "..."}，避免把原始 JSON 文本甩给用户
    let msg = "HTTP " + resp.status;
    try { const d = await resp.json(); if (d && d.error) msg = d.error; } catch (_) { /* ignore */ }
    throw new Error(msg);
  }
  return resp.json();
}

function esc(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}

/* ---------- 执行状态徽章 ---------- */
const RUN_STATUS = {
  finished:  ["pass", "完成"],
  running:   ["run",  "运行中"],
  cancelled: ["skip", "已取消"],
  interrupted: ["skip", "中断(服务重启)"],
  timeout:   ["fail", "超时终止"],
};

function statusBadge(status) {
  const [cls, label] = RUN_STATUS[status] || ["skip", status];
  return `<span class="${cls}">${label}</span>`;
}

function caseStatusClass(s) {
  if (s === "passed") return "pass";
  if (s === "failed" || s === "error") return "fail";
  if (s === "cancelled") return "skip";
  return "skip";
}

function renderRuns(runs, tbodyId, opts) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  const withCancel = opts && opts.cancel;
  tbody.innerHTML = (runs || []).map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${esc(r.test_path)}</td>
      <td>${r.total}</td>
      <td class="pass">${r.passed}</td>
      <td class="fail">${r.failed}</td>
      <td>${r.total ? Math.round(r.passed / r.total * 100) : 0}%</td>
      <td>${r.duration ? r.duration + "s" : "-"}</td>
      <td>${esc(r.started_at || "")}</td>
      <td>${statusBadge(r.status)}</td>
      <td>
        <a href="/runs/${r.id}">详情</a>
        ${withCancel && isAdmin() && r.status === "running"
          ? ` <button class="btn btn-danger" onclick="cancelRun(${r.id})">取消</button>` : ""}
      </td>
    </tr>`).join("") || '<tr><td colspan="10" style="text-align:center;color:#9aa2b1">暂无执行记录</td></tr>';
}

/* ---------- 登录 / 登出（全站导航） ---------- */
function initNav() {
  const userEl = document.getElementById("nav-user");
  const logoutEl = document.getElementById("btn-logout");
  if (!userEl) return;
  const user = window._user;
  if (user && user.username) {
    userEl.textContent = user.username + "（" + (user.role === "admin" ? "管理员" : "用户") + "）";
    logoutEl.style.display = "";
    logoutEl.onclick = async (e) => {
      e.preventDefault();
      try { await getJSON("/api/logout", { method: "POST" }); } catch (_) { /* ignore */ }
      location.href = "/login";
    };
  }
}

/* 非 admin 隐藏管理按钮（模板中标注 .admin-only 的元素） */
function applyAcl() {
  if (isAdmin()) return;
  document.querySelectorAll(".admin-only").forEach(el => { el.style.display = "none"; });
}

/* ---------- 看板 ---------- */
function renderGate(gate) {
  const el = document.getElementById("gate-banner");
  if (!el) return;
  if (!gate || gate.status === "no_data" || gate.status === "disabled") {
    el.className = "gate gate-none";
    el.innerHTML = `质量门禁：${gate && gate.status === "disabled" ? "已停用" : "暂无执行数据，触发执行后自动评估"}`;
    return;
  }
  const map = { PASS: ["gate-pass", "✅ 门禁通过"], WARN: ["gate-warn", "⚠️ 门禁告警"], FAIL: ["gate-fail", "❌ 门禁未过（阻止发布）"] };
  const [cls, label] = map[gate.status] || ["gate-none", gate.status];
  el.className = "gate " + cls;
  el.innerHTML = `${label} <small>· 最近执行 #${gate.latest_run.id}（${esc(gate.latest_run.test_path)}）通过率 ${gate.latest_run.pass_rate}% · ` +
    gate.rules.map(r => `${r.name} ${r.actual}${r.unit}${r.violated ? " ✗" : ""}`).join(" / ") + "</small>";
}

function renderChart(canvasId, build) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (typeof Chart === "undefined") {
    // 图表库未加载（理论上本地化后不会发生）——降级为文字提示而非静默白屏
    canvas.outerHTML = '<div class="hint">图表组件未加载</div>';
    return;
  }
  build(canvas);
}

async function loadDashboard() {
  try {
    const d = await getJSON("/api/dashboard");
    window._user = d.user || window._user;
    initNav();
    renderGate(d.gate);
    document.getElementById("k-score").textContent = d.quality_score.score;
    document.getElementById("k-total").textContent = d.summary.total_cases;
    document.getElementById("k-passrate").textContent = d.summary.pass_rate + "%";
    document.getElementById("k-flaky").textContent = d.summary.flaky_count;
    document.getElementById("k-stablefail").textContent = d.summary.stable_fail;
    document.getElementById("k-runs").textContent = d.summary.run_count;
    if (document.getElementById("k-env")) {
      const e = d.env;
      document.getElementById("k-env").textContent = `Python ${e.python} · ${e.host}`;
    }
    // 平台健康（可观测性：DB/节点/队列/告警）
    try {
      const h = await getJSON("/api/health");
      document.getElementById("h-db").textContent = h.db.ok ? h.db.backend : "异常";
      const alive = (h.workers || []).filter(w => w.ok).length;
      document.getElementById("h-workers").textContent =
        (h.workers && h.workers.length ? `${alive}/${h.workers.length}` : "仅本地");
      document.getElementById("h-queue").textContent =
        `${h.queue.running}/${h.queue.queued}`;
      const alerts = h.alerts || [];
      document.getElementById("h-alerts").textContent =
        alerts.length ? `${alerts.length} 条` : "无";
      if (alerts.length) {
        document.getElementById("h-alerts").style.color = "#e5534b";
      }
    } catch (e) {
      document.getElementById("h-db").textContent = "-";
    }
    renderRuns(d.executions, "runs-tbody");
    renderChart("trendChart", (canvas) => new Chart(canvas, {
      type: "line",
      data: {
        labels: d.trend.map(r => "#" + r.id),
        datasets: [{
          label: "通过率 %", data: d.trend.map(r => r.pass_rate), borderColor: "#378add",
          backgroundColor: "rgba(55,138,221,0.15)", fill: true, tension: 0.3,
        }],
      },
      options: {
        plugins: { legend: { labels: { color: "#9aa2b1" } } },
        scales: {
          x: { ticks: { color: "#9aa2b1" } },
          y: { min: 0, max: 100, ticks: { color: "#9aa2b1" } },
        },
      },
    }));
    const dist = d.pyramid.distribution || {};
    const entries = Object.entries(dist).sort((a, b) => b[1] - a[1]);
    renderChart("pyramidChart", (canvas) => new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: entries.map(e => e[0]),
        datasets: [{
          data: entries.map(e => e[1]),
          backgroundColor: ["#378add", "#1d9e75", "#d4537e", "#ef9f27", "#7f77dd", "#639922", "#888780"],
        }],
      },
      options: {
        plugins: { legend: { position: "right", labels: { color: "#9aa2b1" } } },
      },
    }));
  } catch (e) { console.error(e); }
}

/* ---------- 失败分析 ---------- */
function analysisHtml(f) {
  // 后端在 /api/failures 中联表返回已缓存的归因（ana_* 字段）
  if (f.ana_category) {
    const pct = Math.round((f.ana_confidence || 0) * 100);
    return `<div class="analysis"><b>[${esc(f.ana_category)}]</b> 置信度 ${pct}%（${f.ana_source === "llm" ? "LLM" : "规则"}）<br>${esc(f.ana_suggestion || "")}</div>`;
  }
  return '<span class="hint">未分析</span>';
}

async function loadFailures() {
  const tbody = document.getElementById("failures-tbody");
  const cbody = document.getElementById("clusters-tbody");
  try {
    const d = await getJSON("/api/failures");
    if (cbody) {
      const cs = d.clusters || { clusters: [] };
      cbody.innerHTML = (cs.clusters || []).map(c => `
        <tr>
          <td>${c.id}</td>
          <td class="fail">${esc(c.error_type)}</td>
          <td class="msg" title="${esc(c.fingerprint)}">${esc(String(c.fingerprint).slice(0, 70))}</td>
          <td><b>${c.count}</b></td>
          <td class="msg">${esc(c.sample_nodeid)}</td>
        </tr>`).join("") || '<tr><td colspan="5" style="text-align:center;color:#9aa2b1">暂无失败，无需聚类</td></tr>';
    }
    if (!tbody) return;
    tbody.innerHTML = (d.failures || []).map(f => `
      <tr>
        <td>${esc(f.nodeid)}</td>
        <td class="fail">${esc(f.error_type || "")}</td>
        <td class="msg" title="${esc(f.error_message || "")}">${esc((f.error_message || "").slice(0, 60))}</td>
        <td>${f.screenshot ? `<a class="shot" href="/${esc(f.screenshot)}" target="_blank">截图</a>` : "-"}</td>
        <td><div id="ana-${f.id}">${analysisHtml(f)}</div></td>
        <td>
          <button class="btn" onclick="analyzeFailure(${f.id})">${f.ana_category ? "重新归因" : "AI 归因"}</button>
          <button class="btn" onclick="toggleDetail(${f.id})">详情</button>
        </td>
      </tr>
      <tr id="detail-${f.id}" style="display:none">
        <td colspan="6"><pre class="errbox">${esc(f.error_message || "无错误信息")}</pre></td>
      </tr>`).join("") || '<tr><td colspan="6" style="text-align:center;color:#9aa2b1">暂无失败用例</td></tr>';
  } catch (e) { console.error(e); }
}

function toggleDetail(id) {
  const el = document.getElementById("detail-" + id);
  if (el) el.style.display = el.style.display === "none" ? "" : "none";
}

async function analyzeFailure(id) {
  const box = document.getElementById("ana-" + id);
  if (!box) return;
  box.innerHTML = '<span class="hint">分析中...</span>';
  try {
    const r = await getJSON(`/api/failures/${id}/analyze`, { method: "POST" });
    const pct = Math.round((r.confidence || 0) * 100);
    box.innerHTML = `<div class="analysis"><b>[${esc(r.category)}]</b> 置信度 ${pct}%（${r.source === "llm" ? "LLM" : "规则"}）<br>${esc(r.suggestion || "")}</div>`;
  } catch (e) { box.innerHTML = `<span class="hint">分析失败：${esc(e.message)}</span>`; }
}

/* ---------- flaky 检测 ---------- */
async function detectFlaky() {
  const el = document.getElementById("flaky-result");
  if (!el) return;
  el.textContent = "检测中...";
  try {
    const r = await getJSON("/api/flaky");
    const names = (r.flaky || []).map(f => f.nodeid.split("::").pop() + "(" + Math.round(f.fail_rate * 100) + "%)").join("、");
    el.textContent = `发现 ${r.summary.detected_flaky} 个 flaky：${names || "无"}；稳定失败 ${r.summary.stable_fail} 个`;
  } catch (e) { el.textContent = "检测失败：" + e.message; }
}

/* ---------- 执行中心 ---------- */
async function loadQueue() {
  const el = document.getElementById("queue-banner");
  if (!el) return;
  try {
    const q = await getJSON("/api/queue");
    el.innerHTML = `执行队列：运行中 <b>${q.running}</b> · 排队中 <b>${q.queued}</b> · 并发上限 ${q.max_workers}` +
      (q.cancelling ? ` · <span class="fail">待取消 ${q.cancelling}</span>` : "");
  } catch (e) { /* 队列状态失败不打扰用户 */ }
}

async function loadHistory() {
  const tbody = document.getElementById("history-tbody");
  if (!tbody) return;
  try {
    const d = await getJSON("/api/runs");
    renderRuns(d.runs, "history-tbody", { cancel: true });
  } catch (e) { console.error(e); }
}

async function cancelRun(id) {
  if (!confirm(`确认取消执行 #${id}？\n运行中将终止测试子进程。`)) return;
  try {
    const r = await getJSON(`/api/runs/${id}/cancel`, { method: "POST" });
    alert(r.state === "cancelled_before_start" ? "已取消（尚未开始）" : "已发送取消指令，状态稍后更新");
    loadHistory();
    loadQueue();
  } catch (e) { alert("取消失败：" + e.message); }
}

/* ---------- 精准测试（git 变更 → 影响面分析 → 按建议集执行） ---------- */
async function runImpact() {
  const el = document.getElementById("impact-result");
  if (!el) return;
  el.textContent = "分析 git 变更中...";
  try {
    const d = await getJSON("/api/impact");
    const tests = d.suggested_tests || [];
    if (!tests.length) {
      el.textContent = "无变更或未匹配到测试集（干净工作区）";
      return;
    }
    const reasons = Object.entries(d.reasons || {})
      .map(([dir, rs]) => `${dir}（${rs.length} 处变更）`).join("、");
    if (!confirm(`本次变更 ${d.changed_files.length} 个文件，建议执行 ${tests.length} 个测试集：\n${tests.join("\n")}\n\n原因：${reasons}\n\n确认按建议集执行？`)) {
      el.textContent = `已取消（建议 ${tests.length} 个测试集：${tests.join("、")}）`;
      return;
    }
    const r = await getJSON("/api/impact/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    el.textContent = `已触发 ${r.execution_ids.length} 个执行（#${r.execution_ids.join(" #")}），见下方历史`;
    loadHistory();
    loadQueue();
  } catch (e) { el.textContent = "精准执行失败：" + e.message; }
}

async function triggerRun() {
  const path = document.getElementById("test-path").value.trim();
  const msg = document.getElementById("run-msg");
  if (!path) { msg.textContent = "请输入测试路径"; return; }
  msg.textContent = "执行已触发（后台运行中）...";
  try {
    await getJSON("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        test_path: path,
        reruns: parseInt(document.getElementById("opt-reruns").value || "0", 10),
        parallel: parseInt(document.getElementById("opt-parallel").value || "0", 10),
        timeout: parseInt(document.getElementById("opt-timeout").value || "0", 10),
        marker: document.getElementById("opt-marker").value.trim(),
      }),
    });
    msg.textContent = "执行中，可在下方刷新查看（点详情看用例级结果）";
    loadHistory();
    loadQueue();
  } catch (e) { msg.textContent = "触发失败：" + e.message; }
}

/* ---------- 执行详情 + 单用例重跑 ---------- */
async function loadRunDetail() {
  const tbody = document.getElementById("detail-tbody");
  if (!tbody) return;
  const execId = tbody.dataset.exec;
  try {
    const d = await getJSON("/api/runs/" + execId);
    tbody.innerHTML = (d.cases || []).map(c => `
      <tr>
        <td>${esc(c.nodeid)}</td>
        <td class="${caseStatusClass(c.status)}">${c.status}</td>
        <td>${c.duration}s</td>
        <td class="${c.error_type ? "fail" : ""}">${esc(c.error_type || "")}</td>
        <td class="msg" title="${esc(c.error_message || "")}">${esc((c.error_message || "").slice(0, 60))}</td>
        <td>${c.screenshot ? `<a class="shot" href="/${esc(c.screenshot)}" target="_blank">截图</a>` : "-"}</td>
        <td><button class="btn" onclick="rerunCase('${esc(c.nodeid).replace(/'/g, "\\'")}')">重跑</button></td>
      </tr>`).join("") || '<tr><td colspan="7" style="text-align:center;color:#9aa2b1">无用例结果</td></tr>';
  } catch (e) { tbody.innerHTML = '<tr><td colspan="7">加载失败：' + esc(e.message) + "</td></tr>"; }
}

async function rerunCase(nodeid) {
  if (!confirm("重跑该用例？\n" + nodeid)) return;
  try {
    await getJSON("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ test_path: nodeid, reruns: 1, timeout: 30 }),
    });
    alert("已触发重跑，去执行中心查看");
  } catch (e) { alert("触发失败：" + e.message); }
}

/* ---------- 定时任务 ---------- */
async function loadSchedules() {
  const tbody = document.getElementById("sched-tbody");
  if (!tbody) return;
  try {
    const d = await getJSON("/api/schedules");
    tbody.innerHTML = (d.schedules || []).map(s => `
      <tr>
        <td>${s.id}</td>
        <td>${esc(s.name)}</td>
        <td>${s.kind === "daily" ? "每日" : "每N小时"}</td>
        <td>${esc(s.cron_value)}${s.kind === "daily" ? "" : " 小时"}</td>
        <td>${esc(s.test_path)}</td>
        <td>${s.reruns}</td>
        <td class="${s.enabled ? "pass" : "skip"}">${s.enabled ? "启用" : "停用"}</td>
        <td>${esc(s.last_run || "-")}</td>
        <td>${isAdmin() ? `
          <button class="btn" onclick="toggleSched(${s.id}, ${s.enabled ? 0 : 1})">${s.enabled ? "停用" : "启用"}</button>
          <button class="btn btn-danger" onclick="delSched(${s.id})">删除</button>` : '<span class="hint">-</span>'}
        </td>
      </tr>`).join("") || '<tr><td colspan="9" style="text-align:center;color:#9aa2b1">暂无定时任务</td></tr>';
  } catch (e) { console.error(e); }
}

async function addSchedule() {
  const msg = document.getElementById("sched-msg");
  const path = document.getElementById("sched-path").value.trim();
  if (!path) { msg.textContent = "请输入测试路径"; return; }
  try {
    await getJSON("/api/schedules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("sched-name").value.trim(),
        kind: document.getElementById("sched-kind").value,
        cron_value: document.getElementById("sched-cron").value.trim(),
        test_path: path,
        reruns: 1,
      }),
    });
    msg.textContent = "定时任务已创建";
    loadSchedules();
  } catch (e) { msg.textContent = "创建失败：" + e.message; }
}

async function toggleSched(id, enabled) {
  try {
    await getJSON(`/api/schedules/${id}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    loadSchedules();
  } catch (e) { alert("操作失败：" + e.message); }
}

async function delSched(id) {
  if (!confirm(`确认删除定时任务 #${id}？该操作不可恢复。`)) return;
  try {
    await getJSON(`/api/schedules/${id}`, { method: "DELETE" });
    loadSchedules();
  } catch (e) { alert("删除失败：" + e.message); }
}

/* ---------- 用例管理（CRUD） ---------- */
async function loadManageCases() {
  const tbody = document.getElementById("manage-tbody");
  if (!tbody) return;
  try {
    const kw = (document.getElementById("case-filter").value || "").trim();
    const d = await getJSON("/api/cases/manage?keyword=" + encodeURIComponent(kw));
    tbody.innerHTML = (d.cases || []).map(c => `
      <tr>
        <td>${c.id}</td>
        <td class="msg" title="${esc(c.nodeid)}">${esc(c.nodeid)}</td>
        <td>${esc(c.module || "")}</td>
        <td>${esc(c.tags || "")}</td>
        <td>${esc(c.owner || "")}</td>
        <td class="${c.status === "active" ? "pass" : "skip"}">${c.status === "active" ? "启用" : "停用"}</td>
        <td>${isAdmin() ? `
          <button class="btn" onclick="editCase(${c.id}, '${esc(c.status).replace(/'/g, "\\'")}')">${c.status === "active" ? "停用" : "启用"}</button>
          <button class="btn btn-danger" onclick="delCase(${c.id})">删除</button>` : '<span class="hint">-</span>'}
        </td>
      </tr>`).join("") || '<tr><td colspan="7" style="text-align:center;color:#9aa2b1">用例库为空，可点击"从 pytest 一键导入"</td></tr>';
  } catch (e) { console.error(e); }
}

async function importCases() {
  const btn = document.querySelector('button[onclick="importCases()"]');
  const count = document.getElementById("case-count");
  if (btn) { btn.disabled = true; btn.textContent = "导入中..."; }
  try {
    const d = await getJSON("/api/cases/import", { method: "POST" });
    if (count) count.textContent = `导入完成：新增 ${d.imported}，更新 ${d.updated}`;
    loadManageCases();
  } catch (e) { if (count) count.textContent = "导入失败：" + e.message; }
  if (btn) { btn.disabled = false; btn.textContent = "从 pytest 一键导入"; }
}

async function showAddCase() {
  const nodeid = prompt("输入用例 nodeid（如 tests/test_api/test_user_api.py::TestUserApi::test_user_login[case0]）：");
  if (!nodeid) return;
  try {
    await getJSON("/api/cases/manage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nodeid }),
    });
    loadManageCases();
  } catch (e) { alert("新增失败：" + e.message); }
}

async function editCase(id, status) {
  const next = status === "active" ? "disabled" : "active";
  try {
    await getJSON(`/api/cases/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
    loadManageCases();
  } catch (e) { alert("操作失败：" + e.message); }
}

async function delCase(id) {
  if (!confirm("删除该用例记录？")) return;
  try {
    await getJSON(`/api/cases/${id}`, { method: "DELETE" });
    loadManageCases();
  } catch (e) { alert("删除失败：" + e.message); }
}

/* ---------- 用例清单（collect 只读） ---------- */
async function loadCases() {
  const pre = document.getElementById("cases-pre");
  const count = document.getElementById("case-count");
  if (!pre) return;
  try {
    const d = await getJSON("/api/cases");
    window._cases = d.cases || [];
    if (count) count.textContent = "collect 共 " + d.count + " 条";
    applyCaseFilter();
  } catch (e) { pre.textContent = "收集失败：" + e.message; }
}

function applyCaseFilter() {
  const pre = document.getElementById("cases-pre");
  if (!pre) return;
  const kw = (document.getElementById("case-filter").value || "").trim();
  const list = kw ? (window._cases || []).filter(c => c.includes(kw)) : (window._cases || []);
  pre.textContent = list.join("\n");
}

/* ---------- AI 配置（管理员） ---------- */
async function loadAiConfig() {
  try {
    const d = await getJSON("/api/ai/config");
    window._aiPresets = d.presets || {};
    const sel = document.getElementById("ai-provider-select");
    if (sel) {
      sel.innerHTML = Object.entries(window._aiPresets).map(([k, v]) =>
        `<option value="${k}">${esc(v.label)}</option>`).join("");
    }
    // 状态卡
    const act = d.active;
    document.getElementById("ai-status").textContent = act ? "已启用" : "未配置(规则兜底)";
    document.getElementById("ai-status").className = "num " + (act ? "pass" : "skip");
    if (d.configured && d.settings) {
      const s = d.settings;
      document.getElementById("ai-provider").textContent = s.provider;
      document.getElementById("ai-model").textContent = s.model;
      document.getElementById("ai-key").textContent = s.api_key_masked || "(空/本地模型)";
      if (sel) sel.value = s.provider;
      document.getElementById("ai-base-url").value = s.base_url;
      document.getElementById("ai-model-input").value = s.model;
      document.getElementById("ai-enabled").checked = s.enabled;
    } else {
      document.getElementById("ai-provider").textContent = "-";
      document.getElementById("ai-model").textContent = "-";
      document.getElementById("ai-key").textContent = "-";
      if (sel) applyAiPreset(Object.keys(window._aiPresets)[0]);
    }
    // 服务商说明表
    const tb = document.getElementById("presets-tbody");
    if (tb) {
      tb.innerHTML = Object.entries(window._aiPresets).map(([k, v]) => `
        <tr><td>${esc(v.label)}</td><td>${esc(v.base_url || "-")}</td>
        <td>${esc(v.model || "-")}</td><td>${v.need_key ? "是" : "否"}</td></tr>`).join("");
    }
  } catch (e) { console.error(e); }
}

function applyAiPreset(provider) {
  const p = (window._aiPresets || {})[provider];
  if (!p) return;
  document.getElementById("ai-base-url").value = p.base_url || "";
  document.getElementById("ai-model-input").value = p.model || "";
}

async function saveAiConfig(e) {
  if (e) e.preventDefault();
  const msg = document.getElementById("ai-msg");
  msg.textContent = "保存中...";
  try {
    const body = {
      provider: document.getElementById("ai-provider-select").value,
      base_url: document.getElementById("ai-base-url").value,
      api_key: document.getElementById("ai-api-key").value,
      model: document.getElementById("ai-model-input").value,
      enabled: document.getElementById("ai-enabled").checked,
    };
    const d = await getJSON("/api/ai/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    document.getElementById("ai-api-key").value = "";  // 已落库，清空输入
    msg.textContent = "✅ 已保存（" + (d.active ? "启用中" : "未启用") + "）";
    loadAiConfig();
  } catch (err) { msg.textContent = "❌ " + err.message; }
}

async function testAiConfig() {
  const msg = document.getElementById("ai-msg");
  msg.textContent = "测试中（最长 60s）...";
  try {
    const body = {
      base_url: document.getElementById("ai-base-url").value,
      api_key: document.getElementById("ai-api-key").value,
      model: document.getElementById("ai-model-input").value,
    };
    const d = await getJSON("/api/ai/config/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    msg.textContent = (d.ok ? "✅ " : "❌ ") + d.message;
  } catch (err) { msg.textContent = "❌ " + err.message; }
}

/* ---------- 初始化 ---------- */
let _filterTimer = null;
document.addEventListener("DOMContentLoaded", () => {
  initNav();      // 全站导航（window._user 由服务端注入）
  applyAcl();     // 非 admin 隐藏管理按钮

  if (document.getElementById("trendChart")) loadDashboard();
  if (document.getElementById("failures-tbody")) {
    loadFailures();
    const btn = document.getElementById("btn-flaky");
    if (btn) btn.onclick = detectFlaky;
  }
  if (document.getElementById("ai-provider-select")) {
    loadAiConfig();
    const sel = document.getElementById("ai-provider-select");
    if (sel) sel.onchange = () => applyAiPreset(sel.value);
    const form = document.getElementById("ai-config-form");
    if (form) form.onsubmit = saveAiConfig;
    const tbtn = document.getElementById("btn-ai-test");
    if (tbtn) tbtn.onclick = testAiConfig;
  }
  if (document.getElementById("history-tbody")) {
    loadHistory();
    loadQueue();
    document.getElementById("btn-run").onclick = triggerRun;
    loadSchedules();
    const sbtn = document.getElementById("btn-sched");
    if (sbtn) sbtn.onclick = addSchedule;
    const ibtn = document.getElementById("btn-impact");
    if (ibtn) ibtn.onclick = runImpact;
    // 有运行中任务时轮询刷新（页面不可见时暂停，避免无谓请求）
    setInterval(() => {
      if (document.visibilityState === "visible") { loadHistory(); loadQueue(); }
    }, 10000);
  }
  if (document.getElementById("detail-tbody")) loadRunDetail();
  if (document.getElementById("manage-tbody")) {
    loadManageCases();
    const filter = document.getElementById("case-filter");
    if (filter) filter.addEventListener("input", () => {
      applyCaseFilter();               // 客户端过滤立即生效
      clearTimeout(_filterTimer);      // 服务端查询防抖 300ms
      _filterTimer = setTimeout(loadManageCases, 300);
    });
  }
  if (document.getElementById("cases-pre")) loadCases();
});
