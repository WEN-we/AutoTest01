"""
质量工程平台（Quality Platform）—— Flask 入口

大厂测开形态落地：质量看板 + 失败分析（AI 归因）+ 一键执行（参数化）+ flaky 治理 + 定时回归

启动：
    python -m quality_platform.app        # 默认 127.0.0.1:8081（注意：用 -m 模块方式，勿直接跑文件）
页面：
    /             质量看板（通过率 / flaky 率 / 执行趋势 / 环境信息）
    /failures     失败分析（截图 + AI 归因）
    /runs         执行历史 + 触发新执行（并发/重试/超时参数）
    /runs/<id>    执行详情（用例级结果）
    /cases        用例清单（pytest 收集）
API：
    GET  /api/dashboard                         看板聚合（含环境信息）
    GET  /api/runs                              执行历史
    POST /api/runs {"test_path","reruns","parallel","timeout","marker"}   触发执行
    GET  /api/runs/<id>                         执行详情（用例结果）
    GET  /api/failures                          最近失败
    GET  /api/failures/<id>                     单条失败详情（含 AI 归因）
    POST /api/failures/<id>/analyze             AI 归因单个失败
    GET  /api/flaky                             flaky 识别
    GET  /api/cases                             用例收集清单
    GET  /api/schedules                         定时任务列表
    POST /api/schedules                         新建定时任务
    DELETE /api/schedules/<id>                  删除定时任务
    POST /api/schedules/<id>/toggle             启停定时任务
"""
import os
import platform
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from quality_platform.models import db
from quality_platform.services.ai_integration import ai
from quality_platform.services.failure_clustering import cluster_failures
from quality_platform.services.gate import evaluate_gate, quality_score, test_pyramid
from quality_platform.services.scheduler import scheduler
from quality_platform.services.test_executor import executor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLATFORM_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder=str(PLATFORM_DIR / "templates"),
            static_folder=str(PLATFORM_DIR / "static"))


# ==============================
# 页面
# ==============================
@app.route("/")
def page_dashboard():
    return render_template("dashboard.html")


@app.route("/failures")
def page_failures():
    return render_template("failures.html")


@app.route("/runs")
def page_runs():
    return render_template("runs.html")


@app.route("/runs/<int:exec_id>")
def page_run_detail(exec_id):
    execution = db.get_execution(exec_id)
    if not execution:
        return render_template("run_detail.html", execution=None)
    return render_template("run_detail.html", execution=execution)


@app.route("/cases")
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
        "pytest_workers": executor.__class__.__name__,
        "version": "1.0.0",
    }


@app.route("/api/dashboard")
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
def api_runs():
    return jsonify({"runs": db.list_executions(limit=50)})


@app.route("/api/runs", methods=["POST"])
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
def api_failures():
    return jsonify({"failures": db.recent_failures(limit=100),
                    "clusters": cluster_failures()})


@app.route("/api/failures/clusters")
def api_failures_clusters():
    return jsonify(cluster_failures())


@app.route("/api/failures/<int:case_result_id>")
def api_failure_detail(case_result_id):
    for f in db.recent_failures(500):
        if f["id"] == case_result_id:
            f["analysis"] = db.get_analysis(case_result_id)
            return jsonify(f)
    return jsonify({"error": "失败记录不存在"}), 404


@app.route("/api/failures/<int:case_result_id>/analyze", methods=["POST"])
def api_failures_analyze(case_result_id):
    result = ai.analyze_failure(case_result_id)
    return jsonify(result)


# ==============================
# API：flaky
# ==============================
@app.route("/api/flaky")
def api_flaky():
    return jsonify(ai.detect_flaky())


# ==============================
# API：质量报告导出（大厂一键导出）
# ==============================
@app.route("/api/report/export")
def api_report_export():
    runs = db.list_executions(limit=50)
    gate = evaluate_gate()
    score = quality_score()
    pyramid = test_pyramid()
    return jsonify({
        "exported_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "quality_score": score,
        "gate": gate,
        "pyramid": pyramid,
        "executions": runs,
        "failures": db.recent_failures(limit=100),
        "flaky": ai.detect_flaky(),
    })


# ==============================
# API：用例清单（pytest 收集）
# ==============================
@app.route("/api/cases")
def api_cases():
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
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
def api_schedules():
    return jsonify({"schedules": scheduler.list()})


@app.route("/api/schedules", methods=["POST"])
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
def api_schedules_delete(sched_id):
    scheduler.delete(sched_id)
    return jsonify({"ok": True})


@app.route("/api/schedules/<int:sched_id>/toggle", methods=["POST"])
def api_schedules_toggle(sched_id):
    data = request.get_json(silent=True) or {}
    scheduler.toggle(sched_id, bool(data.get("enabled", True)))
    return jsonify({"ok": True})


# ==============================
# 启动
# ==============================
def main():
    db.init_db()
    scheduler.start()
    port = int(os.getenv("PLATFORM_PORT", "8081"))
    print(f"质量工程平台已启动：http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
