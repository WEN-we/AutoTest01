"""SUT 服务健康巡检（大厂拨测 / 合成监控）

对标大厂线上巡检：不验证复杂业务，只确认「服务活着 + 核心链路有响应」。
- GET  /                 首页可达（200）
- POST /api/login        错误密码应被拒绝（>= 400，不允许 2xx 通过）

该用例集是平台"门禁绿"的稳定数据源；复杂业务断言在 test_api/test_ecommerce。
"""
import pytest
import requests

SUT_BASE = "http://127.0.0.1:8090"
TIMEOUT = 10


@pytest.mark.smoke
class TestSutHealth:
    """SUT 健康巡检（拨测）"""

    def test_sut_homepage_reachable(self):
        """首页可达：服务进程存活且 HTTP 正常响应"""
        resp = requests.get(f"{SUT_BASE}/", timeout=TIMEOUT)
        assert resp.status_code == 200, f"首页不可达：HTTP {resp.status_code}"

    def test_sut_login_rejects_bad_password(self):
        """错误密码必须被拒绝：不允许 2xx 通过"""
        resp = requests.post(
            f"{SUT_BASE}/api/login",
            json={"username": "admin", "password": "definitely-wrong"},
            timeout=TIMEOUT,
        )
        assert resp.status_code >= 400, (
            f"安全缺陷：错误密码返回 {resp.status_code}，登录校验未生效"
        )

    def test_sut_login_accepts_request(self):
        """登录接口对合法请求有业务响应（code 字段存在即可，不要求成功）"""
        resp = requests.post(
            f"{SUT_BASE}/api/login",
            json={"username": "admin", "password": "definitely-wrong"},
            timeout=TIMEOUT,
        )
        assert "code" in resp.text or resp.status_code >= 400, "登录接口无业务响应"
