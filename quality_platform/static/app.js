/* 质量工程平台前端交互 */

async function getJSON(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

function esc(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : String(s);
  return div.innerHTML;
}

function statusClass(s) {
  if (s === "passed") return "pass";
  if (s === "failed" || s === "error") return "fail";
  return "skip";
}

function renderRuns(runs, tbodyId) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  tbody.innerHTML = runs.map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${esc(r.test_path)}</td>
      <td>${r.total}</td>
      <td class="pass">${r.passed}</td>
      <td class="fail">${r.failed}</td>
      <td>${r.total ? Math.round(r.passed / r.total * 100) : 0}%</td>
      <td>${r.duration ? r.duration + "s" : "-"}</td>
      <td>${esc(r.started_at || "")}</td>
      <td class="${r.status === "finished" ? "pass" : "skip"}">${r.status}</td>
      <td><a href="/runs/${r.id}">详情</a></td>
    </tr>`).join("") || '<tr><td colspan="10" style="text-align:center;color:#9aa2b1">暂无执行记录</td></tr>';
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

async function loadDashboard() {
  try {
    const d = await getJSON("/api/dashboard");
    renderGate(d.gate);
    document.getElementById("k-score").textContent = d.quality_score.score;
    document.getElementById("k-total").textContent = d.summary.total_cases;
    document.getElementById("k-passrate").textContent = d.summary.pass_rate + "%";
    document.getElementById("k-flaky").textContent = d.summary.flaky_count;
    document.getElementById("k-stablefail").textContent = d.summary.stable_fail;
    document.getElementById("k-runs").textContent = d.summary.run_count;
    if (document.getElementById("k-env")) {
      const e = d.env;
      document.getElementById("k-env").textContent =
        `Python ${e.python} · ${e.host}`;
    }
    renderRuns(d.executions, "runs-tbody");
    const labels = d.trend.map(r => "#" + r.id);
    const rates = d.trend.map(r => r.pass_rate);
    new Chart(document.getElementById("trendChart"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "通过率 %", data: rates, borderColor: "#378add",
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
    });
    const dist = d.pyramid.distribution || {};
    const entries = Object.entries(dist).sort((a, b) => b[1] - a[1]);
    new Chart(document.getElementById("pyramidChart"), {
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
    });
  } catch (e) { console.error(e); }
}

/* ---------- 失败分析 ---------- */
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
          <td class="msg" title="${esc(c.fingerprint)}">${esc(c.fingerprint.slice(0, 70))}</td>
          <td><b>${c.count}</b></td>
          <td class="msg">${esc(c.sample_nodeid)}</td>
        </tr>`).join("") || '<tr><td colspan="5" style="text-align:center;color:#9aa2b1">暂无失败，无需聚类</td></tr>';
    }
    if (!tbody) return;
    tbody.innerHTML = d.failures.map(f => `
      <tr>
        <td>${esc(f.nodeid)}</td>
        <td class="fail">${esc(f.error_type || "")}</td>
        <td class="msg" title="${esc(f.error_message || "")}">${esc((f.error_message || "").slice(0, 60))}</td>
        <td>${f.screenshot ? `<a class="shot" href="/${f.screenshot}" target="_blank">截图</a>` : "-"}</td>
        <td><div id="ana-${f.id}">${f.analysis_html || '<span class="hint">未分析</span>'}</div></td>
        <td>
          <button class="btn" onclick="analyzeFailure(${f.id})">AI 归因</button>
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
    box.innerHTML = `<div class="analysis"><b>[${esc(r.category)}]</b> 置信度 ${(r.confidence * 100).toFixed(0)}%（${r.source === "llm" ? "LLM" : "规则"}）<br>${esc(r.suggestion || "")}</div>`;
  } catch (e) { box.innerHTML = '<span class="hint">分析失败</span>'; }
}

/* ---------- flaky 检测 ---------- */
async function detectFlaky() {
  const el = document.getElementById("flaky-result");
  if (!el) return;
  el.textContent = "检测中...";
  try {
    const r = await getJSON("/api/flaky");
    const names = r.flaky.map(f => f.nodeid.split("::").pop() + "(" + Math.round(f.fail_rate * 100) + "%)").join("、");
    el.textContent = `发现 ${r.summary.detected_flaky} 个 flaky：${names || "无"}；稳定失败 ${r.summary.stable_fail} 个`;
  } catch (e) { el.textContent = "检测失败：" + e.message; }
}

/* ---------- 执行中心 ---------- */
async function loadHistory() {
  const tbody = document.getElementById("history-tbody");
  if (!tbody) return;
  try {
    const d = await getJSON("/api/runs");
    renderRuns(d.runs, "history-tbody");
  } catch (e) { console.error(e); }
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
    setTimeout(() => { msg.textContent = "执行中，可在下方刷新查看（点详情看用例级结果）"; loadHistory(); }, 1500);
  } catch (e) { msg.textContent = "触发失败：" + e.message; }
}

/* ---------- 执行详情 ---------- */
async function loadRunDetail() {
  const tbody = document.getElementById("detail-tbody");
  if (!tbody) return;
  const execId = tbody.dataset.exec;
  try {
    const d = await getJSON("/api/runs/" + execId);
    tbody.innerHTML = d.cases.map(c => `
      <tr>
        <td>${esc(c.nodeid)}</td>
        <td class="${statusClass(c.status)}">${c.status}</td>
        <td>${c.duration}s</td>
        <td class="${c.error_type ? "fail" : ""}">${esc(c.error_type || "")}</td>
        <td class="msg" title="${esc(c.error_message || "")}">${esc((c.error_message || "").slice(0, 60))}</td>
        <td>${c.screenshot ? `<a class="shot" href="/${c.screenshot}" target="_blank">截图</a>` : "-"}</td>
      </tr>`).join("");
  } catch (e) { tbody.innerHTML = '<tr><td colspan="6">加载失败：' + esc(e.message) + "</td></tr>"; }
}

/* ---------- 定时任务 ---------- */
async function loadSchedules() {
  const tbody = document.getElementById("sched-tbody");
  if (!tbody) return;
  try {
    const d = await getJSON("/api/schedules");
    tbody.innerHTML = d.schedules.map(s => `
      <tr>
        <td>${s.id}</td>
        <td>${esc(s.name)}</td>
        <td>${s.kind === "daily" ? "每日" : "每N小时"}</td>
        <td>${esc(s.cron_value)}${s.kind === "daily" ? "" : " 小时"}</td>
        <td>${esc(s.test_path)}</td>
        <td>${s.reruns}</td>
        <td class="${s.enabled ? "pass" : "skip"}">${s.enabled ? "启用" : "停用"}</td>
        <td>${esc(s.last_run || "-")}</td>
        <td>
          <button class="btn" onclick="toggleSched(${s.id}, ${s.enabled ? 0 : 1})">${s.enabled ? "停用" : "启用"}</button>
          <button class="btn" onclick="delSched(${s.id})">删除</button>
        </td>
      </tr>`).join("") || '<tr><td colspan="9" style="text-align:center;color:#9aa2b1">暂无定时任务</td></tr>';
  } catch (e) { console.error(e); }
}

async function addSchedule() {
  const msg = document.getElementById("run-msg");
  try {
    await getJSON("/api/schedules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("sched-name").value.trim(),
        kind: document.getElementById("sched-kind").value,
        cron_value: document.getElementById("sched-cron").value.trim(),
        test_path: document.getElementById("sched-path").value.trim(),
        reruns: 1,
      }),
    });
    msg.textContent = "定时任务已创建";
    loadSchedules();
  } catch (e) { msg.textContent = "创建失败：" + e.message; }
}

async function toggleSched(id, enabled) {
  await getJSON(`/api/schedules/${id}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  loadSchedules();
}

async function delSched(id) {
  await getJSON(`/api/schedules/${id}`, { method: "DELETE" });
  loadSchedules();
}

/* ---------- 用例清单 ---------- */
async function loadCases() {
  const pre = document.getElementById("cases-pre");
  const count = document.getElementById("case-count");
  if (!pre) return;
  try {
    const d = await getJSON("/api/cases");
    window._cases = d.cases || [];
    if (count) count.textContent = "共 " + d.count + " 条";
    applyCaseFilter();
  } catch (e) { pre.textContent = "收集失败：" + e.message; }
}

function applyCaseFilter() {
  const pre = document.getElementById("cases-pre");
  const kw = (document.getElementById("case-filter").value || "").trim();
  const list = kw ? window._cases.filter(c => c.includes(kw)) : window._cases;
  pre.textContent = list.join("\n");
}

/* ---------- 初始化 ---------- */
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("trendChart")) loadDashboard();
  if (document.getElementById("failures-tbody")) {
    loadFailures();
    const btn = document.getElementById("btn-flaky");
    if (btn) btn.onclick = detectFlaky;
  }
  if (document.getElementById("history-tbody")) {
    loadHistory();
    const btn = document.getElementById("btn-run");
    if (btn) btn.onclick = triggerRun;
    loadSchedules();
    const sbtn = document.getElementById("btn-sched");
    if (sbtn) sbtn.onclick = addSchedule;
  }
  if (document.getElementById("detail-tbody")) loadRunDetail();
  if (document.getElementById("cases-pre")) {
    loadCases();
    document.getElementById("case-filter").addEventListener("input", applyCaseFilter);
  }
});
