"""远程执行节点（分布式 worker 雏形）。

独立进程运行：`python -m quality_platform.remote.worker --port 9101`
- 主控（dispatcher）按文件粒度把用例集分发到多个 worker 并行执行
- 本节点仅负责：接收任务 -> 跑 pytest -> 回传 JUnit XML + 退出码（不落平台库，保持无状态）
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request

from utils.tools.logger import log

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

app = Flask(__name__)
_status = {"busy": False, "jobs_done": 0, "last_error": ""}


@app.get("/health")
def health():
    """健康检查：主控据此剔除不可用节点。"""
    return jsonify({
        "ok": True,
        "name": app.config["WORKER_NAME"],
        "host": f"127.0.0.1:{app.config['PORT']}",
        "status": "busy" if _status["busy"] else "idle",
        "jobs_done": _status["jobs_done"],
    })


@app.post("/run")
def run_job():
    """执行分发的测试任务（test_paths 为文件列表），回传 JUnit XML。"""
    data = request.get_json(silent=True) or {}
    test_paths = data.get("test_paths") or []
    if not test_paths:
        return jsonify({"ok": False, "error": "test_paths 不能为空"}), 400

    _status["busy"] = True
    started = time.time()
    try:
        junit = PROJECT_ROOT / "reports" / "platform" / f"remote_junit_{time.time_ns()}.xml"
        junit.parent.mkdir(parents=True, exist_ok=True)

        cmd = [sys.executable, "-m", "pytest", *test_paths,
               f"--junitxml={junit}", "-q"]
        if int(data.get("reruns", 0) or 0) > 0:
            cmd += [f"--reruns={int(data['reruns'])}", "--reruns-delay=1"]
        if int(data.get("parallel", 0) or 0) > 1:
            cmd += [f"-n{int(data['parallel'])}", "--dist=loadscope"]
        if int(data.get("timeout", 0) or 0) > 0:
            cmd += [f"--timeout={int(data['timeout'])}"]
        if data.get("marker"):
            cmd += ["-m", data["marker"]]

        log.info(f"[worker {app.config['WORKER_NAME']}] 执行：{' '.join(cmd)}")
        proc = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=int(data.get("timeout_total", 1800)),
        )
        junit_xml = junit.read_text(encoding="utf-8", errors="replace") if junit.exists() else ""
        _status["jobs_done"] += 1
        return jsonify({
            "ok": True,
            "exit_code": proc.returncode,
            "junit_xml": junit_xml,
            "duration": round(time.time() - started, 2),
            "error": (proc.stderr or "")[-2000:],
        })
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "worker 执行超时", "junit_xml": ""}), 504
    except Exception as exc:  # noqa: BLE001
        _status["last_error"] = str(exc)
        return jsonify({"ok": False, "error": str(exc)[:500], "junit_xml": ""}), 500
    finally:
        _status["busy"] = False


def main():
    parser = argparse.ArgumentParser(description="质量平台远程执行节点")
    parser.add_argument("--port", type=int, default=9101)
    parser.add_argument("--name", default="")
    args = parser.parse_args()
    app.config["PORT"] = args.port
    app.config["WORKER_NAME"] = args.name or f"worker-{args.port}"
    print(f"[worker] {app.config['WORKER_NAME']} 启动：http://127.0.0.1:{args.port}"
          f"（{sys.executable}）")
    try:
        from waitress import serve
        serve(app, host="127.0.0.1", port=args.port, threads=4)
    except ImportError:
        app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
