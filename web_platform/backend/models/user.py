"""
用户数据模型
使用 platform_user 表
"""
import bcrypt
from backend.utils.database import Database


class User:
    """用户模型"""

    @staticmethod
    def find_by_username(username: str):
        """根据用户名查找用户"""
        sql = "SELECT * FROM platform_user WHERE username = %s"
        return Database.execute_query(sql, (username,), fetch_one=True)

    @staticmethod
    def find_by_id(user_id: int):
        """根据ID查找用户"""
        sql = """
            SELECT id, username, email, nickname, role, status,
                   created_at, updated_at, last_login, login_attempts, locked_until, remark
            FROM platform_user WHERE id = %s
        """
        return Database.execute_query(sql, (user_id,), fetch_one=True)

    @staticmethod
    def find_by_email(email: str):
        """根据邮箱查找用户"""
        sql = "SELECT * FROM platform_user WHERE email = %s"
        return Database.execute_query(sql, (email,), fetch_one=True)

    @staticmethod
    def create(username: str, password: str, email: str = "", nickname: str = "", role: str = "user") -> int:
        """创建新用户"""
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')

        sql = """
            INSERT INTO platform_user (username, password, email, nickname, role, status, created_at, login_attempts)
            VALUES (%s, %s, %s, %s, %s, 'active', NOW(), 0)
        """
        return Database.execute_insert(sql, (username, hashed_str, email, nickname, role))

    @staticmethod
    def update_last_login(user_id: int):
        """更新最后登录时间"""
        sql = "UPDATE platform_user SET last_login = NOW(), login_attempts = 0 WHERE id = %s"
        Database.execute_update(sql, (user_id,))

    @staticmethod
    def increment_login_attempts(user_id: int):
        """增加登录失败次数"""
        sql = "UPDATE platform_user SET login_attempts = login_attempts + 1 WHERE id = %s"
        Database.execute_update(sql, (user_id,))

    @staticmethod
    def lock_account(user_id: int, minutes: int = 30):
        """锁定账户"""
        sql = """
            UPDATE platform_user
            SET locked_until = DATE_ADD(NOW(), INTERVAL %s MINUTE),
                status = 'locked'
            WHERE id = %s
        """
        Database.execute_update(sql, (minutes, user_id))

    @staticmethod
    def unlock_account(user_id: int):
        """解锁账户"""
        sql = """
            UPDATE platform_user
            SET status = 'active', locked_until = NULL, login_attempts = 0
            WHERE id = %s
        """
        Database.execute_update(sql, (user_id,))

    @staticmethod
    def is_account_locked(user: dict) -> bool:
        """检查账户是否被锁定"""
        if user.get('status') == 'locked':
            locked_until = user.get('locked_until')
            if locked_until:
                from datetime import datetime
                if isinstance(locked_until, str):
                    locked_until = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S')
                if locked_until > datetime.now():
                    return True
        return False

    @staticmethod
    def verify_password(user: dict, password: str) -> bool:
        """验证密码"""
        stored = user.get('password', '')

        if isinstance(stored, str):
            stored_hash = stored.encode('utf-8')
        else:
            stored_hash = stored

        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)

    @staticmethod
    def update_password(user_id: int, new_password: str):
        """更新密码"""
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')
        sql = "UPDATE platform_user SET password = %s WHERE id = %s"
        Database.execute_update(sql, (hashed_str, user_id))

    @staticmethod
    def update_profile(user_id: int, nickname: str = None, email: str = None):
        """更新用户资料"""
        updates = []
        params = []

        if nickname:
            updates.append("nickname = %s")
            params.append(nickname)
        if email:
            updates.append("email = %s")
            params.append(email)

        if updates:
            params.append(user_id)
            sql = f"UPDATE platform_user SET {', '.join(updates)} WHERE id = %s"
            Database.execute_update(sql, tuple(params))

    @staticmethod
    def get_all_users(page: int = 1, page_size: int = 20, role: str = None):
        """获取所有用户（分页）"""
        offset = (page - 1) * page_size

        if role:
            sql = """
                SELECT id, username, email, nickname, role, status, created_at, last_login
                FROM platform_user
                WHERE role = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            count_sql = "SELECT COUNT(*) as total FROM platform_user WHERE role = %s"
            total = Database.execute_query(count_sql, (role,), fetch_one=True)['total']
            users = Database.execute_query(sql, (role, page_size, offset))
        else:
            sql = """
                SELECT id, username, email, nickname, role, status, created_at, last_login
                FROM platform_user
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            count_sql = "SELECT COUNT(*) as total FROM platform_user"
            total = Database.execute_query(count_sql, fetch_one=True)['total']
            users = Database.execute_query(sql, (page_size, offset))

        return {
            'items': users,
            'total': total,
            'page': page,
            'page_size': page_size
        }
