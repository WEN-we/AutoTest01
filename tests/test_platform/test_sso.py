"""
SSO 单点登录服务 + 路由 单元测试
覆盖：签发/验签/篡改拒绝/过期拒绝/自动开户/路由保护
"""
import sys
import time
from unittest.mock import patch

import pytest

sys.path.insert(0, r"D:\Pthon.Object\PythonProject3")
os = __import__("os")
os.environ["PLATFORM_SECRET"] = "test-sso-secret"

from quality_platform.services import sso  # noqa: E402


class TestSsoToken:
    def test_issue_and_verify(self):
        """签发 -> 验签成功，payload 正确。"""
        r = sso.issue_token("alice", role="admin", ttl=300)
        assert "token" in r and "expires_at" in r
        identity = sso.verify_token(r["token"])
        assert identity == {"username": "alice", "role": "admin"}

    def test_tampered_token_rejected(self):
        """篡改签名/内容 -> 拒绝。"""
        r = sso.issue_token("bob")
        bad = r["token"][:-2] + ("aa" if not r["token"].endswith("aa") else "bb")
        assert sso.verify_token(bad) is None
        # 换用户名但保留签名（伪造 payload）
        payload_b64 = r["token"].split(".")[0]
        import base64, json
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        payload["sub"] = "mallory"
        forged = sso._b64url(json.dumps(payload).encode()) + "." + r["token"].split(".")[1]
        assert sso.verify_token(forged) is None

    def test_expired_token_rejected(self):
        """过期令牌 -> 拒绝。"""
        r = sso.issue_token("carol", ttl=1)
        time.sleep(2.0)
        assert sso.verify_token(r["token"]) is None

    def test_garbage_token_rejected(self):
        assert sso.verify_token("not-a-token") is None
        assert sso.verify_token("") is None


class TestSsoApi:
    def _client(self):
        from quality_platform.app import app
        return app.test_client()

    def test_issue_requires_login(self):
        """未登录签发 -> 401。"""
        c = self._client()
        r = c.post("/api/sso/token", json={"username": "x"})
        assert r.status_code == 401

    def test_sso_login_flow(self):
        """签发 -> 跳转登录 -> 会话建立 -> 自动开户。"""
        c = self._client()
        c.post("/api/login", json={"username": "admin", "password": "admin123"})
        r = c.post("/api/sso/token", json={"username": "sso_alice"})
        assert r.status_code == 200
        token = r.json["token"]
        c.post("/api/logout")

        r = c.get("/sso/login?token=" + token, follow_redirects=False)
        assert r.status_code == 302
        # 会话已建立
        r = c.get("/api/dashboard")
        assert r.status_code == 200
        # 自动开户
        from quality_platform.models import get_user_by_username
        assert get_user_by_username("sso_alice") is not None

    def test_sso_invalid_token(self):
        """无效令牌 -> 401 登录页。"""
        c = self._client()
        r = c.get("/sso/login?token=bad.token", follow_redirects=False)
        assert r.status_code == 401
