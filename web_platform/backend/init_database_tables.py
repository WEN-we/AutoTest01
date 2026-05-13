"""
数据库初始化脚本
创建测试平台所需的所有表
"""
import pymysql
import sys

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": os.getenv("DB_PASSWORD", ""),
    "charset": "utf8mb4"
}

DATABASE_NAME = "test_auto"

SQL_COMMANDS = [
    """
    CREATE TABLE IF NOT EXISTS `test_task` (
        `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
        `name` VARCHAR(100) NOT NULL COMMENT '任务名称',
        `description` TEXT COMMENT '任务描述',
        `test_type` VARCHAR(50) NOT NULL COMMENT '测试类型',
        `test_path` VARCHAR(255) COMMENT '测试路径',
        `test_scene` VARCHAR(50) DEFAULT 'other' COMMENT '测试场景',
        `env_config` JSON COMMENT '环境配置',
        `status` ENUM('idle', 'queued', 'running', 'success', 'failed', 'stopped') DEFAULT 'idle' COMMENT '任务状态',
        `run_count` INT DEFAULT 0 COMMENT '执行次数',
        `last_run_at` DATETIME COMMENT '最后执行时间',
        `created_by` INT COMMENT '创建者ID',
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        INDEX `idx_test_type` (`test_type`),
        INDEX `idx_test_scene` (`test_scene`),
        INDEX `idx_status` (`status`),
        INDEX `idx_created_by` (`created_by`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试任务表';
    """,
    
    """
    CREATE TABLE IF NOT EXISTS `test_execution` (
        `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '执行ID',
        `execution_id` VARCHAR(36) NOT NULL UNIQUE COMMENT '执行UUID',
        `task_id` INT NOT NULL COMMENT '任务ID',
        `user_id` INT COMMENT '执行者ID',
        `status` ENUM('pending', 'running', 'success', 'failed', 'stopped') DEFAULT 'pending' COMMENT '执行状态',
        `start_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
        `end_time` DATETIME COMMENT '结束时间',
        `duration` INT COMMENT '执行时长（秒）',
        `exit_code` INT COMMENT '退出码',
        `result_summary` JSON COMMENT '结果摘要',
        `trigger_type` ENUM('manual', 'scheduled', 'api', 'jenkins') DEFAULT 'manual' COMMENT '触发方式',
        `scene` VARCHAR(50) COMMENT '测试场景',
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        INDEX `idx_execution_id` (`execution_id`),
        INDEX `idx_task_id` (`task_id`),
        INDEX `idx_user_id` (`user_id`),
        INDEX `idx_status` (`status`),
        INDEX `idx_start_time` (`start_time`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试执行记录表';
    """,
    
    """
    CREATE TABLE IF NOT EXISTS `test_report` (
        `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '报告ID',
        `execution_id` VARCHAR(36) NOT NULL COMMENT '执行UUID',
        `task_id` INT COMMENT '任务ID',
        `report_type` ENUM('json', 'html', 'allure', 'junit') DEFAULT 'json' COMMENT '报告类型',
        `report_path` VARCHAR(500) COMMENT '报告文件路径',
        `report_data` JSON COMMENT '报告数据',
        `summary` JSON COMMENT '测试摘要',
        `passed` INT DEFAULT 0 COMMENT '通过数',
        `failed` INT DEFAULT 0 COMMENT '失败数',
        `skipped` INT DEFAULT 0 COMMENT '跳过数',
        `errors` INT DEFAULT 0 COMMENT '错误数',
        `total` INT DEFAULT 0 COMMENT '总数',
        `pass_rate` DECIMAL(5,2) COMMENT '通过率',
        `duration` INT COMMENT '执行时长（秒）',
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        INDEX `idx_execution_id` (`execution_id`),
        INDEX `idx_task_id` (`task_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试报告表';
    """,
    
    """
    CREATE TABLE IF NOT EXISTS `ai_model_config` (
        `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
        `name` VARCHAR(100) NOT NULL COMMENT '模型名称',
        `provider` VARCHAR(50) NOT NULL COMMENT '提供商',
        `model_type` VARCHAR(100) NOT NULL COMMENT '模型类型',
        `api_endpoint` VARCHAR(500) COMMENT 'API端点',
        `api_key` VARCHAR(255) COMMENT 'API密钥',
        `api_version` VARCHAR(50) COMMENT 'API版本',
        `max_tokens` INT DEFAULT 4000 COMMENT '最大Token数',
        `temperature` DECIMAL(3,2) DEFAULT 0.7 COMMENT '温度参数',
        `timeout` INT DEFAULT 60 COMMENT '超时时间',
        `status` ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
        `is_default` TINYINT DEFAULT 0 COMMENT '是否默认',
        `config` JSON COMMENT '其他配置',
        `remark` TEXT COMMENT '备注',
        `created_by` INT COMMENT '创建者',
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        INDEX `idx_provider` (`provider`),
        INDEX `idx_status` (`status`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI模型配置表';
    """,
    
    """
    CREATE TABLE IF NOT EXISTS `integration_config` (
        `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
        `integration_type` VARCHAR(50) NOT NULL COMMENT '集成类型',
        `name` VARCHAR(100) NOT NULL COMMENT '配置名称',
        `base_url` VARCHAR(500) NOT NULL COMMENT '服务地址',
        `api_token` VARCHAR(255) COMMENT 'API Token',
        `api_key` VARCHAR(255) COMMENT 'API Key',
        `username` VARCHAR(100) COMMENT '用户名',
        `password` VARCHAR(255) COMMENT '密码',
        `auth_type` ENUM('token', 'basic', 'oauth', 'apikey') DEFAULT 'token' COMMENT '认证类型',
        `config` JSON COMMENT '其他配置',
        `status` ENUM('active', 'inactive', 'error') DEFAULT 'active' COMMENT '状态',
        `last_sync` DATETIME COMMENT '最后同步时间',
        `remark` TEXT COMMENT '备注',
        `created_by` INT COMMENT '创建者',
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        INDEX `idx_integration_type` (`integration_type`),
        INDEX `idx_status` (`status`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='集成配置表';
    """,
    
    """
    CREATE TABLE IF NOT EXISTS `execution_log` (
        `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
        `execution_id` VARCHAR(36) NOT NULL COMMENT '执行UUID',
        `log_level` ENUM('INFO', 'WARNING', 'ERROR', 'DEBUG') DEFAULT 'INFO' COMMENT '日志级别',
        `message` TEXT COMMENT '日志内容',
        `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
        INDEX `idx_execution_id` (`execution_id`),
        INDEX `idx_timestamp` (`timestamp`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行日志表';
    """
]


def init_database():
    """初始化数据库表"""
    try:
        print(f"正在连接 MySQL 服务器...")
        conn = pymysql.connect(**DB_CONFIG)
        print("✅ 连接成功！")
        
        cursor = conn.cursor()
        
        print(f"\n📦 正在创建/切换到数据库: {DATABASE_NAME}")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{DATABASE_NAME}`")
        print(f"✅ 数据库 {DATABASE_NAME} 就绪")
        
        print(f"\n📋 正在创建数据表...")
        for i, sql in enumerate(SQL_COMMANDS, 1):
            table_name = sql.split('`')[1] if '`' in sql else f"表{i}"
            cursor.execute(sql)
            print(f"   ✅ 表 {i}: {table_name}")
        
        conn.commit()
        print(f"\n🎉 数据库初始化完成！")
        print(f"\n已创建以下表：")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        print("\n✅ 数据库连接已关闭")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    init_database()
