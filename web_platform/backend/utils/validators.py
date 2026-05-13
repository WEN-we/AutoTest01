"""
验证工具模块
"""
import re
from typing import Tuple


class Validator:
    """输入验证工具"""

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """验证用户名"""
        if not username:
            return False, "用户名不能为空"
        if len(username) < 3:
            return False, "用户名至少3个字符"
        if len(username) > 50:
            return False, "用户名最多50个字符"
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
            return True, ""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "邮箱格式不正确"
        return True, ""

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """验证URL格式"""
        if not url:
            return False, "URL不能为空"
        pattern = r'^https?://'
        if not re.match(pattern, url):
            return False, "URL必须以http://或https://开头"
        return True, ""
