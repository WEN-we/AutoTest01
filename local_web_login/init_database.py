"""
数据库初始化脚本
用于初始化 local_web_login 数据库及表结构
"""
import pymysql
import json
import bcrypt
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("LOCAL_DB_NAME", "local_web_login"),
    "charset": "utf8mb4"
}


def create_database():
    """创建数据库"""
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset=DB_CONFIG["charset"]
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS `local_web_login` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        print(f"数据库 {DB_CONFIG['database']} 创建成功")
    finally:
        conn.close()


def create_tables():
    """创建数据表"""
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `user` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `username` VARCHAR(50) UNIQUE NOT NULL,
                    `password` VARCHAR(255) NOT NULL,
                    `email` VARCHAR(100),
                    `role` ENUM('admin', 'tester', 'viewer') DEFAULT 'tester',
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `last_login` DATETIME,
                    `login_attempts` INT DEFAULT 0,
                    `locked_until` DATETIME,
                    `is_active` BOOLEAN DEFAULT TRUE,
                    INDEX `idx_username` (`username`),
                    INDEX `idx_email` (`email`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 user 创建成功")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_task` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `name` VARCHAR(100) NOT NULL,
                    `description` TEXT,
                    `test_type` VARCHAR(50) DEFAULT 'web',
                    `test_path` VARCHAR(500),
                    `env_config` JSON,
                    `status` VARCHAR(20) DEFAULT 'idle',
                    `created_by` INT,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    `last_run_at` DATETIME,
                    FOREIGN KEY (`created_by`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_status` (`status`),
                    INDEX `idx_test_type` (`test_type`),
                    INDEX `idx_created_at` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 test_task 创建成功")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_execution` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `execution_id` VARCHAR(100),
                    `task_id` INT NOT NULL,
                    `task_name` VARCHAR(100),
                    `run_number` INT DEFAULT 1,
                    `user_id` INT,
                    `status` VARCHAR(20) DEFAULT 'running',
                    `start_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `end_time` DATETIME,
                    `duration` INT,
                    `result_summary` JSON,
                    `trigger_type` VARCHAR(20) DEFAULT 'manual',
                    `test_type` VARCHAR(50),
                    FOREIGN KEY (`task_id`) REFERENCES `test_task`(`id`) ON DELETE CASCADE,
                    FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_task_id` (`task_id`),
                    INDEX `idx_execution_id` (`execution_id`),
                    INDEX `idx_status` (`status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 test_execution 创建成功")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `ai_model_config` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `name` VARCHAR(100) NOT NULL,
                    `provider` VARCHAR(50),
                    `model_type` VARCHAR(50) NOT NULL,
                    `api_endpoint` VARCHAR(255),
                    `model_id` VARCHAR(100),
                    `api_key` VARCHAR(255),
                    `priority` INT DEFAULT 0,
                    `config` JSON,
                    `status` ENUM('active', 'inactive') DEFAULT 'active',
                    `created_by` INT,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (`created_by`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_model_type` (`model_type`),
                    INDEX `idx_status` (`status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 ai_model_config 创建成功")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `integration_config` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `integration_type` VARCHAR(50) NOT NULL,
                    `name` VARCHAR(100) NOT NULL,
                    `base_url` VARCHAR(255) NOT NULL,
                    `api_token` VARCHAR(255),
                    `api_key` VARCHAR(255),
                    `username` VARCHAR(100),
                    `password` VARCHAR(255),
                    `auth_type` VARCHAR(20) DEFAULT 'apikey',
                    `config` JSON,
                    `status` ENUM('active', 'inactive') DEFAULT 'active',
                    `created_by` INT,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (`created_by`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_integration_type` (`integration_type`),
                    INDEX `idx_status` (`status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 integration_config 创建成功")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_report` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `execution_id` INT NOT NULL,
                    `report_type` VARCHAR(20) DEFAULT 'json',
                    `report_path` VARCHAR(255),
                    `report_data` JSON,
                    `summary` JSON,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`execution_id`) REFERENCES `test_execution`(`id`) ON DELETE CASCADE,
                    INDEX `idx_execution_id` (`execution_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("表 test_report 创建成功")

        conn.commit()
        print("所有数据表创建成功")

    except Exception as e:
        conn.rollback()
        print(f"创建数据表失败: {e}")
        raise
    finally:
        conn.close()


def create_default_admin():
    """创建默认管理员账户"""
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM `user` WHERE username = 'admin'")
            admin = cursor.fetchone()

            if not admin:
                admin_pwd = os.getenv("ADMIN_DEFAULT_PASSWORD", "change_me_in_production")
                hashed = bcrypt.hashpw(admin_pwd.encode('utf-8'), bcrypt.gensalt())
                hashed_str = hashed.decode('utf-8')

                cursor.execute(
                    """INSERT INTO `user` (username, password, email, role, created_at)
                       VALUES (%s, %s, %s, %s, NOW())""",
                    ("admin", hashed_str, "admin@example.com", "admin")
                )

                conn.commit()
                print("默认管理员账户创建成功")
                print("用户名: admin")
                print("密码: (从环境变量 ADMIN_DEFAULT_PASSWORD 读取)")
            else:
                print("管理员账户已存在")

    except Exception as e:
        conn.rollback()
        print(f"创建默认管理员失败: {e}")
    finally:
        conn.close()


def create_sample_data():
    """创建示例数据"""
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM test_task")
            result = cursor.fetchone()

            if result['count'] == 0:
                cursor.execute("SELECT id FROM `user` LIMIT 1")
                user = cursor.fetchone()

                if user:
                    user_id = user['id']

                    sample_tasks = [
                        ("登录功能测试", "测试用户登录流程", "web", "http://127.0.0.1:8080",
                         json.dumps({"username": "test", "password": "test123"}), "success"),
                        ("首页功能测试", "测试首页加载和展示", "web", "http://example.com",
                         json.dumps({}), "success"),
                        ("API接口测试", "测试用户API接口", "api", "http://api.example.com/users",
                         json.dumps({"method": "GET"}), "failed"),
                        ("AI自动化测试", "AI驱动的端到端测试", "ai", "http://example.com",
                         json.dumps({"model": "qwen"}), "idle"),
                    ]

                    for task in sample_tasks:
                        cursor.execute(
                            """INSERT INTO test_task
                               (name, description, test_type, test_path, env_config, status, created_by, created_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                            (*task, user_id)
                        )

                    conn.commit()
                    print("示例任务数据创建成功")
            else:
                print("任务数据已存在，跳过创建示例数据")

    except Exception as e:
        conn.rollback()
        print(f"创建示例数据失败: {e}")
    finally:
        conn.close()


def init_database():
    """初始化数据库"""
    print("开始初始化 local_web_login 数据库...")
    print(f"数据库配置: {DB_CONFIG}")

    create_database()
    create_tables()
    create_default_admin()
    create_sample_data()

    print("\n数据库初始化完成!")
    print("\n请使用以下凭据登录:")
    print("  用户名: admin")
    print("  密码: (请查看环境变量 ADMIN_DEFAULT_PASSWORD 的值)")


if __name__ == '__main__':
    init_database()
