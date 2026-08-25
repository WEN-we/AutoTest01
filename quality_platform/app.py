"""
质量工程平台（Quality Platform）—— Flask 入口

大厂测开形态落地：鉴权 + 质量看板 + 失败分析（AI 归因）+ 参数化执行 + flaky 治理 + 定时回归 + 用例库

启动：
    python -m quality_platform.app        # 默认 127.0.0.1:8081（用 -m 模块方式）
    # 默认管理员：admin / admin123（首次启动自动创建，请尽快修改）

页面（需登录）：
    /login          登录页
    /               质量看板（门禁/质量分/金字塔/趋势）
    /failures       失败分析（截图 + AI 归因 + 指纹聚类）
    /runs           执行中心（参数化执行 + 定时任务）
    /runs/<id>      执行详情（用例级结果 + 单用例重跑）
    /cases          用例清单（collect 视图 + 用例库管理）
API（写操作需登录，GET 读也需登录）：
    POST /api/login · POST /api/logout
    GET  /api/dashboard · /api/runs · /api/runs/<id> · /api/failures · /api/failures/<id>
    POST /api/failures/<id>/analyze · GET /api/flaky · GET /api/schedules
    POST /api/runs {"test_path","reruns","parallel","timeout","marker"}
    GET  /api/queue · POST /api/runs/<id>/cancel（取消执行）
    GET/POST/DELETE /api/cases/manage · PUT/DELETE /api/cases/<id> · POST /api/cases/import
    GET/POST /api/schedules · DELETE /api/schedules/<id> · POST /api/schedules/<id>/toggle
    GET  /api/report/export
    （标注 admin 的删除/修改/取消类接口需要管理员角色，RBAC：user 只读+触发执行）
"""
import os
import platform
import secrets
import subprocess
import sys
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from quality_platform.models import (create_sso_user, db, ensure_admin,
                                     get_user_by_username, verify_user)
from quality_platform.services.ai_integration import ai
from quality_platform.services.failure_clustering import cluster_failures
from quality_platform.services.gate import evaluate_gate, quality_score, test_pyramid
from quality_platform.services.scheduler import scheduler
from quality_platform.services.test_executor import executor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLATFORM_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(PLATFORM_DIR / "templates"),
            static_folder=str(PLATFORM_DIR / "static"))
# 密钥优先取环境变量；未配置时每次启动随机生成（会话不跨重启保留，但绝不使用固定弱密钥）
_secret = os.getenv("PLATFORM_SECRET", "")
if not _secret:
    _secret = secrets.token_hex(32)
    print("[安全提示] 未设置 PLATFORM_SECRET，本次启动使用随机会话密钥（重启后需重新登录）；"
          "生产环境请在环境变量/.env 中固定配置")
app.secret_key = _secret


# ==============================
# 鉴权
# ==============================
def login_required(view):
    """页面/API 登录保护（大厂：平台必须鉴权）"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录"}), 401
            return redirect(url_for("page_login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """管理操作保护（RBAC：删除/修改共享资源仅 admin；未登录先 401）"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user:
            return jsonify({"error": "未登录"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "需要管理员权限"}), 403
        return view(*args, **kwargs)
    return wrapped


def permission_required(perm: str):
    """细粒度 RBAC 权限保护（admin/engineer/viewer 三级；未登录先 401，无权限 403）。"""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            from quality_platform.services.rbac import has_permission
            user = session.get("user") or {}
            if not has_permission(user.get("role"), perm):
                return jsonify({"error": f"权限不足：需要 {perm} 权限"}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/login")
def page_login():
    if session.get("user"):
        return redirect(url_for("page_dashboard"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = verify_user(username, password)
    if not user:
        db.insert_audit(username, "login", detail="认证失败",
                        ip=request.remote_addr, ok=False)
        return jsonify({"error": "用户名或密码错误"}), 401
    session["user"] = {"id": user["id"], "username": user["username"],
                       "role": user["role"]}
    db.insert_audit(user["username"], "login", ip=request.remote_addr)
    return jsonify({"ok": True, "user": session["user"]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    username = (session.get("user") or {}).get("username", "anonymous")
    session.clear()
    db.insert_audit(username, "logout", ip=request.remote_addr)
    return jsonify({"ok": True})


# ==============================
# 轻量 SSO 单点登录（信任令牌，PLATFORM_SECRET 签名）
# ==============================
@app.route("/sso/login")
def sso_login():
    """外部系统携带 SSO 令牌跳转：验签 -> 建立会话 -> 进入平台。

    用法：<a href="/sso/login?token=xxx">单点登录</a>
    令牌由受信任系统用 PLATFORM_SECRET 签发（见 POST /api/sso/token 演示）。
    """
    from quality_platform.services import sso

    token = request.args.get("token", "")
    identity = sso.verify_token(token) if token else None
    if not identity:
        db.insert_audit("anonymous", "sso_login", detail="令牌无效或已过期",
                        ip=request.remote_addr, ok=False)
        return render_template("login.html", sso_error="SSO 令牌无效或已过期"), 401

    # 首次登录自动开户（SSO 为可信身份源）；admin 角色由签发方授予
    user = get_user_by_username(identity["username"])
    if not user:
        user = create_sso_user(identity["username"], identity["role"])
    session["user"] = {"id": user["id"], "username": user["username"],
                       "role": user["role"]}
    db.insert_audit(user["username"], "sso_login", detail="单点登录成功",
                    ip=request.remote_addr, ok=True)
    return redirect(url_for("page_dashboard"))


@app.route("/api/sso/token", methods=["POST"])
@admin_required
def api_sso_issue():
    """（管理员）为外部系统签发一次性 SSO 令牌，用于集成联调/演示。"""
    from quality_platform.services import sso

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    role = (data.get("role") or "user").strip()
    ttl = int(data.get("ttl", sso.DEFAULT_TTL))
    if not username:
        return jsonify({"error": "username 不能为空"}), 400
    result = sso.issue_token(username, role, ttl=ttl)
    _audit("sso_issue", target=username, detail=f"role={role} ttl={ttl}s")
    return jsonify({"ok": True, **result})


def _current_user() -> dict:
    return session.get("user", {})


def _audit(action: str, target: str = "", detail: str = "", ok: bool = True):
    """统一审计埋点（当前会话用户 + 来源 IP）"""
    username = (session.get("user") or {}).get("username", "anonymous")
    db.insert_audit(username, action, target=target, detail=detail,
                    ip=request.remote_addr, ok=ok)


# ==============================
# 页面
# ==============================
@app.route("/")
@login_required
def page_dashboard():
    return render_template("dashboard.html")


@app.route("/failures")
@login_required
def page_failures():
    return render_template("failures.html")


@app.route("/runs")
@login_required
def page_runs():
    return render_template("runs.html")


@app.route("/runs/<int:exec_id>")
@login_required
def page_run_detail(exec_id):
    execution = db.get_execution(exec_id)
    if not execution:
        return render_template("run_detail.html", execution=None)
    return render_template("run_detail.html", execution=execution)


@app.route("/cases")
@login_required
def page_cases():
    return render_template("cases.html")


@app.route("/audit")
@permission_required("audit")
def page_audit():
    return render_template("audit.html")


@app.route("/users")
@permission_required("user_admin")
def page_users():
    return render_template("users.html")


@app.route("/ai-config")
@permission_required("ai_config")
def page_ai_config():
    return render_template("ai_config.html")


# ==============================
# API：看板
# ==============================
def _env_info() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "host": platform.node(),
        "version": "1.1.0",
    }


@app.route("/api/health")
def api_health():
    """服务健康检查（监控探活用，公开）：
    DB 连通/后端类型 + worker 节点 + 执行队列 + 最近执行 + 告警。"""
    from quality_platform.remote.dispatcher import workers_status
    from quality_platform.services.observability import check_alerts, db_health
    from quality_platform.services.test_executor import _load_distributed_workers
    try:
        alerts = check_alerts()
    except Exception:  # noqa: BLE001
        alerts = []
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(timespec="seconds"),
        "db": db_health(),
        "queue": executor.queue_status(),
        "workers": workers_status(_load_distributed_workers()),
        "latest_execution": db.list_executions(limit=1) or None,
        "alerts": alerts,
    })


@app.route("/api/metrics")
@login_required
def api_metrics():
    """执行指标：近 7 天趋势 + 累计指标（看板可观测性）。"""
    from quality_platform.services.observability import cumulative_stats, daily_stats
    return jsonify({
        "daily": daily_stats(7),
        "cumulative": cumulative_stats(),
    })


@app.route("/api/dashboard")
@login_required
def api_dashboard():
    runs = db.list_executions(limit=10)
    finished = [r for r in runs if r["status"] == "finished"]
    total_cases = sum(r["total"] for r in finished)
    total_passed = sum(r["passed"] for r in finished)
    pass_rate = round(total_passed / total_cases * 100, 1) if total_cases else 0.0
    avg_duration = (sum(r["duration"] or 0 for r in finished) / len(finished)) if finished else 0.0
    flaky_report = ai.detect_flaky()
    gate = evaluate_gate()
    score = quality_score()
    pyramid = test_pyramid()
    return jsonify({
        "executions": runs,
        "env": _env_info(),
        "user": _current_user(),
        "gate": gate,
        "quality_score": score,
        "pyramid": pyramid,
        "summary": {
            "total_cases": total_cases,
            "pass_rate": pass_rate,
            "avg_duration": round(avg_duration, 1),
            "flaky_count": flaky_report["summary"]["detected_flaky"],
            "stable_fail": flaky_report["summary"]["stable_fail"],
            "run_count": len(finished),
        },
        "trend": [
            {"id": r["id"], "test_path": r["test_path"], "total": r["total"],
             "passed": r["passed"], "failed": r["failed"],
             "pass_rate": round(r["passed"] / r["total"] * 100, 1) if r["total"] else 0,
             "started_at": r["started_at"], "duration": r["duration"]}
            for r in runs
        ],
    })


# ==============================
# API：执行
# ==============================
@app.route("/api/runs", methods=["GET"])
@login_required
def api_runs():
    return jsonify({"runs": db.list_executions(limit=50)})


@app.route("/api/runs", methods=["POST"])
@permission_required("run")
def api_run_start():
    data = request.get_json(silent=True) or {}
    test_path = (data.get("test_path") or "").strip()
    if not test_path:
        return jsonify({"error": "test_path 不能为空"}), 400
    workers = data.get("workers") or None
    if workers:
        workers = [str(w).strip() for w in workers if str(w).strip()]
        if not workers:
            workers = None
    exec_id = executor.run_async(
        test_path,
        reruns=int(data.get("reruns", 0) or 0),
        parallel=int(data.get("parallel", 0) or 0),
        timeout=int(data.get("timeout", 0) or 0),
        marker=(data.get("marker") or "").strip(),
        workers=workers,
    )
    _audit("run_start", target=str(exec_id), detail=f"{test_path} workers={workers or '本地'}")
    return jsonify({"execution_id": exec_id, "status": "running",
                    "mode": "distributed" if workers else "local"}), 202


@app.route("/api/workers")
@login_required
def api_workers():
    """分布式执行节点状态（配置的 worker 实时健康检查）。"""
    from quality_platform.remote.dispatcher import workers_status
    from quality_platform.services.test_executor import _load_distributed_workers
    urls = _load_distributed_workers()
    if not urls:
        return jsonify({"workers": [], "enabled": False,
                        "note": "未配置 distributed.workers（platform_config.yaml）"})
    return jsonify({"workers": workers_status(urls), "enabled": True})


@app.route("/api/runs/<int:exec_id>")
@login_required
def api_run_detail(exec_id):
    execution = db.get_execution(exec_id)
    if not execution:
        return jsonify({"error": "执行不存在"}), 404
    results = db.list_case_results(exec_id)
    return jsonify({"execution": execution, "cases": results})


@app.route("/api/runs/<int:exec_id>/cancel", methods=["POST"])
@admin_required
def api_run_cancel(exec_id):
    """取消执行（排队中移出队列；运行中终止子进程）。"""
    result = executor.cancel(exec_id)
    _audit("run_cancel", target=str(exec_id),
           detail=result.get("state", ""), ok=result.get("ok", False))
    return jsonify(result)


@app.route("/api/queue")
@login_required
def api_queue():
    """执行队列状态：并发上限/运行中/排队中/待取消。"""
    return jsonify(executor.queue_status())


# ==============================
# API：失败分析
# ==============================
@app.route("/api/failures")
@login_required
def api_failures():
    return jsonify({"failures": db.recent_failures(limit=100),
                    "clusters": cluster_failures()})


@app.route("/api/failures/clusters")
@login_required
def api_failures_clusters():
    return jsonify(cluster_failures())


@app.route("/api/failures/<int:case_result_id>")
@login_required
def api_failure_detail(case_result_id):
    case = db.get_case_result(case_result_id)
    if not case:
        return jsonify({"error": "失败记录不存在"}), 404
    case["analysis"] = db.get_analysis(case_result_id)
    return jsonify(case)


@app.route("/api/failures/<int:case_result_id>/analyze", methods=["POST"])
@login_required
def api_failures_analyze(case_result_id):
    result = ai.analyze_failure(case_result_id)
    return jsonify(result)


# ==============================
# API：flaky
# ==============================
@app.route("/api/flaky")
@login_required
def api_flaky():
    return jsonify(ai.detect_flaky())


# ==============================
# API：AI 配置（管理员维护密钥 / 本地模型）
# ==============================
@app.route("/api/ai/config")
@admin_required
def api_ai_config_get():
    """读取当前 AI 配置（api_key 脱敏返回）。"""
    from quality_platform.services import ai_config

    row = db.get_ai_settings()
    if not row:
        return jsonify({"configured": False, "presets": ai_config.PROVIDER_PRESETS,
                        "active": ai_config.get_active_config()})
    return jsonify({
        "configured": True,
        "settings": {
            "provider": row["provider"],
            "base_url": row["base_url"],
            "api_key_masked": ai_config.mask_key(ai_config.decrypt_key(row.get("api_key_enc") or "")),
            "model": row["model"],
            "enabled": bool(row["enabled"]),
        },
        "presets": ai_config.PROVIDER_PRESETS,
        "active": ai_config.get_active_config(),
    })


@app.route("/api/ai/config", methods=["PUT"])
@admin_required
def api_ai_config_put():
    """保存 AI 配置。api_key 传空表示不修改（保留原值）。"""
    from quality_platform.services import ai_config

    data = request.get_json(silent=True) or {}
    provider = (data.get("provider") or "").strip()
    base_url = (data.get("base_url") or "").strip().rstrip("/")
    model = (data.get("model") or "").strip()
    enabled = bool(data.get("enabled", True))
    if not provider or not base_url or not model:
        return jsonify({"error": "provider/base_url/model 均不能为空"}), 400

    existing = db.get_ai_settings()
    old_enc = (existing or {}).get("api_key_enc") or ""
    new_key = (data.get("api_key") or "").strip()
    if new_key:
        api_key_enc = ai_config.encrypt_key(new_key)
    else:
        api_key_enc = old_enc  # 未传新 key 则保留原密文

    cfg_id = db.save_ai_settings(provider, base_url, api_key_enc, model, enabled)
    _audit("ai_config_save", target=str(cfg_id),
           detail=f"{provider}/{model} enabled={enabled}", ok=True)
    return jsonify({"ok": True, "config_id": cfg_id,
                    "active": ai_config.get_active_config()})


@app.route("/api/ai/config/test", methods=["POST"])
@admin_required
def api_ai_config_test():
    """用提交的配置试连（不落库），返回连通结果。"""
    from quality_platform.services import ai_config

    data = request.get_json(silent=True) or {}
    base_url = (data.get("base_url") or "").strip().rstrip("/")
    api_key = (data.get("api_key") or "").strip()
    model = (data.get("model") or "").strip()
    if not base_url or not model:
        return jsonify({"error": "base_url/model 不能为空"}), 400
    # 试连时若未传 key，尝试用已保存配置的 key
    if not api_key:
        row = db.get_ai_settings()
        if row:
            api_key = ai_config.decrypt_key(row.get("api_key_enc") or "")
    _audit("ai_config_test", detail=f"{model} @ {base_url}")
    result = ai_config.test_connection(base_url, api_key, model)
    return jsonify(result)


# ==============================
# API：用例库管理（CRUD）
# ==============================
@app.route("/api/cases/manage", methods=["GET"])
@login_required
def api_cases_manage():
    module = request.args.get("module", "")
    keyword = request.args.get("keyword", "")
    return jsonify({"cases": db.list_cases(module=module, keyword=keyword)})


@app.route("/api/cases/manage", methods=["POST"])
@login_required
def api_cases_add():
    data = request.get_json(silent=True) or {}
    nodeid = (data.get("nodeid") or "").strip()
    if not nodeid:
        return jsonify({"error": "nodeid 不能为空"}), 400
    case_id = db.upsert_case(
        nodeid, name=data.get("name", ""), module=data.get("module", ""),
        tags=data.get("tags", ""), owner=data.get("owner", ""),
        description=data.get("description", ""),
        status=data.get("status", "active"),
    )
    _audit("case_add", target=str(case_id), detail=nodeid)
    return jsonify({"case_id": case_id}), 201


@app.route("/api/cases/<int:case_id>", methods=["PUT"])
@permission_required("case_edit")
def api_cases_update(case_id):
    data = request.get_json(silent=True) or {}
    ok = db.update_case(case_id, **data)
    _audit("case_update", target=str(case_id),
           detail=str(data.get("status", "")), ok=ok)
    return jsonify({"ok": ok})


@app.route("/api/cases/<int:case_id>", methods=["DELETE"])
@permission_required("case_edit")
def api_cases_delete(case_id):
    ok = db.delete_case(case_id)
    _audit("case_delete", target=str(case_id), ok=ok)
    return jsonify({"ok": ok})


@app.route("/api/cases/import", methods=["POST"])
@permission_required("case_edit")
def api_cases_import():
    """从 pytest collect 结果一键导入用例库。"""
    try:
        nodeids = _collect_test_nodeids(force=True)
        result = db.import_cases(nodeids)
        _audit("case_import", detail=f"新增{result['imported']}/更新{result['updated']}")
        return jsonify({"imported": result["imported"], "updated": result["updated"],
                        "total": len(nodeids)})
    except Exception as exc:
        import traceback as _tb
        _tb.print_exc()
        _audit("case_import", detail=str(exc)[:200], ok=False)
        return jsonify({"error": str(exc)}), 500


# ==============================
# API：用例清单（pytest 实时收集，带 TTL 缓存）
# ==============================
_COLLECT_TTL = 300  # 缓存 5 分钟，避免每次请求同步阻塞跑 pytest collect
_collect_cache: dict = {"ts": 0.0, "nodeids": []}


def _collect_test_nodeids(force: bool = False) -> list[str]:
    """运行 pytest --collect-only 收集用例 nodeid（结果缓存 _COLLECT_TTL 秒）。"""
    if not force and (time.time() - _collect_cache["ts"]) < _COLLECT_TTL:
        return _collect_cache["nodeids"]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "tests/test_smoke/", "tests/test_api/", "tests/test_whitebox/"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    nodeids = [ln for ln in proc.stdout.splitlines()
               if "::" in ln and not ln.startswith("no tests ran")]
    _collect_cache["ts"] = time.time()
    _collect_cache["nodeids"] = nodeids
    return nodeids


@app.route("/api/cases")
@login_required
def api_cases():
    try:
        lines = _collect_test_nodeids()
        return jsonify({"cases": lines[:1000], "count": len(lines)})
    except Exception as exc:
        return jsonify({"error": str(exc), "cases": []}), 500


# ==============================
# API：定时任务（nightly 回归）
# ==============================
@app.route("/api/schedules", methods=["GET"])
@login_required
def api_schedules():
    return jsonify({"schedules": scheduler.list()})


@app.route("/api/schedules", methods=["POST"])
@login_required
def api_schedules_add():
    data = request.get_json(silent=True) or {}
    kind = data.get("kind", "daily")
    if kind == "daily":
        sched_id = scheduler.add_daily(
            data.get("cron_value", "22:00"), data.get("test_path", ""),
            name=data.get("name", "每日回归"),
            reruns=int(data.get("reruns", 1) or 0),
            parallel=int(data.get("parallel", 0) or 0),
        )
    else:
        sched_id = scheduler.add_interval(
            float(data.get("cron_value", 6)), data.get("test_path", ""),
            name=data.get("name", "周期回归"),
            reruns=int(data.get("reruns", 1) or 0),
            parallel=int(data.get("parallel", 0) or 0),
        )
    _audit("sched_add", target=str(sched_id),
           detail=f"{kind} {data.get('cron_value', '')} {data.get('test_path', '')}")
    return jsonify({"schedule_id": sched_id}), 201


@app.route("/api/schedules/<int:sched_id>", methods=["DELETE"])
@admin_required
def api_schedules_delete(sched_id):
    scheduler.delete(sched_id)
    _audit("sched_delete", target=str(sched_id))
    return jsonify({"ok": True})


@app.route("/api/schedules/<int:sched_id>/toggle", methods=["POST"])
@admin_required
def api_schedules_toggle(sched_id):
    data = request.get_json(silent=True) or {}
    scheduler.toggle(sched_id, bool(data.get("enabled", True)))
    _audit("sched_toggle", target=str(sched_id),
           detail=f"enabled={bool(data.get('enabled', True))}")
    return jsonify({"ok": True})


# ==============================
# API：精准测试（变更影响面分析）
# ==============================
@app.route("/api/impact")
@login_required
def api_impact():
    """分析 git 变更 → 建议执行的测试集（精准测试，可解释：每个测试集附带选中原因）"""
    from quality_platform.services.impact_analysis import analyze_changes
    base = request.args.get("base", "HEAD~1")
    return jsonify(analyze_changes(base=base))


@app.route("/api/impact/run", methods=["POST"])
@admin_required
def api_impact_run():
    """按影响面分析结果一键执行建议测试集（admin）。"""
    from quality_platform.services.impact_analysis import analyze_changes
    report = analyze_changes(base=request.get_json(silent=True).get("base", "HEAD~1")
                             if request.get_json(silent=True) else "HEAD~1")
    targets = report["suggested_tests"]
    if not targets:
        return jsonify({"error": "无建议测试集（无变更或未收集到变更）"}), 400
    exec_ids = []
    for test_path in targets:
        exec_ids.append(executor.run_async(test_path, reruns=1))
    _audit("impact_run", detail=f"{len(exec_ids)} 个测试集：{','.join(targets)}")
    return jsonify({"execution_ids": exec_ids, "targets": targets}), 202


# ==============================
# API：审计日志（仅 admin）
# ==============================
@app.route("/api/audit")
@permission_required("audit")
def api_audit():
    """审计日志查询（admin/engineer：谁在什么时间对什么做了什么、成败）"""
    return jsonify({"logs": db.list_audit(
        limit=int(request.args.get("limit", 200) or 200),
        action=request.args.get("action", ""),
        username=request.args.get("username", ""),
    )})


@app.route("/api/users")
@permission_required("user_admin")
def api_users():
    """用户列表（RBAC 用户管理，仅 admin）。"""
    from quality_platform.models import list_users
    from quality_platform.services.rbac import role_label
    users = list_users()
    for u in users:
        u["role_label"] = role_label(u["role"])
    return jsonify({"users": users})


@app.route("/api/users/<int:user_id>/role", methods=["PUT"])
@permission_required("user_admin")
def api_user_update_role(user_id):
    """更新用户角色（RBAC，仅 admin；角色白名单 rbac.ROLES）。"""
    from quality_platform.models import update_user_role
    from quality_platform.services.rbac import ROLES
    role = (request.get_json(silent=True) or {}).get("role", "").strip().lower()
    if role not in ROLES:
        return jsonify({"error": f"角色必须为 {ROLES}"}), 400
    ok = update_user_role(user_id, role)
    _audit("user_role", target=str(user_id), detail=f"role={role}", ok=ok)
    return jsonify({"ok": ok})


# ==============================
# API：质量报告导出
# ==============================
@app.route("/api/report/export")
@login_required
def api_report_export():
    runs = db.list_executions(limit=50)
    gate = evaluate_gate()
    score = quality_score()
    pyramid = test_pyramid()
    return jsonify({
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "quality_score": score,
        "gate": gate,
        "pyramid": pyramid,
        "executions": runs,
        "failures": db.recent_failures(limit=100),
        "flaky": ai.detect_flaky(),
    })


# ==============================
# 启动
# ==============================
# 模块加载即初始化：import 模式（test_client / WSGI 加载）同样预置管理员，避免全新库无账号
ensure_admin()  # 幂等：预置默认管理员 admin/admin123（首次启动自动创建）


def main():
    db.init_db()
    ensure_admin()
    executor.recover_orphans()   # 启动恢复：回收上次进程退出遗留的僵尸 running 记录
    scheduler.start()
    port = int(os.getenv("PLATFORM_PORT", "8081"))
    print(f"质量工程平台已启动：http://127.0.0.1:{port}（admin / admin123）")
    # 优先 waitress（生产级 WSGI，Windows 友好）；未安装时降级 Flask 开发服务器
    try:
        from waitress import serve
        print("WSGI 服务器：waitress（生产级，4 线程）")
        serve(app, host="127.0.0.1", port=port, threads=4)
    except ImportError:
        print("[提示] 未安装 waitress，降级使用 Flask 开发服务器（生产环境请：pip install waitress）")
        app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
