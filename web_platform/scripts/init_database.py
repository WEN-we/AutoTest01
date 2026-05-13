"""
数据库初始化脚本
创建所有必需的数据库表
"""
import pymysql
from backend.config.settings import config

# 获取数据库配置
db_config = config.get_database_config()


def create_database():
    """创建数据库"""
    conn = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['username'],
        password=db_config['password'],
        charset=db_config['charset']
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✓ 数据库 {db_config['database']} 创建成功")
    finally:
        conn.close()


def create_tables():
    """创建所有数据表"""
    conn = pymysql.connect(**db_config)

    try:
        with conn.cursor() as cursor:
            # 1. 用户表
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
                    `is_active` BOOLEAN DEFAULT TRUE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ 表 user 创建成功")

            # 2. 测试任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_task` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `name` VARCHAR(100) NOT NULL,
                    `description` TEXT,
                    `task_type` ENUM('web', 'api', 'mobile', 'performance', 'ai', 'zentao') NOT NULL,
                    `target_url` VARCHAR(500),
                    `test_data` JSON,
                    `ai_model` VARCHAR(50),
                    `status` ENUM('pending', 'running', 'success', 'failed', 'cancelled') DEFAULT 'pending',
                    `created_by` INT,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    `started_at` DATETIME,
                    `finished_at` DATETIME,
                    `result_summary` JSON,
                    FOREIGN KEY (`created_by`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_status` (`status`),
                    INDEX `idx_task_type` (`task_type`),
                    INDEX `idx_created_at` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ 表 test_task 创建成功")

            # 3. 测试执行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_execution` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `task_id` INT NOT NULL,
                    `executor_id` INT,
                    `status` ENUM('running', 'success', 'failed', 'skipped') NOT NULL,
                    `start_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `end_time` DATETIME,
                    `duration` INT,
                    `logs` TEXT,
                    `report_path` VARCHAR(255),
                    `jenkins_build_id` VARCHAR(50),
                    FOREIGN KEY (`task_id`) REFERENCES `test_task`(`id`) ON DELETE CASCADE,
                    FOREIGN KEY (`executor_id`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_task_id` (`task_id`),
                    INDEX `idx_executor_id` (`executor_id`),
                    INDEX `idx_status` (`status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ 表 test_execution 创建成功")

            # 4. AI模型配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `ai_model_config` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `model_type` VARCHAR(50) NOT NULL,
                    `model_name` VARCHAR(100) NOT NULL,
                    `api_key` VARCHAR(255),
                    `base_url` VARCHAR(255),
                    `model_id` VARCHAR(100),
                    `is_active` BOOLEAN DEFAULT TRUE,
                    `priority` INT DEFAULT 0,
                    `config` JSON,
                    `created_by` INT,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (`created_by`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_model_type` (`model_type`),
                    INDEX `idx_is_active` (`is_active`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ 表 ai_model_config 创建成功")

            # 5. 集成配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `integration_config` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `integration_type` ENUM('jenkins', 'zentao', 'gitlab', 'jira') NOT NULL,
                    `name` VARCHAR(100) NOT NULL,
                    `base_url` VARCHAR(255) NOT NULL,
                    `auth_type` ENUM('api_key', 'token', 'basic') DEFAULT 'basic',
                    `credentials` JSON,
                    `is_active` BOOLEAN DEFAULT TRUE,
                    `config` JSON,
                    `created_by` INT,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (`created_by`) REFERENCES `user`(`id`) ON DELETE SET NULL,
                    INDEX `idx_integration_type` (`integration_type`),
                    INDEX `idx_is_active` (`is_active`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ 表 integration_config 创建成功")

            # 6. 测试报告表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `test_report` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `execution_id` INT NOT NULL,
                    `report_type` ENUM('json', 'html', 'allure', 'junit') NOT NULL,
                    `report_path` VARCHAR(255),
                    `report_data` JSON,
                    `summary` JSON,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`execution_id`) REFERENCES `test_execution`(`id`) ON DELETE CASCADE,
                    INDEX `idx_execution_id` (`execution_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ 表 test_report 创建成功")

        conn.commit()
        print("\n✓ 所有数据表创建成功")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ 创建数据表失败: {e}")
        raise
    finally:
        conn.close()


def create_admin_user():
    """创建默认管理员账户"""
    import bcrypt

    conn = pymysql.connect(**db_config)

    try:
        with conn.cursor() as cursor:
            # 检查是否已存在
            cursor.execute("SELECT * FROM user WHERE username = 'admin'")
            admin = cursor.fetchone()

            if not admin:
                hashed = bcrypt.hashpw("change_me_in_production".encode('utf-8'), bcrypt.gensalt())
                cursor.execute(
                    """INSERT INTO user (username, password, email, role, created_at, login_attempts)
                       VALUES (%s, %s, %s, %s, NOW(), 0)""",
                    ("admin", hashed.decode('utf-8'), "admin@test-platform.com", "admin")
                )
                conn.commit()
                print("\n✓ 默认管理员账户创建成功")
                print("  用户名: admin")
                print("  密码: change_me_in_production")
            else:
                print("\n✓ 管理员账户已存在")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ 创建管理员失败: {e}")
    finally:
        conn.close()


def main():
    """主函数"""
    print("=" * 50)
    print("测试平台Web - 数据库初始化")
    print("=" * 50)
    print(f"\n数据库配置:")
    print(f"  Host: {db_config['host']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['username']}")
    print()

    try:
        create_database()
        create_tables()
        create_admin_user()

        print("\n" + "=" * 50)
        print("✓ 数据库初始化完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        raise


if __name__ == '__main__':
    main()
