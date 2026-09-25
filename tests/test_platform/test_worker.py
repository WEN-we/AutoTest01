"""远程执行节点（worker.py）单元测试：健康检查 + 任务执行端点。

通过 Flask test_client 直接测端点；subprocess 用 monkeypatch 替换（不真跑 pytest）。
"""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from quality_platform.remote import worker


@pytest.fixture
def client():
    worker.app.config["TESTING"] = True
    worker.app.config["WORKER_NAME"] = "worker-test"
    worker.app.config["PORT"] = 9199
    with worker.app.test_client() as c:
        yield c


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert d["name"] == "worker-test"
        assert d["host"].endswith("9199")
        assert d["status"] in ("idle", "busy")

    def test_config_defaults_present(self):
        """模块级默认配置存在（WSGI 直接加载 worker:app 时 /health 不 KeyError）。"""
        assert worker.app.config.get("WORKER_NAME")
        assert worker.app.config.get("PORT")
        # 模拟 WSGI 场景：用全新 app 上下文渲染 health（依赖默认配置）
        with worker.app.test_request_context("/health"):
            resp = worker.health()
            assert resp.status_code == 200


class TestRunJob:
    def test_empty_paths_400(self, client):
        r = client.post("/run", json={"test_paths": []})
        assert r.status_code == 400
        assert "test_paths" in r.get_json()["error"]

    def test_run_success_returns_junit(self, client, monkeypatch):
        """正常执行：回传 junit_xml + exit_code。"""
        def fake_run(cmd, **kwargs):
            # 写入 junit 文件（模拟 pytest 产出）
            junit_arg = [c for c in cmd if str(c).startswith("--junitxml=")][0]
            Path(junit_arg.split("=", 1)[1]).write_text(
                '<?xml version="1.0"?><testsuite><testcase classname="a" name="t" time="0.1"/></testsuite>',
                encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="1 passed", stderr="")

        monkeypatch.setattr(worker.subprocess, "run", fake_run)
        r = client.post("/run", json={"test_paths": ["tests/test_platform/test_models.py"],
                                      "reruns": 1, "timeout": 60, "marker": "smoke"})
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True and d["exit_code"] == 0
        assert "<testcase" in d["junit_xml"]

    def test_run_timeout_504(self, client, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=1)

        monkeypatch.setattr(worker.subprocess, "run", fake_run)
        r = client.post("/run", json={"test_paths": ["tests/x.py"]})
        assert r.status_code == 504
        assert "超时" in r.get_json()["error"]

    def test_run_exception_500(self, client, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise OSError("pytest 启动失败")

        monkeypatch.setattr(worker.subprocess, "run", fake_run)
        r = client.post("/run", json={"test_paths": ["tests/x.py"]})
        assert r.status_code == 500
        assert "pytest 启动失败" in r.get_json()["error"]

    def test_run_without_junit_file_returns_empty_xml(self, client, monkeypatch):
        """pytest 未产出 junit 时返回空字符串（主控按 0 结果处理，不崩）。"""
        monkeypatch.setattr(worker.subprocess, "run",
                            lambda cmd, **k: SimpleNamespace(returncode=4, stdout="", stderr="err"))
        r = client.post("/run", json={"test_paths": ["tests/x.py"]})
        assert r.status_code == 200
        assert r.get_json()["junit_xml"] == ""

    def test_busy_flag_reset_after_job(self, client, monkeypatch):
        """任务结束后 busy 复位（否则 /health 永远显示 busy）。"""
        monkeypatch.setattr(worker.subprocess, "run",
                            lambda cmd, **k: SimpleNamespace(returncode=0, stdout="", stderr=""))
        client.post("/run", json={"test_paths": ["tests/x.py"]})
        assert client.get("/health").get_json()["status"] == "idle"

    def test_jobs_done_counter(self, client, monkeypatch):
        monkeypatch.setattr(worker.subprocess, "run",
                            lambda cmd, **k: SimpleNamespace(returncode=0, stdout="", stderr=""))
        before = client.get("/health").get_json()["jobs_done"]
        client.post("/run", json={"test_paths": ["tests/x.py"]})
        assert client.get("/health").get_json()["jobs_done"] == before + 1
