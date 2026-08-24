"""TestExecutor 单元测试：命令构建 / JUnit 解析 / 队列与取消治理"""
import sys
import time
from pathlib import Path

import pytest

from quality_platform.models import db
# 别名避免 pytest 把 Test* 类误收集为测试类
from quality_platform.services.test_executor import TestExecutor as PytestExecutor


@pytest.fixture
def executor_factory(monkeypatch):
    """创建不落库的执行器（db 全部打桩）"""
    ids = iter(range(1, 10000))
    monkeypatch.setattr(db, "insert_execution", lambda p: next(ids))
    monkeypatch.setattr(db, "finish_execution", lambda *a, **k: None)
    monkeypatch.setattr(db, "insert_case_result", lambda *a, **k: None)

    def make(**kwargs):
        ex = PytestExecutor(**kwargs)
        monkeypatch.setattr(ex, "_mark_status", lambda *a, **k: None)
        return ex

    return make


class TestBuildCommand:
    def test_basic_command(self, executor_factory):
        ex = executor_factory()
        cmd = ex._build_command("tests/test_api/", 0, 0, 0, "", Path("j.xml"))
        assert cmd[1:3] == ["-m", "pytest"]
        assert "tests/test_api/" in cmd
        assert "--junitxml=j.xml" in cmd

    def test_all_options(self, executor_factory):
        ex = executor_factory()
        cmd = ex._build_command("tests/x/", reruns=2, parallel=4,
                                timeout=30, marker="smoke", junit_file=Path("j.xml"))
        assert "--reruns=2" in cmd
        assert "--reruns-delay=1" in cmd
        assert "-n4" in cmd
        assert "--timeout=30" in cmd
        # marker 过滤：最后一个 -m 的参数是 smoke（第一个 -m 是 pytest 模块标志）
        assert cmd[-2:] == ["-m", "smoke"]

    def test_zero_options_omitted(self, executor_factory):
        ex = executor_factory()
        cmd = ex._build_command("tests/x/", 0, 0, 0, "", Path("j.xml"))
        assert not any(c.startswith("--reruns") for c in cmd)
        assert not any(c.startswith("-n") for c in cmd)
        assert "--timeout=0" not in cmd


_JUNIT_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="4" failures="1" errors="1" skipped="1">
  <testcase classname="tests.test_api.test_user" name="test_ok" time="0.1"/>
  <testcase classname="tests.test_api.test_user" name="test_fail" time="0.2">
    <failure type="AssertionError">assert 1 == 2</failure>
  </testcase>
  <testcase classname="tests.test_api.test_user" name="test_error" time="0.3">
    <error type="ImportError">cannot import foo</error>
  </testcase>
  <testcase classname="tests.test_api.test_user" name="test_skip" time="0.0">
    <skipped type="pytest.skip" message="no env"/>
  </testcase>
</testsuite>
"""


class TestParseJunit:
    def test_parse_all_statuses(self, executor_factory, tmp_path):
        xml = tmp_path / "junit.xml"
        xml.write_text(_JUNIT_XML, encoding="utf-8")
        results = PytestExecutor()._parse_junit(xml)

        assert len(results) == 4
        by_name = {r["nodeid"].split("::")[-1]: r for r in results}
        assert by_name["test_ok"]["status"] == "passed"
        assert by_name["test_fail"]["status"] == "failed"
        assert by_name["test_fail"]["error_type"] == "AssertionError"
        assert "assert 1 == 2" in by_name["test_fail"]["error_message"]
        assert by_name["test_error"]["status"] == "error"
        assert by_name["test_skip"]["status"] == "skipped"

    def test_nodeid_from_classname_and_name(self, executor_factory, tmp_path):
        xml = tmp_path / "junit.xml"
        xml.write_text(_JUNIT_XML, encoding="utf-8")
        results = PytestExecutor()._parse_junit(xml)
        assert results[0]["nodeid"] == "tests.test_api.test_user::test_ok"


class TestQueueAndCancel:
    def test_queue_status_empty(self, executor_factory):
        status = executor_factory(max_workers=2).queue_status()
        assert status == {"max_workers": 2, "running": 0, "queued": 0, "cancelling": 0}

    def test_concurrency_limit_one_running(self, executor_factory, monkeypatch):
        """max_workers=1：第二个任务必须排队"""
        ex = executor_factory(max_workers=1)
        release = {"flag": False}

        def fake_run(*args, **kwargs):
            while not release["flag"]:
                time.sleep(0.05)

        monkeypatch.setattr(ex, "_run", fake_run)
        try:
            ex.run_async("tests/a/")
            ex.run_async("tests/b/")
            time.sleep(0.3)  # 等第一个任务真正跑起来
            status = ex.queue_status()
            assert status["running"] == 1
            assert status["queued"] == 1
        finally:
            release["flag"] = True
            ex._pool.shutdown(wait=True)

    def test_cancel_queued_task(self, executor_factory, monkeypatch):
        """取消排队中任务：直接出队，返回 cancelled_before_start"""
        ex = executor_factory(max_workers=1)
        release = {"flag": False}

        def fake_run(*args, **kwargs):
            while not release["flag"]:
                time.sleep(0.05)

        monkeypatch.setattr(ex, "_run", fake_run)
        try:
            ex.run_async("tests/a/")          # 占住唯一 worker
            exec_id2 = ex.run_async("tests/b/")  # 排队
            result = ex.cancel(exec_id2)
            assert result["ok"] is True
            assert result["state"] == "cancelled_before_start"
        finally:
            release["flag"] = True
            ex._pool.shutdown(wait=True)

    def test_cancel_unknown_task(self, executor_factory):
        ex = executor_factory()
        try:
            result = ex.cancel(99999)
            assert result["ok"] is False
        finally:
            ex._pool.shutdown(wait=True)


class TestSubprocessGovernance:
    def test_timeout_kills_subprocess(self, executor_factory):
        """整体超时 → kill 子进程并返回 timed_out"""
        ex = executor_factory()
        ex.default_timeout = 1
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        cancelled, timed_out, _ = ex._run_subprocess(cmd, env=None, exec_id=1,
                                                     poll_seconds=0.5)
        assert cancelled is False
        assert timed_out is True

    def test_cancel_kills_running_subprocess(self, executor_factory):
        """运行中取消 → kill 子进程并返回 cancelled"""
        ex = executor_factory()
        ex._cancels.add(1)
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        cancelled, timed_out, _ = ex._run_subprocess(cmd, env=None, exec_id=1,
                                                     poll_seconds=0.5)
        assert cancelled is True
        assert timed_out is False

    def test_normal_completion(self, executor_factory):
        """正常结束：不取消不超时"""
        ex = executor_factory()
        ex.default_timeout = 10
        cmd = [sys.executable, "-c", "print('hello')"]
        cancelled, timed_out, (out, _) = ex._run_subprocess(cmd, env=None, exec_id=1,
                                                            poll_seconds=0.5)
        assert cancelled is False
        assert timed_out is False
        assert "hello" in out


class TestAutoAnalyze:
    """执行完成 → 失败用例自动 AI 归因（智能闭环）"""

    @pytest.fixture
    def analyzer_env(self, executor_factory, monkeypatch):
        """构造带失败记录的执行 + 可观测的归因调用"""
        ex = executor_factory()
        rows = [
            {"id": 1, "nodeid": "t::f1", "status": "failed"},
            {"id": 2, "nodeid": "t::f2", "status": "error"},
            {"id": 3, "nodeid": "t::p", "status": "passed"},
        ]
        monkeypatch.setattr(db, "list_case_results", lambda exec_id: rows)
        calls = []
        monkeypatch.setattr("quality_platform.services.ai_integration.ai.analyze_failure",
                            lambda cid: calls.append(cid) or {"category": "x"})
        return ex, calls

    def test_analyzes_failed_cases(self, analyzer_env, monkeypatch):
        monkeypatch.setattr("quality_platform.services.test_executor._load_auto_analysis_cfg",
                            lambda: {"enabled": True, "max_cases": 10})
        ex, calls = analyzer_env
        ex._auto_analyze(1)
        assert calls == [1, 2]  # 只分析 failed/error，跳过 passed

    def test_max_cases_limit(self, analyzer_env, monkeypatch):
        monkeypatch.setattr("quality_platform.services.test_executor._load_auto_analysis_cfg",
                            lambda: {"enabled": True, "max_cases": 1})
        ex, calls = analyzer_env
        ex._auto_analyze(1)
        assert calls == [1]  # 成本控制：只分析第一条

    def test_disabled_skips(self, analyzer_env, monkeypatch):
        monkeypatch.setattr("quality_platform.services.test_executor._load_auto_analysis_cfg",
                            lambda: {"enabled": False})
        ex, calls = analyzer_env
        ex._auto_analyze(1)
        assert calls == []

    def test_analyzer_exception_not_raise(self, executor_factory, monkeypatch):
        """归因服务异常不影响执行主流程"""
        ex = executor_factory()
        monkeypatch.setattr("quality_platform.services.test_executor._load_auto_analysis_cfg",
                            lambda: {"enabled": True, "max_cases": 10})
        monkeypatch.setattr(db, "list_case_results",
                            lambda exec_id: (_ for _ in ()).throw(RuntimeError("db down")))
        ex._auto_analyze(1)  # 不抛异常即通过


class TestRecoverOrphans:
    """启动恢复：服务重启后回收僵尸 running 记录（浏览器实测发现的真 bug）"""

    def test_marks_zombies_and_returns_count(self, executor_factory, monkeypatch):
        class FakeCursor:
            rowcount = 3

        captured = {}

        class FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, sql, params=()):
                captured["sql"] = sql
                return FakeCursor()

        monkeypatch.setattr(db, "_conn", lambda: FakeConn())
        ex = executor_factory()
        assert ex.recover_orphans() == 3
        assert "status='interrupted'" in captured["sql"]
        assert "status='running'" in captured["sql"]

    def test_recover_db_error_returns_zero(self, executor_factory, monkeypatch):
        """恢复逻辑异常不影响启动（返回 0 不抛）"""

        class BrokenConn:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, sql, params=()):
                raise RuntimeError("db locked")

        monkeypatch.setattr(db, "_conn", lambda: BrokenConn())
        ex = executor_factory()
        assert ex.recover_orphans() == 0

