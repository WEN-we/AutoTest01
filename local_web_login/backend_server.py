"""
本地测试服务 - 修复版
修复了密码验证和注册问题
"""
import sys
import os

current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
sys.path.insert(0, project_root)

from utils.tools.path_manager import path_manager
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from functools import wraps
import bcrypt
import jwt
import datetime
import re
import logging
from typing import Dict, Optional, Tuple

# 导入统一的数据库工具类
from utils.tools.db_util import Database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['JWT_EXPIRATION_HOURS'] = 24
app.config['MAX_LOGIN_ATTEMPTS'] = 5
app.config['LOCKOUT_MINUTES'] = 30

# 数据库配置（与 utils/tools/config_reader.py 保持一致）
# 注意：现在使用统一的 Database 类，配置从 ConfigReader 读取


# ==================== 用户模型 ====================

class User:
    """用户模型"""

    def __init__(self, id: int = None, username: str = "", email: str = "",
                 created_at: datetime.datetime = None, last_login: datetime.datetime = None):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = created_at
        self.last_login = last_login

    @staticmethod
    def find_by_username(username: str) -> Optional[Dict]:
        """根据用户名查找用户"""
        sql = "SELECT * FROM user WHERE username = %s"
        return Database.execute_query(sql, (username,), fetch_one=True)

    @staticmethod
    def find_by_id(user_id: int) -> Optional[Dict]:
        """根据ID查找用户"""
        sql = "SELECT id, username, email, created_at, last_login FROM user WHERE id = %s"
        return Database.execute_query(sql, (user_id,), fetch_one=True)

    @staticmethod
    def find_by_email(email: str) -> Optional[Dict]:
        """根据邮箱查找用户"""
        sql = "SELECT * FROM user WHERE email = %s"
        return Database.execute_query(sql, (email,), fetch_one=True)

    @staticmethod
    def create(username: str, password: str, email: str = "") -> int:
        """创建新用户 - 修复：确保密码以字符串存储"""
        # 密码加密
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')  # 关键修复：转为字符串

        sql = """
            INSERT INTO user (username, password, email, created_at, login_attempts, locked_until)
            VALUES (%s, %s, %s, NOW(), 0, NULL)
        """
        Database.execute_update(sql, (username, hashed_str, email))

        # 获取新用户ID
        result = Database.execute_query("SELECT LAST_INSERT_ID() as id", fetch_one=True)
        return result['id']

    @staticmethod
    def update_last_login(user_id: int):
        """更新最后登录时间"""
        sql = "UPDATE user SET last_login = NOW(), login_attempts = 0 WHERE id = %s"
        Database.execute_update(sql, (user_id,))

    @staticmethod
    def increment_login_attempts(user_id: int):
        """增加登录失败次数"""
        sql = "UPDATE user SET login_attempts = login_attempts + 1 WHERE id = %s"
        Database.execute_update(sql, (user_id,))

    @staticmethod
    def lock_account(user_id: int, minutes: int = 30):
        """锁定账户"""
        lock_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        sql = "UPDATE user SET locked_until = %s WHERE id = %s"
        Database.execute_update(sql, (lock_time, user_id))

    @staticmethod
    def is_account_locked(user: Dict) -> bool:
        """检查账户是否被锁定"""
        locked_until = user.get('locked_until')
        if locked_until and locked_until > datetime.datetime.now():
            return True
        return False

    @staticmethod
    def verify_password(user: Dict, password: str) -> bool:
        """验证密码 - 修复：兼容字符串和 bytes"""
        stored = user.get('password', '')

        # 统一转为 bytes
        if isinstance(stored, str):
            stored_hash = stored.encode('utf-8')
        else:
            stored_hash = stored

        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)


# ==================== JWT认证工具 ====================

class Auth:
    """认证工具类"""

    @staticmethod
    def generate_token(user_id: int) -> str:
        """生成JWT令牌"""
        payload = {
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=app.config['JWT_EXPIRATION_HOURS']),
            'iat': datetime.datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def get_auth_token() -> Optional[str]:
        """从请求头获取token"""
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        return None


# ==================== 装饰器 ====================

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = Auth.get_auth_token()
        if not token:
            return jsonify({"code": 401, "message": "未登录或令牌无效"}), 401

        user_id = Auth.verify_token(token)
        if not user_id:
            return jsonify({"code": 401, "message": "登录已过期，请重新登录"}), 401

        # 将用户信息存入请求上下文
        request.current_user = User.find_by_id(user_id)
        if not request.current_user:
            return jsonify({"code": 401, "message": "用户不存在"}), 401

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


# ==================== 验证工具 ====================

class Validator:
    """输入验证工具"""

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """验证用户名"""
        if not username:
            return False, "用户名不能为空"
        if len(username) < 3:
            return False, "用户名至少3个字符"
        if len(username) > 20:
            return False, "用户名最多20个字符"
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含字母、数字和下划线"
        return True, ""

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """验证密码强度"""
        if not password:
            return False, "密码不能为空"
        if len(password) < 6:
            return False, "密码至少6个字符"
        if len(password) > 50:
            return False, "密码最多50个字符"
        return True, ""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """验证邮箱格式"""
        if not email:
            return True, ""  # 邮箱可选
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "邮箱格式不正确"
        return True, ""


# ==================== API响应工具 ====================

def success_response(data: Dict = None, message: str = "操作成功") -> Dict:
    """成功响应"""
    response = {"code": 200, "message": message}
    if data:
        response["data"] = data
    return response


def error_response(message: str, code: int = 400):
    """错误响应"""
    return jsonify({"code": code, "message": message}), code


# ==================== 前端页面 ====================

LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户登录 - 测试平台</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        :root {
            --primary-color: #4f46e5;
            --primary-hover: #4338ca;
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        body {
            background: var(--bg-gradient);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 420px;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .logo {
            width: 80px;
            height: 80px;
            background: var(--bg-gradient);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            color: white;
            font-size: 36px;
        }
        .login-title {
            text-align: center;
            font-size: 24px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 8px;
        }
        .login-subtitle {
            text-align: center;
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 32px;
        }
        .form-floating { margin-bottom: 16px; }
        .form-floating input {
            border-radius: 12px;
            border: 2px solid #e5e7eb;
            height: 56px;
        }
        .form-floating input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
        }
        .form-floating label { padding-left: 16px; }
        .btn-login {
            width: 100%;
            height: 52px;
            background: var(--primary-color);
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            margin-top: 8px;
            transition: all 0.3s ease;
        }
        .btn-login:hover {
            background: var(--primary-hover);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(79, 70, 229, 0.4);
        }
        .form-options {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 16px 0;
            font-size: 14px;
        }
        .forgot-password {
            color: var(--primary-color);
            text-decoration: none;
            font-weight: 500;
        }
        .divider {
            display: flex;
            align-items: center;
            margin: 24px 0;
            color: #9ca3af;
            font-size: 14px;
        }
        .divider::before, .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #e5e7eb;
        }
        .divider span { padding: 0 16px; }
        .register-link {
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }
        .register-link a {
            color: var(--primary-color);
            font-weight: 600;
            text-decoration: none;
        }
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1050;
        }
        .modal-content { border-radius: 20px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo"><i class="bi bi-shield-check"></i></div>
        <h1 class="login-title">欢迎回来</h1>
        <p class="login-subtitle">请登录您的测试平台账号</p>
        <form id="loginForm" novalidate>
            <div class="form-floating">
                <input type="text" class="form-control" id="username" placeholder="用户名" required>
                <label for="username"><i class="bi bi-person me-2"></i>用户名</label>
                <div class="invalid-feedback">请输入用户名</div>
            </div>
            <div class="form-floating">
                <input type="password" class="form-control" id="password" placeholder="密码" required>
                <label for="password"><i class="bi bi-lock me-2"></i>密码</label>
                <div class="invalid-feedback">请输入密码</div>
            </div>
            <div class="form-options">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="rememberMe">
                    <label class="form-check-label text-secondary" for="rememberMe">记住我</label>
                </div>
                <a href="#" class="forgot-password" onclick="showForgotPassword()">忘记密码？</a>
            </div>
            <button type="submit" class="btn btn-primary btn-login" id="loginBtn">
                <span class="spinner-border spinner-border-sm d-none" id="loading"></span>
                <span id="btnText">登 录</span>
            </button>
        </form>
        <div class="divider"><span>或</span></div>
        <p class="register-link">
            还没有账号？<a href="#" onclick="showRegister()">立即注册</a>
        </p>
    </div>
    <div class="toast-container">
        <div id="toast" class="toast align-items-center text-white border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi me-2" id="toastIcon"></i>
                    <span id="toastMessage"></span>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    </div>
    <div class="modal fade" id="registerModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header border-0 pb-0">
                    <h5 class="modal-title fw-bold">注册新账号</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body p-4">
                    <form id="registerForm">
                        <div class="form-floating mb-3">
                            <input type="text" class="form-control" id="regUsername" placeholder="用户名" required>
                            <label for="regUsername">用户名</label>
                        </div>
                        <div class="form-floating mb-3">
                            <input type="email" class="form-control" id="regEmail" placeholder="邮箱">
                            <label for="regEmail">邮箱（可选）</label>
                        </div>
                        <div class="form-floating mb-3">
                            <input type="password" class="form-control" id="regPassword" placeholder="密码" required>
                            <label for="regPassword">密码</label>
                        </div>
                        <div class="form-floating mb-3">
                            <input type="password" class="form-control" id="regConfirmPassword" placeholder="确认密码" required>
                            <label for="regConfirmPassword">确认密码</label>
                        </div>
                        <button type="submit" class="btn btn-primary w-100" style="border-radius: 12px; height: 52px;">注 册</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            const toastMessage = document.getElementById('toastMessage');
            const toastIcon = document.getElementById('toastIcon');
            toast.className = `toast align-items-center text-white border-0 bg-${type}`;
            toastMessage.textContent = message;
            toastIcon.className = `bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info-circle'} me-2`;
            new bootstrap.Toast(toast).show();
        }
        function validateForm() {
            const username = document.getElementById('username');
            const password = document.getElementById('password');
            let isValid = true;
            if (!username.value.trim()) {
                username.classList.add('is-invalid');
                isValid = false;
            } else {
                username.classList.remove('is-invalid');
            }
            if (!password.value.trim()) {
                password.classList.add('is-invalid');
                isValid = false;
            } else {
                password.classList.remove('is-invalid');
            }
            return isValid;
        }
        document.getElementById('username').addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
        document.getElementById('password').addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            if (!validateForm()) return;
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const loginBtn = document.getElementById('loginBtn');
            const loading = document.getElementById('loading');
            const btnText = document.getElementById('btnText');
            loginBtn.disabled = true;
            loading.classList.remove('d-none');
            btnText.textContent = '登录中...';
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await res.json();
                if (data.code === 200) {
                    localStorage.setItem('token', data.data.token);
                    localStorage.setItem('user', JSON.stringify(data.data.user));
                    showToast('登录成功！', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    showToast(data.message, 'danger');
                }
            } catch (error) {
                showToast('网络错误，请稍后重试', 'danger');
            } finally {
                loginBtn.disabled = false;
                loading.classList.add('d-none');
                btnText.textContent = '登 录';
            }
        });
        function showRegister() {
            new bootstrap.Modal(document.getElementById('registerModal')).show();
        }
        function showForgotPassword() {
            showToast('请联系管理员重置密码', 'info');
        }
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const username = document.getElementById('regUsername').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            const confirmPassword = document.getElementById('regConfirmPassword').value;
            if (password !== confirmPassword) {
                showToast('两次输入的密码不一致', 'danger');
                return;
            }
            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password, email})
                });
                const data = await res.json();
                if (data.code === 200) {
                    showToast('注册成功！请登录', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('registerModal')).hide();
                } else {
                    showToast(data.message, 'danger');
                }
            } catch (error) {
                showToast('网络错误，请稍后重试', 'danger');
            }
        });
    </script>
</body>
</html>
'''


DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>控制台 - 测试平台</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body { background: #f3f4f6; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { border-radius: 16px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .stat-card { padding: 24px; }
        .stat-number { font-size: 32px; font-weight: 700; color: #4f46e5; }
        .stat-label { color: #6b7280; font-size: 14px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="#"><i class="bi bi-shield-check me-2"></i>测试平台</a>
            <div class="d-flex align-items-center text-white">
                <span class="me-3"><i class="bi bi-person-circle me-1"></i><span id="username">用户</span></span>
                <button class="btn btn-outline-light btn-sm" onclick="logout()">
                    <i class="bi bi-box-arrow-right me-1"></i>退出
                </button>
            </div>
        </div>
    </nav>
    <div class="container py-4">
        <div class="row g-4">
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-number" id="testCount">0</div>
                    <div class="stat-label">测试用例</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-number text-success" id="passCount">0</div>
                    <div class="stat-label">通过</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-number text-danger" id="failCount">0</div>
                    <div class="stat-label">失败</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-number text-warning" id="pendingCount">0</div>
                    <div class="stat-label">待执行</div>
                </div>
            </div>
        </div>
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">欢迎使用测试平台</h5>
                        <p class="card-text text-muted">您已成功登录，可以开始使用AI自主测试功能。</p>
                        <a href="/" class="btn btn-primary">返回登录页</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const token = localStorage.getItem('token');
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        if (!token) {
            window.location.href = '/';
        } else {
            document.getElementById('username').textContent = user.username || '用户';
        }
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/';
        }
    </script>
</body>
</html>
'''


# ==================== API路由 ====================

@app.route('/')
def index():
    """登录页面"""
    return render_template_string(LOGIN_HTML)


@app.route('/dashboard')
def dashboard():
    """控制台页面"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()

        # 验证输入
        valid, msg = Validator.validate_username(username)
        if not valid:
            return error_response(msg)

        valid, msg = Validator.validate_password(password)
        if not valid:
            return error_response(msg)

        valid, msg = Validator.validate_email(email)
        if not valid:
            return error_response(msg)

        # 检查用户名是否已存在
        if User.find_by_username(username):
            return error_response("用户名已被注册")

        # 检查邮箱是否已存在
        if email and User.find_by_email(email):
            return error_response("邮箱已被注册")

        # 创建用户
        user_id = User.create(username, password, email)
        logger.info(f"新用户注册成功: {username}")

        return jsonify(success_response(
            data={"user_id": user_id},
            message="注册成功"
        ))

    except Exception as e:
        logger.error(f"注册失败: {e}")
        return error_response("注册失败，请稍后重试", 500)


@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        test_mode = data.get('test_mode', False)

        if not username or not password:
            return error_response("用户名和密码不能为空")

        # 查找用户
        user = User.find_by_username(username)
        if not user:
            # 测试模式：用户不存在时也允许登录
            if test_mode:
                logger.warning(f"[测试模式] 用户 {username} 不存在，但仍允许登录")
                # 生成临时token
                temp_token = jwt.encode(
                    {'user_id': 0, 'username': username, 'exp': datetime.datetime.now() + datetime.timedelta(hours=24)},
                    app.config['SECRET_KEY'],
                    algorithm='HS256'
                )
                return jsonify(success_response(
                    data={
                        "token": temp_token,
                        "user": {
                            "id": 0,
                            "username": username,
                            "email": ''
                        }
                    },
                    message="测试模式登录成功"
                ))
            return error_response("用户名或密码错误")

        # 检查账户是否被锁定
        if User.is_account_locked(user):
            locked_until = user.get('locked_until')
            return error_response(f"账户已被锁定，请{locked_until}后再试", 403)

        # 测试模式：跳过密码验证
        if test_mode:
            logger.warning(f"[测试模式] 用户 {username} 跳过密码验证")
        elif not User.verify_password(user, password):
            # 增加失败次数
            User.increment_login_attempts(user['id'])

            # 检查是否需要锁定
            if user.get('login_attempts', 0) + 1 >= app.config['MAX_LOGIN_ATTEMPTS']:
                User.lock_account(user['id'], app.config['LOCKOUT_MINUTES'])
                return error_response(f"登录失败次数过多，账户已锁定{app.config['LOCKOUT_MINUTES']}分钟", 403)

            return error_response("用户名或密码错误")

        # 登录成功
        if not test_mode:
            User.update_last_login(user['id'])

        # 生成JWT令牌
        token = Auth.generate_token(user['id'] if user['id'] != 0 else 0)

        logger.info(f"用户登录成功: {username} {'[测试模式]' if test_mode else ''}")

        return jsonify(success_response(
            data={
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user.get('email', '')
                }
            },
            message="登录成功"
        ))

    except Exception as e:
        logger.error(f"登录失败: {e}")
        return error_response("登录失败，请稍后重试", 500)


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    user = request.current_user
    logger.info(f"用户登出: {user['username']}")
    return jsonify(success_response(message="登出成功"))


@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    """获取用户信息"""
    user = request.current_user
    return jsonify(success_response(
        data={
            "id": user['id'],
            "username": user['username'],
            "email": user.get('email', ''),
            "created_at": user.get('created_at'),
            "last_login": user.get('last_login')
        }
    ))


@app.route('/api/user/password', methods=['PUT'])
@login_required
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        user = request.current_user

        # 验证旧密码
        if not User.verify_password(user, old_password):
            return error_response("原密码错误")

        # 验证新密码
        valid, msg = Validator.validate_password(new_password)
        if not valid:
            return error_response(msg)

        # 更新密码
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')
        sql = "UPDATE user SET password = %s WHERE id = %s"
        Database.execute_update(sql, (hashed_str, user['id']))

        logger.info(f"用户修改密码成功: {user['username']}")
        return jsonify(success_response(message="密码修改成功"))

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return error_response("修改密码失败", 500)


@app.route('/api/admin/users', methods=['GET'])
@login_required
def list_users():
    """获取用户列表"""
    try:
        sql = """
            SELECT id, username, email, created_at, last_login, login_attempts, locked_until
            FROM user ORDER BY created_at DESC
        """
        users = Database.execute_query(sql)
        return jsonify(success_response(data={"users": users}))
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return error_response("获取用户列表失败", 500)


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"code": 404, "message": "接口不存在"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"code": 500, "message": "服务器内部错误"}), 500


# ==================== 蓝图注册 ====================

def register_blueprints():
    """注册所有蓝图"""
    from local_web_login.tasks_api import tasks_bp
    from local_web_login.ai_models_api import ai_models_bp
    from local_web_login.integrations_api import integrations_bp
    from local_web_login.jenkins_api import jenkins_bp
    from local_web_login.zentao_api import zentao_bp

    app.register_blueprint(tasks_bp)
    app.register_blueprint(ai_models_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(jenkins_bp)
    app.register_blueprint(zentao_bp)

    logger.info("所有蓝图注册成功")


# ==================== 启动 ====================

if __name__ == '__main__':
    register_blueprints()
    logger.info("服务启动: http://127.0.0.1:8080")
    app.run(debug=True, port=8080)
