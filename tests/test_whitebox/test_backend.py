"""
白盒测试 - 登录功能
测试本地登录服务的核心逻辑
"""
import pytest
from unittest.mock import Mock, patch
# 导入 app
from local_web_login.backend_server import app


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestLogin:
    """登录功能测试"""

    def test_login_empty_username(self, client):
        """测试空用户名"""
        response = client.post('/login', json={'username': '', 'password': 'test'})
        assert response.status_code == 400
        assert response.json == {"code": 400, "message": "参数不能为空"}

    def test_login_empty_password(self, client):
        """测试空密码"""
        response = client.post('/login', json={'username': 'test', 'password': ''})
        assert response.status_code == 400
        assert response.json == {"code": 400, "message": "参数不能为空"}

    def test_login_empty_both(self, client):
        """测试用户名和密码都为空"""
        response = client.post('/login', json={'username': '', 'password': ''})
        assert response.status_code == 400
        assert response.json == {"code": 400, "message": "参数不能为空"}

    @patch('local_web_login.backend_server.User.verify_password')
    @patch('local_web_login.local_db.pymysql')
    def test_login_success(self, mock_pymysql, mock_verify, client):
        """测试登录成功"""
        mock_verify.return_value = True
        # 模拟数据库连接和查询
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "username": "test", "password": "hashed",
            "email": "test@test.com", "created_at": None, "last_login": None,
            "login_attempts": 0, "locked_until": None
        }
        mock_db.cursor.return_value = mock_cursor
        mock_pymysql.connect.return_value = mock_db

        response = client.post('/api/login', json={'username': 'test', 'password': 'test'})
        assert response.status_code == 200
        assert response.json["code"] == 200
        assert response.json["message"] == "登录成功"

        # 验证数据库操作（find_by_username + update_last_login 共两次）
        mock_pymysql.connect.assert_called()
        mock_db.cursor.assert_called()
        mock_cursor.execute.assert_called()
        mock_cursor.fetchone.assert_called()

    @patch('local_web_login.local_db.pymysql')
    def test_login_failure(self, mock_pymysql, client):
        """测试登录失败"""
        # 模拟数据库连接和查询
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # 未找到用户
        mock_db.cursor.return_value = mock_cursor
        mock_pymysql.connect.return_value = mock_db

        response = client.post('/api/login', json={'username': 'test', 'password': 'wrong'})
        assert response.status_code == 400
        assert response.json["code"] == 400
        assert "用户名或密码错误" in response.json["message"]

    @patch('local_web_login.local_db.pymysql')
    def test_login_db_error(self, mock_pymysql, client):
        """测试数据库错误"""
        # 模拟数据库连接失败
        mock_pymysql.connect.side_effect = Exception("数据库连接失败")

        response = client.post('/api/login', json={'username': 'test', 'password': 'test'})
        # 数据库异常被登录接口捕获，返回 500 错误
        assert response.status_code == 500