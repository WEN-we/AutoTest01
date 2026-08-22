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
    GET/POST/DELETE /api/cases/manage · PUT/DELETE /api/cases/<id> · POST /api/cases/import
    GET/POST /api/schedules · DELETE /api/schedules/<id> · POST /api/schedules/<id>/toggle
    GET  /api/report/export
"""
import os
import platform
import subprocess
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from quality_platform.models import db, ensure_admin, verify_user
from quality_platform.services.ai_integration import ai
from quality_platform.services.failure_clustering import cluster_failures
from quality_platform.services.gate import evaluate_gate, quality_score, test_pyramid
from quality_platform.services.scheduler import scheduler
from quality_platform.services.test_executor import executor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLATFORM_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(PLATFORM_DIR / "templates"),
            static_folder=str(PLATFORM_DIR / "static"))
app.secret_key = os.getenv("PLATFORM_SECRET", "quality-platform-dev-secret-change-me")


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
        return jsonify({"error": "用户名或密码错误"}), 401
    session["user"] = {"id": user["id"], "username": user["username"],
                       "role": user["role"]}
    return jsonify({"ok": True, "user": session["user"]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


def _current_user() -> dict:
    return session.get("user", {})


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
@login_required
def api_run_start():
    data = request.get_json(silent=True) or {}
    test_path = (data.get("test_path") or "").strip()
    if not test_path:
        return jsonify({"error": "test_path 不能为空"}), 400
    exec_id = executor.run_async(
        test_path,
        reruns=int(data.get("reruns", 0) or 0),
        parallel=int(data.get("parallel", 0) or 0),
        timeout=int(data.get("timeout", 0) or 0),
        marker=(data.get("marker") or "").strip(),
    )
    return jsonify({"execution_id": exec_id, "status": "running"}), 202


@app.route("/api/runs/<int:exec_id>")
@login_required
def api_run_detail(exec_id):
    execution = db.get_execution(exec_id)
    if not execution:
        return jsonify({"error": "执行不存在"}), 404
    results = db.list_case_results(exec_id)
    return jsonify({"execution": execution, "cases": results})


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
    for f in db.recent_failures(500):
        if f["id"] == case_result_id:
            f["analysis"] = db.get_analysis(case_result_id)
            return jsonify(f)
    return jsonify({"error": "失败记录不存在"}), 404


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
    return jsonify({"case_id": case_id}), 201


@app.route("/api/cases/<int:case_id>", methods=["PUT"])
@login_required
def api_cases_update(case_id):
    data = request.get_json(silent=True) or {}
    ok = db.update_case(case_id, **data)
    return jsonify({"ok": ok})


@app.route("/api/cases/<int:case_id>", methods=["DELETE"])
@login_required
def api_cases_delete(case_id):
    ok = db.delete_case(case_id)
    return jsonify({"ok": ok})


@app.route("/api/cases/import", methods=["POST"])
@login_required
def api_cases_import():
    """从 pytest collect 结果一键导入用例库。"""
    try:
        from utils.tools.logger import log as _log
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_smoke/", "tests/test_api/", "tests/test_whitebox/"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
        _log.info(f"[平台] collect 完成：rc={proc.returncode} stdout={len(proc.stdout)} 字符")
        nodeids = [ln for ln in proc.stdout.splitlines()
                   if "::" in ln and not ln.startswith("no tests ran")]
        result = db.import_cases(nodeids)
        return jsonify({"imported": result["imported"], "updated": result["updated"],
                        "total": len(nodeids)})
    except Exception as exc:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({"error": str(exc)}), 500


# ==============================
# API：用例清单（pytest 实时收集）
# ==============================
@app.route("/api/cases")
@login_required
def api_cases():
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_smoke/", "tests/test_api/", "tests/test_whitebox/"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        lines = [ln for ln in proc.stdout.splitlines()
                 if "::" in ln and not ln.startswith("no tests ran")]
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
    return jsonify({"schedule_id": sched_id}), 201


@app.route("/api/schedules/<int:sched_id>", methods=["DELETE"])
@login_required
def api_schedules_delete(sched_id):
    scheduler.delete(sched_id)
    return jsonify({"ok": True})


@app.route("/api/schedules/<int:sched_id>/toggle", methods=["POST"])
@login_required
def api_schedules_toggle(sched_id):
    data = request.get_json(silent=True) or {}
    scheduler.toggle(sched_id, bool(data.get("enabled", True)))
    return jsonify({"ok": True})


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
def main():
    db.init_db()
    ensure_admin()
    scheduler.start()
    port = int(os.getenv("PLATFORM_PORT", "8081"))
    print(f"质量工程平台已启动：http://127.0.0.1:{port}（admin / admin123）")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
