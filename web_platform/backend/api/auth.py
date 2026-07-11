"""
认证API接口
"""
from flask import Blueprint, request, jsonify, current_app
import bcrypt
import os
from werkzeug.utils import secure_filename
from backend.models.user import User
from backend.utils.decorators import login_required, generate_token
from backend.utils.validators import Validator
from backend.utils.response import success_response, error_response
from utils.tools.crypto_util import get_password_crypto

auth_bp = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def _decrypt_password(encrypted_password):
    """解密密码"""
    if not encrypted_password:
        return None
    password_crypto = get_password_crypto()
    decrypted = password_crypto.decrypt_password(encrypted_password)
    if decrypted is None:
        # 解密失败，可能是明文密码（兼容旧版本）
        return encrypted_password
    return decrypted


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route('/public-key', methods=['GET'])
def get_public_key():
    """获取RSA公钥"""
    try:
        password_crypto = get_password_crypto()
        return success_response({"public_key": password_crypto.get_public_key()})
    except Exception as e:
        print(f"获取公钥失败: {e}")
        return error_response("获取公钥失败", 500)


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = _decrypt_password(data.get('password', ''))
        email = data.get('email', '').strip()

        # 验证输入
        valid, msg = Validator.validate_username(username)
        if not valid:
            return error_response(msg)

        valid, msg = Validator.validate_email(email)
        if not valid:
            return error_response(msg)

        valid, msg = Validator.validate_password(password)
        if not valid:
            return error_response(msg)

        # 检查用户是否已存在
        if User.find_by_username(username):
            return error_response("用户名已被注册")

        if email and User.find_by_email(email):
            return error_response("邮箱已被注册")

        # 创建用户
        user_id = User.create(username, password, email)
        user = User.find_by_id(user_id)

        # 生成Token
        token = generate_token(user['id'])

        print(f"用户注册成功: {username}")
        return success_response({
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user.get('email', ''),
                "nickname": user.get('nickname', ''),
                "role": user.get('role', 'user')
            }
        }, "注册成功")
    except Exception as e:
        print(f"注册失败: {e}")
        return error_response("注册失败", 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = _decrypt_password(data.get('password', ''))

        if not username or not password:
            return error_response("用户名和密码不能为空")

        # 查找用户
        user = User.find_by_username(username)
        if not user:
            return error_response("用户名或密码错误")

        # 检查账号状态
        if User.is_account_locked(user):
            return error_response("账号已被锁定，请稍后再试")

        # 验证密码
        if not User.verify_password(user['password'], password):
            User.increment_login_attempts(user['id'])
            return error_response("用户名或密码错误")

        # 更新最后登录时间
        User.update_last_login(user['id'])

        # 生成Token
        token = generate_token(user['id'])

        print(f"用户登录成功: {username}")
        return success_response({
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user.get('email', ''),
                "nickname": user.get('nickname', ''),
                "avatar_url": user.get('avatar_url', ''),
                "role": user.get('role', 'user')
            }
        }, "登录成功")
    except Exception as e:
        print(f"登录失败: {e}")
        return error_response("登录失败", 500)


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取用户信息"""
    try:
        user = User.find_by_id(request.current_user_id)
        if not user:
            return error_response("用户不存在", 404)

        return success_response({
            "id": user['id'],
            "username": user['username'],
            "email": user.get('email', ''),
            "nickname": user.get('nickname', ''),
            "avatar_url": user.get('avatar_url', ''),
            "role": user.get('role', 'user'),
            "created_at": str(user.get('created_at', '')),
            "last_login": str(user.get('last_login', ''))
        })
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return error_response("获取失败", 500)


@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户信息"""
    try:
        data = request.get_json()
        nickname = data.get('nickname', '')
        email = data.get('email', '')

        user = User.find_by_id(request.current_user_id)
        if not user:
            return error_response("用户不存在", 404)

        # 验证邮箱
        if email and email != user.get('email'):
            valid, msg = Validator.validate_email(email)
            if not valid:
                return error_response(msg)
            # 检查邮箱是否已被其他用户使用
            existing = User.find_by_email(email)
            if existing and existing['id'] != request.current_user_id:
                return error_response("邮箱已被注册")

        User.update_profile(request.current_user_id, nickname=nickname, email=email)

        # 返回更新后的用户信息
        updated_user = User.find_by_id(request.current_user_id)
        return success_response({
            "id": updated_user['id'],
            "username": updated_user['username'],
            "email": updated_user.get('email', ''),
            "nickname": updated_user.get('nickname', ''),
            "avatar_url": updated_user.get('avatar_url', ''),
            "role": updated_user.get('role', 'user')
        }, "资料更新成功")
    except Exception as e:
        print(f"更新资料失败: {e}")
        return error_response("更新失败", 500)


@auth_bp.route('/password', methods=['PUT'])
@login_required
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        old_password = _decrypt_password(data.get('old_password', ''))
        new_password = _decrypt_password(data.get('new_password', ''))

        user = User.find_by_id(request.current_user_id)

        if not user:
            return error_response("用户不存在", 404)

        if not User.verify_password(user['password'], old_password):
            return error_response("原密码错误")

        valid, msg = Validator.validate_password(new_password)
        if not valid:
            return error_response(msg)

        User.update_password(user['id'], new_password)

        return success_response(message="密码修改成功")

    except Exception as e:
        return error_response("修改密码失败", 500)


@auth_bp.route('/username', methods=['PUT'])
@login_required
def update_username():
    """更新用户名"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()

        if not username:
            return error_response("用户名不能为空")

        valid, msg = Validator.validate_username(username)
        if not valid:
            return error_response(msg)

        user = User.find_by_id(request.current_user_id)
        if not user:
            return error_response("用户不存在", 404)

        # 检查用户名是否已被使用
        existing = User.find_by_username(username)
        if existing and existing['id'] != request.current_user_id:
            return error_response("用户名已被占用")

        User.update_username(request.current_user_id, username)

        return success_response(message="用户名修改成功")
    except Exception as e:
        print(f"修改用户名失败: {e}")
        return error_response("修改失败", 500)


@auth_bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    """上传头像"""
    try:
        if 'avatar' not in request.files:
            return error_response("请选择要上传的文件")

        file = request.files['avatar']
        if file.filename == '':
            return error_response("请选择文件")

        if file and allowed_file(file.filename):
            user = User.find_by_id(request.current_user_id)

            # 获取上传目录
            upload_dir = current_app.config.get('UPLOAD_FOLDER')
            if not upload_dir:
                backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                upload_dir = os.path.join(backend_dir, 'uploads', 'avatars')

            # 确保目录存在
            os.makedirs(upload_dir, exist_ok=True)

            # 生成安全的文件名
            filename = secure_filename(f"avatar_{user['id']}_{file.filename}")
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)

            # 保存头像URL
            avatar_url = f"/uploads/avatars/{filename}"
            User.update_avatar(request.current_user_id, avatar_url)

            return success_response(data={"avatar_url": avatar_url}, message="头像上传成功")

        return error_response("不支持的文件格式，仅支持 PNG、JPG、JPEG、GIF")
    except Exception as e:
        print(f"上传头像失败: {e}")
        return error_response("上传失败", 500)


@auth_bp.route('/account', methods=['DELETE'])
@login_required
def delete_account():
    """注销账号"""
    try:
        data = request.get_json()
        password = _decrypt_password(data.get('password', ''))

        user = User.find_by_id(request.current_user_id)

        if not user:
            return error_response("用户不存在", 404)

        if not User.verify_password(user['password'], password):
            return error_response("密码错误")

        User.delete_user(request.current_user_id)

        return success_response(message="账号注销成功")
    except Exception as e:
        return error_response("注销失败", 500)


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """找回密码（简化版，实际应发送邮件）"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        new_password = _decrypt_password(data.get('new_password', ''))

        if not email or not new_password:
            return error_response("请填写邮箱和新密码")

        valid, msg = Validator.validate_email(email)
        if not valid:
            return error_response(msg)

        valid, msg = Validator.validate_password(new_password)
        if not valid:
            return error_response(msg)

        user = User.find_by_email(email)
        if not user:
            # 为了安全，即使邮箱不存在也返回成功提示
            return success_response(message="如果邮箱已注册，密码重置链接已发送到您的邮箱")

        # 实际生产环境应该发送重置邮件，这里直接重置密码用于演示
        User.update_password(user['id'], new_password)

        print(f"密码重置成功: {user['username']}")
        return success_response(message="密码重置成功，请使用新密码登录")
    except Exception as e:
        print(f"密码重置失败: {e}")
        return error_response("重置失败", 500)
