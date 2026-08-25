"""细粒度 RBAC 单元测试：权限矩阵 + API 访问控制 + SSO 角色登录。"""
import pytest

from quality_platform.services import rbac


class TestPermissionMatrix:
    def test_admin_has_all(self):
        for p in rbac.ALL_PERMISSIONS:
            assert rbac.has_permission("admin", p), f"admin 缺 {p}"

    def test_engineer(self):
        for p in ("view", "run", "case_edit", "audit"):
            assert rbac.has_permission("engineer", p), f"engineer 缺 {p}"
        for p in ("ai_config", "user_admin"):
            assert not rbac.has_permission("engineer", p), f"engineer 不应有 {p}"

    def test_viewer_read_only(self):
        assert rbac.has_permission("viewer", "view")
        for p in ("run", "case_edit", "audit", "ai_config", "user_admin"):
            assert not rbac.has_permission("viewer", p)

    def test_legacy_user_role_falls_back_viewer(self):
        """历史 role='user' 视为 viewer（只读，安全兜底）。"""
        assert not rbac.has_permission("user", "run")
        assert rbac.has_permission("user", "view")
        assert rbac.has_permission(None, "view")


class TestApiAcl:
    def _login_as_role(self, c, username, role):
        """签发指定角色 SSO 令牌登录（绕过密码，验证 RBAC 授权）。"""
        c.post("/api/login", json={"username": "admin", "password": "admin123"})
        r = c.post("/api/sso/token", json={"username": username, "role": role})
        token = r.json["token"]
        c.post("/api/logout")
        c.get("/sso/login?token=" + token)
        return c

    def _client(self):
        from quality_platform.app import app
        return app.test_client()

    def test_engineer_can_run_and_audit(self, monkeypatch):
        """engineer：可触发执行 + 查看审计；不可用户管理/AI 配置。"""
        monkeypatch.setattr("quality_platform.services.test_executor.executor.run_async",
                            lambda *a, **k: 999)
        c = self._login_as_role(self._client(), "eng_api", "engineer")
        r = c.post("/api/runs", json={"test_path": "tests/x"})
        assert r.status_code == 202
        assert c.get("/api/audit").status_code == 200
        assert c.get("/api/users").status_code == 403
        assert c.get("/ai-config").status_code == 403

    def test_viewer_cannot_run(self, monkeypatch):
        """viewer：只读，触发执行 403。"""
        c = self._login_as_role(self._client(), "view_api", "viewer")
        r = c.post("/api/runs", json={"test_path": "tests/x"})
        assert r.status_code == 403
        assert c.get("/api/dashboard").status_code == 200

    def test_engineer_cannot_edit_ai_config(self):
        c = self._login_as_role(self._client(), "eng2", "engineer")
        assert c.put("/api/ai/config", json={}).status_code == 403

    def test_legacy_user_role_readonly(self):
        """旧 role='user' 用户：只读 + 不可执行。"""
        c = self._login_as_role(self._client(), "old_user", "user")
        assert c.post("/api/runs", json={"test_path": "tests/x"}).status_code == 403
        assert c.get("/api/dashboard").status_code == 200
