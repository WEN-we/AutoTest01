"""
认证API接口
"""
from flask import Blueprint, request, jsonify
import bcrypt
from backend.models.user import User
from backend.utils.decorators import login_required, generate_token
from backend.utils.validators import Validator
from backend.config.settings import config

auth_bp = Blueprint('auth', __name__)


def success_response(data=None, message="操作成功"):
    """成功响应"""
    response = {"code": 200, "message": message}
    if data:
        response["data"] = data
    return jsonify(response)


def error_response(message, code=400):
    """错误响应"""
    return jsonify({"code": code, "message": message}), code


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return error_response("用户名和密码不能为空")

        # 查找用户
        user = User.find_by_username(username)
        if not user:
            return error_response("用户名或密码错误")

        # 检查账户是否被锁定
        if User.is_account_locked(user):
            locked_until = user.get('locked_until')
            return error_response(f"账户已被锁定，请{locked_until}分钟后重试", 403)

        # 验证密码
        if not User.verify_password(user, password):
            # 增加失败次数
            User.increment_login_attempts(user['id'])

            # 检查是否需要锁定
            max_attempts = config.get('security.max_login_attempts')
            if user.get('login_attempts', 0) + 1 >= max_attempts:
                lockout_minutes = config.get('security.lockout_minutes')
                User.lock_account(user['id'], lockout_minutes)
                return error_response(f"登录失败次数过多，账户已锁定{lockout_minutes}分钟", 403)

            return error_response("用户名或密码错误")

        # 登录成功
        User.update_last_login(user['id'])

        # 生成JWT令牌
        token = generate_token(user['id'])

        return success_response(
            data={
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user.get('email', ''),
                    "role": user.get('role', 'tester')
                },
                "expires_in": config.get('security.jwt_expiration_hours') * 3600
            },
            message="登录成功"
        )

    except Exception as e:
        print(f"登录失败: {e}")
        return error_response("登录失败，请稍后重试", 500)


@auth_bp.route('/register', methods=['POST'])
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
        print(f"新用户注册成功: {username}")

        return success_response(
            data={"user_id": user_id},
            message="注册成功"
        )

    except Exception as e:
        print(f"注册失败: {e}")
        return error_response("注册失败，请稍后重试", 500)


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户信息"""
    try:
        from flask import request
        user = User.find_by_id(request.current_user_id)

        if not user:
            return error_response("用户不存在", 404)

        return success_response(
            data={
                "id": user['id'],
                "username": user['username'],
                "email": user.get('email', ''),
                "role": user.get('role', 'tester'),
                "created_at": str(user.get('created_at', '')),
                "last_login": str(user.get('last_login', ''))
            }
        )
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return error_response("获取用户信息失败", 500)


@auth_bp.route('/password', methods=['PUT'])
@login_required
def change_password():
    """修改密码"""
    try:
        from flask import request
        data = request.get_json()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        user = User.find_by_id(request.current_user_id)

        # 验证旧密码
        if not User.verify_password(user, old_password):
            return error_response("原密码错误")

        # 验证新密码
        valid, msg = Validator.validate_password(new_password)
        if not valid:
            return error_response(msg)

        # 更新密码
        User.update_password(user['id'], new_password)

        print(f"用户修改密码成功: {user['username']}")
        return success_response(message="密码修改成功")

    except Exception as e:
        print(f"修改密码失败: {e}")
        return error_response("修改密码失败", 500)
