"""
初始化平台数据库
创建 platform_user 表并添加默认管理员
"""
import pymysql
import bcrypt
import sys
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "test_auto"),
    "charset": "utf8mb4"
}

def create_platform_user_table():
    """创建平台用户表"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 创建 platform_user 表
            sql = """
            CREATE TABLE IF NOT EXISTS `platform_user` (
                `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
                `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
                `password` VARCHAR(255) NOT NULL COMMENT '密码（bcrypt加密）',
                `email` VARCHAR(100) COMMENT '邮箱',
                `nickname` VARCHAR(50) COMMENT '昵称',
                `role` ENUM('admin', 'user', 'viewer') DEFAULT 'user' COMMENT '角色',
                `status` ENUM('active', 'inactive', 'locked') DEFAULT 'active' COMMENT '状态',
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                `last_login` DATETIME COMMENT '最后登录时间',
                `login_attempts` INT DEFAULT 0 COMMENT '登录失败次数',
                `locked_until` DATETIME COMMENT '锁定截止时间',
                `remark` TEXT COMMENT '备注',
                INDEX `idx_username` (`username`),
                INDEX `idx_status` (`status`),
                INDEX `idx_role` (`role`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台用户表'
            """
            cursor.execute(sql)
            conn.commit()
            print("✓ platform_user 表创建成功")

            # 检查是否已有管理员账户
            cursor.execute("SELECT COUNT(*) as cnt FROM platform_user WHERE username = 'admin'")
            result = cursor.fetchone()

            if result[0] == 0:
                # 创建默认管理员账户
                admin_pwd = os.getenv("ADMIN_DEFAULT_PASSWORD", "change_me_in_production")
                hashed = bcrypt.hashpw(admin_pwd.encode('utf-8'), bcrypt.gensalt())

                sql = """
                INSERT INTO `platform_user` (username, password, email, role, status, remark)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    'admin',
                    hashed.decode('utf-8'),
                    'admin@test.com',
                    'admin',
                    'active',
                    '平台管理员账户'
                ))
                conn.commit()
                print("✓ 默认管理员账户创建成功")
                print("  用户名: admin")
                print("  密码: (从环境变量 ADMIN_DEFAULT_PASSWORD 读取)")
            else:
                print("✓ 管理员账户已存在")

            # 显示所有用户
            cursor.execute("SELECT id, username, email, role, status FROM platform_user")
            users = cursor.fetchall()
            print(f"\n当前用户列表 ({len(users)} 个用户):")
            for user in users:
                print(f"  [{user[3]}] {user[0]}: {user[1]} ({user[2]}) - {user[4]}")

    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 50)
    print("初始化平台数据库")
    print("=" * 50)
    print()

    try:
        create_platform_user_table()
        print()
        print("=" * 50)
        print("初始化完成！")
        print("=" * 50)
    except pymysql.err.OperationalError as e:
        print(f"✗ 数据库连接失败: {e}")
        print("请确保 MySQL 服务已启动，并且配置正确")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        sys.exit(1)
