"""
批量将明文密码转换为 bcrypt 加密
用于迁移旧数据库到新系统
"""
import pymysql
import bcrypt
import os

# 数据库配置（从环境变量读取）
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "test_auto"),
    "charset": "utf8mb4"
}

def migrate_passwords():
    """批量迁移密码"""
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 1. 获取所有用户
            cursor.execute("SELECT id, username, password FROM user")
            users = cursor.fetchall()

            print(f"共找到 {len(users)} 个用户")

            migrated = 0
            skipped = 0

            for user in users:
                user_id = user['id']
                username = user['username']
                old_password = user['password']

                # 检查是否已经是 bcrypt 格式
                if old_password.startswith('$2b$') or old_password.startswith('$2a$'):
                    print(f"[{username}] 已是加密格式，跳过")
                    skipped += 1
                    continue

                # 明文密码加密
                hashed = bcrypt.hashpw(old_password.encode('utf-8'), bcrypt.gensalt())

                # 更新数据库
                cursor.execute(
                    "UPDATE user SET password = %s WHERE id = %s",
                    (hashed.decode('utf-8'), user_id)
                )

                print(f"[{username}] 密码已加密")
                migrated += 1

            conn.commit()
            print(f"\n迁移完成：{migrated} 个已加密，{skipped} 个已跳过")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_passwords()