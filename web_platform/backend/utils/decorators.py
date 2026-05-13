"""
认证装饰器
"""
from functools import wraps
from flask import request, jsonify
import jwt
import datetime
from backend.config.settings import config


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()

        if not token:
            return jsonify({"code": 401, "message": "未登录或令牌无效"}), 401

        user_id = verify_token(token)
        if not user_id:
            return jsonify({"code": 401, "message": "登录已过期，请重新登录"}), 401

        # 将用户ID存入请求上下文
        request.current_user_id = user_id

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from backend.models.user import User
        user = User.find_by_id(request.current_user_id)

        if not user or user.get('role') != 'admin':
            return jsonify({"code": 403, "message": "需要管理员权限"}), 403

        return f(*args, **kwargs)

    return decorated_function


def get_token_from_header():
    """从请求头获取Token"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def verify_token(token: str):
    """验证Token"""
    try:
        secret = config.get('security.jwt_secret')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_token(user_id: int) -> str:
    """生成Token"""
    secret = config.get('security.jwt_secret')
    expiration_hours = config.get('security.jwt_expiration_hours')

    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_hours),
        'iat': datetime.datetime.utcnow()
    }

    return jwt.encode(payload, secret, algorithm='HS256')
