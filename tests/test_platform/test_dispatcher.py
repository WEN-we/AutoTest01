"""分布式执行（远程 worker）单元测试：文件拆分 / JUnit 合并 / 节点降级。"""
import pytest

from quality_platform.remote import dispatcher


class TestListTestFiles:
    def test_dir_glob(self):
        files = dispatcher.list_test_files("tests/test_platform/")
        assert len(files) >= 5
        assert all(f.endswith("test_*.py") or f.endswith(".py") for f in files)
        assert any("test_models" in f for f in files)

    def test_single_file(self):
        files = dispatcher.list_test_files("tests/test_platform/test_models.py")
        assert files == ["tests/test_platform/test_models.py"]

    def test_missing_path(self):
        assert dispatcher.list_test_files("tests/no_such_dir_xyz/") == []


class TestParseJunitText:
    def test_parse_multiple_statuses(self):
        xml = """<?xml version="1.0"?>
        <testsuite>
          <testcase classname="a" name="ok" time="0.1"/>
          <testcase classname="a" name="bad" time="0.2">
            <failure type="AssertionError">assert 1 == 2</failure>
          </testcase>
          <testcase classname="a" name="err" time="0.3">
            <error type="RuntimeError">boom</error>
          </testcase>
          <testcase classname="a" name="skip" time="0.0">
            <skipped/>
          </testcase>
        </testsuite>"""
        r = dispatcher.parse_junit_text(xml)
        assert len(r) == 4
        by = {x["nodeid"].split("::")[-1]: x["status"] for x in r}
        assert by == {"ok": "passed", "bad": "failed", "err": "error", "skip": "skipped"}
        fail = next(x for x in r if x["status"] == "failed")
        assert fail["error_type"] == "AssertionError"

    def test_empty(self):
        assert dispatcher.parse_junit_text("") == []


class TestWorkerHealth:
    def test_unreachable_worker(self):
        """不可达节点 -> check_worker False -> run_distributed 降级本地。"""
        assert dispatcher.check_worker("http://127.0.0.1:1", timeout=1) is False

    def test_run_distributed_no_workers(self):
        """无可用节点 -> fallback_local=True（由主控走本地执行兜底）。"""
        out = dispatcher.run_distributed("tests/test_platform/test_models.py",
                                         ["http://127.0.0.1:1"], timeout_total=5)
        assert out["fallback_local"] is True
        assert out["results"] == []

    def test_workers_status_unreachable(self):
        st = dispatcher.workers_status(["http://127.0.0.1:1"])
        assert st[0]["ok"] is False
