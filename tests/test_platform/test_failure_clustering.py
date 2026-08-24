"""失败指纹聚类单元测试（mock 数据层）"""
from quality_platform.models import db
from quality_platform.services.failure_clustering import cluster_failures


def _failure(fid, nodeid, error_type, message, exec_time="2026-08-22 10:00:00"):
    return {"id": fid, "nodeid": nodeid, "error_type": error_type,
            "error_message": message, "exec_time": exec_time}


def _mock_failures(monkeypatch, failures):
    monkeypatch.setattr(db, "recent_failures", lambda limit=200: failures)


class TestClusterFailures:
    def test_same_root_cause_merged(self, monkeypatch):
        """同错误类型 + 同指纹 → 归为一个簇"""
        _mock_failures(monkeypatch, [
            _failure(1, "t::a", "TimeoutError", "Timeout after 30s when clicking #btn"),
            _failure(2, "t::b", "TimeoutError", "Timeout after 30s when clicking #btn"),
            _failure(3, "t::c", "TimeoutError", "Timeout after 30s when clicking #btn"),
        ])
        result = cluster_failures()
        assert result["total_failures"] == 3
        assert result["root_causes"] == 1
        assert result["clusters"][0]["count"] == 3
        assert set(result["clusters"][0]["case_ids"]) == {1, 2, 3}

    def test_numbers_normalized_same_cluster(self, monkeypatch):
        """错误信息中的数字差异不拆簇（同根因）"""
        _mock_failures(monkeypatch, [
            _failure(1, "t::a", "TimeoutError", "wait 30 seconds for locator #user"),
            _failure(2, "t::b", "TimeoutError", "wait 45 seconds for locator #user"),
        ])
        result = cluster_failures()
        assert result["root_causes"] == 1

    def test_hex_normalized(self, monkeypatch):
        """长 hex（内存地址/请求ID）差异不拆簇"""
        _mock_failures(monkeypatch, [
            _failure(1, "t::a", "Error", "session 0x7f3a1b2c4d5e expired"),
            _failure(2, "t::b", "Error", "session 0x7f9c8b7a6d5e expired"),
        ])
        assert cluster_failures()["root_causes"] == 1

    def test_different_type_split(self, monkeypatch):
        """不同错误类型 → 不同簇"""
        _mock_failures(monkeypatch, [
            _failure(1, "t::a", "TimeoutError", "same message"),
            _failure(2, "t::b", "AssertionError", "same message"),
        ])
        result = cluster_failures()
        assert result["root_causes"] == 2

    def test_clusters_sorted_by_impact(self, monkeypatch):
        """按影响面（count）降序"""
        _mock_failures(monkeypatch, [
            _failure(1, "t::a", "TimeoutError", "timeout x"),
            _failure(2, "t::b", "TimeoutError", "timeout x"),
            _failure(3, "t::c", "AssertionError", "assert y"),
        ])
        clusters = cluster_failures()["clusters"]
        counts = [c["count"] for c in clusters]
        assert counts == sorted(counts, reverse=True)
        assert clusters[0]["error_type"] == "TimeoutError"

    def test_empty_failures(self, monkeypatch):
        _mock_failures(monkeypatch, [])
        result = cluster_failures()
        assert result == {"clusters": [], "total_failures": 0, "root_causes": 0}

    def test_missing_error_fields(self, monkeypatch):
        """无错误类型/信息 → 不崩溃，归入 Unknown 簇"""
        _mock_failures(monkeypatch, [
            {"id": 1, "nodeid": "t::a", "exec_time": "2026-08-22 10:00:00"},
        ])
        result = cluster_failures()
        assert result["root_causes"] == 1
        assert result["clusters"][0]["error_type"] == "Unknown"
        assert result["clusters"][0]["fingerprint"] == "(无错误信息)"
