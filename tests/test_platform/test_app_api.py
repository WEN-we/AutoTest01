"""平台 API 层单元测试：鉴权 / RBAC / 核心端点（Flask test client，全 mock）"""
import pytest

import quality_platform.app as app_mod
from quality_platform.app import app


@pytest.fixture
def client(monkeypatch):
    """测试客户端：mock 数据层与执行器，登录走假用户"""
    app.config["TESTING"] = True
    users = {
        "admin": {"id": 1, "username": "admin", "role": "admin"},
        "alice": {"id": 2, "username": "alice", "role": "user"},
    }

    def fake_verify_user(username, password):
        if password == "right-pw":
            return users.get(username)
        return None

    monkeypatch.setattr(app_mod, "verify_user", fake_verify_user)
    monkeypatch.setattr(app_mod.db, "list_executions", lambda limit=20: [])
    monkeypatch.setattr(app_mod.db, "get_execution", lambda i: None)
    monkeypatch.setattr(app_mod.db, "list_cases", lambda **k: [])
    monkeypatch.setattr(app_mod.db, "delete_case", lambda i: True)
    monkeypatch.setattr(app_mod.db, "update_case", lambda i, **f: True)
    monkeypatch.setattr(app_mod.executor, "run_async",
                        lambda *a, **k: 123)
    monkeypatch.setattr(app_mod.executor, "cancel",
                        lambda i: {"ok": True, "state": "cancelled_before_start"})
    monkeypatch.setattr(app_mod.executor, "queue_status",
                        lambda: {"max_workers": 2, "running": 0, "queued": 0,
                                 "cancelling": 0})
    monkeypatch.setattr(app_mod.scheduler, "list", lambda: [])
    with app.test_client() as c:
        yield c, users


def _login(client, username, password="right-pw"):
    return client.post("/api/login", json={"username": username,
                                           "password": password})


class TestAuth:
    def test_api_requires_login(self, client):
        c, _ = client
        resp = c.get("/api/runs")
        assert resp.status_code == 401

    def test_page_redirects_to_login(self, client):
        c, _ = client
        resp = c.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_login_success(self, client):
        c, users = client
        resp = _login(c, "alice")
        assert resp.status_code == 200
        assert resp.get_json()["user"]["role"] == "user"

    def test_login_wrong_password(self, client):
        c, _ = client
        resp = _login(c, "alice", password="wrong")
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        c, _ = client
        resp = _login(c, "ghost", password="right-pw")
        assert resp.status_code == 401

    def test_logout_clears_session(self, client):
        c, _ = client
        _login(c, "alice")
        assert c.get("/api/runs").status_code == 200
        c.post("/api/logout")
        assert c.get("/api/runs").status_code == 401


class TestRBAC:
    """user 角色只读 + 触发执行；删除/修改/取消类操作仅 admin"""

    def test_user_cannot_delete_case(self, client):
        c, _ = client
        _login(c, "alice")
        assert c.delete("/api/cases/1").status_code == 403

    def test_user_cannot_update_case(self, client):
        c, _ = client
        _login(c, "alice")
        resp = c.put("/api/cases/1", json={"name": "x"})
        assert resp.status_code == 403

    def test_user_cannot_cancel_run(self, client):
        c, _ = client
        _login(c, "alice")
        assert c.post("/api/runs/1/cancel").status_code == 403

    def test_user_cannot_import_cases(self, client):
        c, _ = client
        _login(c, "alice")
        assert c.post("/api/cases/import").status_code == 403

    def test_admin_can_delete_case(self, client):
        c, _ = client
        _login(c, "admin")
        resp = c.delete("/api/cases/1")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_admin_can_cancel_run(self, client):
        c, _ = client
        _login(c, "admin")
        resp = c.post("/api/runs/1/cancel")
        assert resp.status_code == 200
        assert resp.get_json()["state"] == "cancelled_before_start"

    def test_admin_required_before_login(self, client):
        """未登录直接访问 admin 接口 → 401（鉴权先于授权）"""
        c, _ = client
        assert c.delete("/api/cases/1").status_code == 401


class TestCoreEndpoints:
    def test_user_can_trigger_run(self, client):
        """普通用户可以触发执行（login_required 即可）"""
        c, _ = client
        _login(c, "alice")
        resp = c.post("/api/runs", json={"test_path": "tests/test_api/"})
        assert resp.status_code == 202
        assert resp.get_json()["execution_id"] == 123

    def test_login_failure_audited(self, client, monkeypatch):
        """登录失败也留审计痕（谁在尝试爆破）"""
        c, _ = client
        records = []
        monkeypatch.setattr(app_mod.db, "insert_audit",
                            lambda u, a, **k: records.append((u, a, k.get("ok", True))))
        c.post("/api/login", json={"username": "intruder", "password": "wrong"})
        assert records == [("intruder", "login", False)]

    def test_run_start_audited(self, client, monkeypatch):
        c, _ = client
        _login(c, "alice")
        records = []
        monkeypatch.setattr(app_mod.db, "insert_audit",
                            lambda u, a, **k: records.append((u, a)))
        c.post("/api/runs", json={"test_path": "tests/x/"})
        assert ("alice", "run_start") in records

    def test_cancel_audited(self, client, monkeypatch):
        c, _ = client
        _login(c, "admin")
        records = []
        monkeypatch.setattr(app_mod.db, "insert_audit",
                            lambda u, a, **k: records.append((u, a)))
        c.post("/api/runs/1/cancel")
        assert ("admin", "run_cancel") in records

    def test_case_delete_audited(self, client, monkeypatch):
        c, _ = client
        _login(c, "admin")
        records = []
        monkeypatch.setattr(app_mod.db, "insert_audit",
                            lambda u, a, **k: records.append((u, a)))
        c.delete("/api/cases/9")
        assert ("admin", "case_delete") in records


class TestAuditApi:
    """审计查询接口（admin 专属）"""

    def test_admin_can_query(self, client, monkeypatch):
        c, _ = client
        _login(c, "admin")
        monkeypatch.setattr(app_mod.db, "list_audit",
                            lambda **k: [{"id": 1, "username": "admin",
                                          "action": "login", "ok": 1}])
        resp = c.get("/api/audit")
        assert resp.status_code == 200
        assert resp.get_json()["logs"][0]["action"] == "login"

    def test_user_forbidden(self, client):
        c, _ = client
        _login(c, "alice")
        assert c.get("/api/audit").status_code == 403

    def test_page_requires_admin(self, client):
        c, _ = client
        _login(c, "alice")
        assert c.get("/audit").status_code == 403

    def test_run_requires_test_path(self, client):
        c, _ = client
        _login(c, "admin")
        resp = c.post("/api/runs", json={})
        assert resp.status_code == 400

    def test_queue_endpoint(self, client):
        c, _ = client
        _login(c, "alice")
        resp = c.get("/api/queue")
        assert resp.status_code == 200
        assert resp.get_json()["max_workers"] == 2

    def test_runs_list(self, client):
        c, _ = client
        _login(c, "alice")
        resp = c.get("/api/runs")
        assert resp.status_code == 200
        assert resp.get_json() == {"runs": []}

    def test_run_detail_not_found(self, client):
        c, _ = client
        _login(c, "admin")
        resp = c.get("/api/runs/999")
        assert resp.status_code == 404


class TestDashboardAndReports:
    """看板 / 失败分析 / 用例库 / 调度 / 报告导出（依赖服务全部 mock）"""

    @pytest.fixture
    def rich_client(self, client, monkeypatch):
        c, users = client
        empty_flaky = {"flaky": [], "stable_fail": [], "stable_pass": [],
                       "summary": {"detected_flaky": 0, "stable_fail": 0,
                                   "stable_pass": 0}}
        monkeypatch.setattr(app_mod.ai, "detect_flaky", lambda: empty_flaky)
        monkeypatch.setattr(app_mod, "evaluate_gate",
                            lambda: {"status": "PASS", "rules": [], "latest_run": None})
        monkeypatch.setattr(app_mod, "quality_score",
                            lambda: {"score": 95.0, "parts": {}})
        monkeypatch.setattr(app_mod, "test_pyramid",
                            lambda: {"distribution": {"api": 10}, "total": 10})
        monkeypatch.setattr(app_mod.db, "recent_failures", lambda limit=100: [])
        monkeypatch.setattr(app_mod, "cluster_failures",
                            lambda: {"clusters": [], "total_failures": 0,
                                     "root_causes": 0})
        monkeypatch.setattr(app_mod.db, "upsert_case", lambda *a, **k: 7)
        monkeypatch.setattr(app_mod.scheduler, "add_daily",
                            lambda *a, **k: 11)
        monkeypatch.setattr(app_mod.scheduler, "add_interval",
                            lambda *a, **k: 12)
        monkeypatch.setattr(app_mod.scheduler, "delete", lambda i: None)
        monkeypatch.setattr(app_mod.scheduler, "toggle", lambda i, e: None)
        _login(c, "admin")
        return c

    def test_dashboard_aggregates(self, rich_client):
        resp = rich_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["gate"]["status"] == "PASS"
        assert data["quality_score"]["score"] == 95.0
        assert data["pyramid"]["distribution"]["api"] == 10
        assert data["user"]["role"] == "admin"
        assert "executions" in data and "trend" in data

    def test_failures_list(self, rich_client):
        resp = rich_client.get("/api/failures")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["failures"] == []
        assert data["clusters"]["root_causes"] == 0

    def test_flaky_endpoint(self, rich_client):
        resp = rich_client.get("/api/flaky")
        assert resp.status_code == 200
        assert resp.get_json()["summary"]["detected_flaky"] == 0

    def test_cases_manage_add(self, rich_client):
        resp = rich_client.post("/api/cases/manage", json={"nodeid": "t::x"})
        assert resp.status_code == 201
        assert resp.get_json()["case_id"] == 7

    def test_cases_manage_add_requires_nodeid(self, rich_client):
        resp = rich_client.post("/api/cases/manage", json={})
        assert resp.status_code == 400

    def test_schedules_add_daily(self, rich_client):
        resp = rich_client.post("/api/schedules",
                                json={"kind": "daily", "cron_value": "22:00",
                                      "test_path": "tests/"})
        assert resp.status_code == 201
        assert resp.get_json()["schedule_id"] == 11

    def test_schedules_add_interval(self, rich_client):
        resp = rich_client.post("/api/schedules",
                                json={"kind": "interval", "cron_value": 6,
                                      "test_path": "tests/"})
        assert resp.status_code == 201
        assert resp.get_json()["schedule_id"] == 12

    def test_schedules_delete_and_toggle(self, rich_client):
        assert rich_client.delete("/api/schedules/3").status_code == 200
        resp = rich_client.post("/api/schedules/3/toggle", json={"enabled": False})
        assert resp.status_code == 200

    def test_report_export(self, rich_client):
        resp = rich_client.get("/api/report/export")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["quality_score"]["score"] == 95.0
        assert "exported_at" in data

    def test_pages_render(self, rich_client):
        for page in ("/", "/failures", "/runs", "/cases"):
            resp = rich_client.get(page)
            assert resp.status_code == 200, f"页面 {page} 渲染失败"

    def test_run_detail_page_missing(self, rich_client):
        """执行不存在时详情页优雅降级（而非 500）"""
        resp = rich_client.get("/runs/999")
        assert resp.status_code == 200
