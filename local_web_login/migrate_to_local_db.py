"""
数据迁移脚本
从 test_auto 数据库迁移 local_web_login 使用的表到 local_web_login 数据库
"""
import pymysql
from pymysql.cursors import DictCursor
import bcrypt
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SOURCE_DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": os.getenv("DB_PASSWORD", ""),
    "database": "test_auto",
    "charset": "utf8mb4",
}

TARGET_DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": os.getenv("DB_PASSWORD", ""),
    "database": "local_web_login",
    "charset": "utf8mb4",
}


def ensure_database_exists():
    """确保 local_web_login 数据库存在"""
    conn = pymysql.connect(
        host=TARGET_DB_CONFIG["host"],
        port=TARGET_DB_CONFIG["port"],
        user=TARGET_DB_CONFIG["user"],
        password=TARGET_DB_CONFIG["password"],
        charset=TARGET_DB_CONFIG["charset"]
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS `local_web_login` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print("[OK] 数据库 local_web_login 已确认存在")
    finally:
        conn.close()


def create_tables():
    """在 local_web_login 数据库中创建表结构"""
    conn = pymysql.connect(**TARGET_DB_CONFIG)
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
            print("[OK] 表 user 创建成功")

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
            print("[OK] 表 test_task 创建成功")

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
            print("[OK] 表 test_execution 创建成功")

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
            print("[OK] 表 ai_model_config 创建成功")

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
            print("[OK] 表 integration_config 创建成功")

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
            print("[OK] 表 test_report 创建成功")

        conn.commit()
        print("\n[OK] 所有数据表创建成功")
    except Exception as e:
        conn.rollback()
        print(f"[FAIL] 创建数据表失败: {e}")
        raise
    finally:
        conn.close()


def migrate_table(source_conn, target_conn, table_name, columns):
    """迁移单个表的数据"""
    try:
        with source_conn.cursor(DictCursor) as src_cursor:
            src_cursor.execute(f"SELECT * FROM `{table_name}`")
            rows = src_cursor.fetchall()

        if not rows:
            print(f"  [SKIP] {table_name}: 无数据")
            return 0

        with target_conn.cursor() as tgt_cursor:
            col_list = ", ".join([f"`{c}`" for c in columns])
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"

            migrated = 0
            for row in rows:
                values = []
                for col in columns:
                    val = row.get(col)
                    if isinstance(val, bytes):
                        try:
                            val = val.decode('utf-8')
                        except Exception:
                            pass
                    values.append(val)
                try:
                    tgt_cursor.execute(insert_sql, values)
                    migrated += 1
                except pymysql.err.IntegrityError as e:
                    if 'Duplicate entry' in str(e):
                        continue
                    raise
                except Exception as e:
                    print(f"  [WARN] {table_name} 行迁移失败: {e}")
                    continue

        target_conn.commit()
        print(f"  [OK] {table_name}: 迁移 {migrated}/{len(rows)} 行")
        return migrated

    except Exception as e:
        target_conn.rollback()
        print(f"  [FAIL] {table_name} 迁移失败: {e}")
        return 0


def migrate_data():
    """从 test_auto 迁移数据到 local_web_login"""
    source_conn = pymysql.connect(**SOURCE_DB_CONFIG)
    target_conn = pymysql.connect(**TARGET_DB_CONFIG)

    total = 0
    try:
        print("\n开始迁移数据...")

        user_cols = ['id', 'username', 'password', 'email', 'role',
                     'created_at', 'last_login', 'login_attempts', 'locked_until', 'is_active']
        total += migrate_table(source_conn, target_conn, 'user', user_cols)

        task_cols = ['id', 'name', 'description', 'test_type', 'test_path',
                     'env_config', 'status', 'created_by', 'created_at', 'updated_at', 'last_run_at']
        total += migrate_table(source_conn, target_conn, 'test_task', task_cols)

        exec_cols = ['id', 'execution_id', 'task_id', 'task_name', 'run_number',
                     'user_id', 'status', 'start_time', 'end_time', 'duration',
                     'result_summary', 'trigger_type', 'test_type']
        total += migrate_table(source_conn, target_conn, 'test_execution', exec_cols)

        model_cols = ['id', 'name', 'provider', 'model_type', 'api_endpoint',
                      'model_id', 'api_key', 'priority', 'config', 'status', 'created_by', 'updated_at']
        total += migrate_table(source_conn, target_conn, 'ai_model_config', model_cols)

        integ_cols = ['id', 'integration_type', 'name', 'base_url', 'api_token',
                      'api_key', 'username', 'password', 'auth_type', 'config',
                      'status', 'created_by', 'updated_at']
        total += migrate_table(source_conn, target_conn, 'integration_config', integ_cols)

        report_cols = ['id', 'execution_id', 'report_type', 'report_path',
                       'report_data', 'summary', 'created_at']
        total += migrate_table(source_conn, target_conn, 'test_report', report_cols)

        print(f"\n[OK] 数据迁移完成，共迁移 {total} 行数据")

    except Exception as e:
        print(f"[FAIL] 数据迁移失败: {e}")
        raise
    finally:
        source_conn.close()
        target_conn.close()


def ensure_default_admin():
    """确保默认管理员账户存在"""
    conn = pymysql.connect(**TARGET_DB_CONFIG)
    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("SELECT * FROM `user` WHERE username = 'admin'")
            admin = cursor.fetchone()

            if not admin:
                hashed = bcrypt.hashpw("change_me_in_production".encode('utf-8'), bcrypt.gensalt())
                hashed_str = hashed.decode('utf-8')
                cursor.execute(
                    """INSERT INTO `user` (username, password, email, role, created_at)
                       VALUES (%s, %s, %s, %s, NOW())""",
                    ("admin", hashed_str, "admin@example.com", "admin")
                )
                conn.commit()
                print("[OK] 默认管理员账户创建成功 (admin / change_me_in_production)")
            else:
                print("[OK] 管理员账户已存在")
    except Exception as e:
        conn.rollback()
        print(f"[WARN] 检查管理员账户失败: {e}")
    finally:
        conn.close()


def verify_migration():
    """验证迁移结果"""
    source_conn = pymysql.connect(**SOURCE_DB_CONFIG)
    target_conn = pymysql.connect(**TARGET_DB_CONFIG)

    tables = ['user', 'test_task', 'test_execution', 'ai_model_config',
              'integration_config', 'test_report']

    print("\n验证迁移结果:")
    print("-" * 60)
    print(f"{'表名':<25} {'源库(test_auto)':<15} {'目标库(local_web_login)':<15}")
    print("-" * 60)

    all_ok = True
    for table in tables:
        try:
            with source_conn.cursor(DictCursor) as cursor:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                src_count = cursor.fetchone()['cnt']
        except Exception:
            src_count = 'N/A'

        try:
            with target_conn.cursor(DictCursor) as cursor:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                tgt_count = cursor.fetchone()['cnt']
        except Exception:
            tgt_count = 'N/A'

        status = "OK" if src_count == tgt_count else "DIFF"
        if status == "DIFF":
            all_ok = False
        print(f"{table:<25} {str(src_count):<15} {str(tgt_count):<15} {status}")

    print("-" * 60)
    if all_ok:
        print("[OK] 迁移验证通过")
    else:
        print("[WARN] 部分表数据量不一致，请检查")

    source_conn.close()
    target_conn.close()


def run_migration():
    """执行完整迁移流程"""
    print("=" * 60)
    print("local_web_login 数据库迁移工具")
    print("源数据库: test_auto")
    print("目标数据库: local_web_login")
    print("=" * 60)

    ensure_database_exists()
    create_tables()
    migrate_data()
    ensure_default_admin()
    verify_migration()

    print("\n迁移完成！")
    print("local_web_login 服务现在将连接到 local_web_login 数据库")


if __name__ == '__main__':
    run_migration()
