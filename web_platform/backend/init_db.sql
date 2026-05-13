-- =============================================
-- 测试平台数据库初始化脚本
-- 数据库: test_auto
-- 创建日期: 2026-05-09
-- =============================================

-- 使用数据库
USE test_auto;

-- =============================================
-- 1. 平台用户表（如果不存在）
-- =============================================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台用户表';

-- =============================================
-- 2. 测试任务表
-- =============================================
CREATE TABLE IF NOT EXISTS `test_task` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
    `name` VARCHAR(100) NOT NULL COMMENT '任务名称',
    `description` TEXT COMMENT '任务描述',
    `test_type` VARCHAR(50) NOT NULL COMMENT '测试类型: api, ui, smoke, android, ios, windows, linux, harmony, service, performance, ai, whitebox',
    `test_path` VARCHAR(255) COMMENT '测试路径（相对于tests目录）',
    `test_scene` VARCHAR(50) DEFAULT 'other' COMMENT '测试场景: platform, external, local, other',
    `env_config` JSON COMMENT '环境配置',
    `status` ENUM('idle', 'queued', 'running', 'success', 'failed', 'stopped') DEFAULT 'idle' COMMENT '任务状态',
    `created_by` INT COMMENT '创建者ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_test_type` (`test_type`),
    INDEX `idx_test_scene` (`test_scene`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_by` (`created_by`),
    FOREIGN KEY (`created_by`) REFERENCES `platform_user`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试任务表';

-- =============================================
-- 3. 测试执行记录表
-- =============================================
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
    `result_summary` JSON COMMENT '结果摘要（passed, failed, skipped, errors数量）',
    `trigger_type` ENUM('manual', 'scheduled', 'api', 'jenkins') DEFAULT 'manual' COMMENT '触发方式',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_execution_id` (`execution_id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_start_time` (`start_time`),
    FOREIGN KEY (`task_id`) REFERENCES `test_task`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `platform_user`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试执行记录表';

-- =============================================
-- 4. 测试报告表
-- =============================================
CREATE TABLE IF NOT EXISTS `test_report` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '报告ID',
    `execution_id` VARCHAR(36) NOT NULL COMMENT '执行UUID',
    `task_id` INT NOT NULL COMMENT '任务ID',
    `report_type` ENUM('json', 'html', 'allure', 'junit') DEFAULT 'json' COMMENT '报告类型',
    `report_path` VARCHAR(500) COMMENT '报告文件路径',
    `report_data` JSON COMMENT '报告数据（JSON格式）',
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
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_report_type` (`report_type`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试报告表';

-- =============================================
-- 5. AI模型配置表
-- =============================================
CREATE TABLE IF NOT EXISTS `ai_model_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    `name` VARCHAR(100) NOT NULL COMMENT '模型名称',
    `provider` VARCHAR(50) NOT NULL COMMENT '提供商: openai, anthropic, local',
    `model_type` VARCHAR(100) NOT NULL COMMENT '模型类型: gpt-4, gpt-3.5-turbo, claude-3, 本地模型',
    `api_endpoint` VARCHAR(500) COMMENT 'API端点',
    `api_key` VARCHAR(255) COMMENT 'API密钥（加密存储）',
    `api_version` VARCHAR(50) COMMENT 'API版本',
    `max_tokens` INT DEFAULT 4000 COMMENT '最大Token数',
    `temperature` DECIMAL(3,2) DEFAULT 0.7 COMMENT '温度参数',
    `timeout` INT DEFAULT 60 COMMENT '超时时间（秒）',
    `status` ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    `is_default` TINYINT DEFAULT 0 COMMENT '是否默认',
    `config` JSON COMMENT '其他配置',
    `remark` TEXT COMMENT '备注',
    `created_by` INT COMMENT '创建者',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_provider` (`provider`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_default` (`is_default`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI模型配置表';

-- =============================================
-- 6. 集成配置表
-- =============================================
CREATE TABLE IF NOT EXISTS `integration_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    `integration_type` VARCHAR(50) NOT NULL COMMENT '集成类型: jenkins, zentao, gitlab, jira',
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

-- =============================================
-- 7. 任务执行日志表（存储执行过程中的日志）
-- =============================================
CREATE TABLE IF NOT EXISTS `execution_log` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    `execution_id` VARCHAR(36) NOT NULL COMMENT '执行UUID',
    `log_level` ENUM('INFO', 'WARNING', 'ERROR', 'DEBUG') DEFAULT 'INFO' COMMENT '日志级别',
    `message` TEXT COMMENT '日志内容',
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
    INDEX `idx_execution_id` (`execution_id`),
    INDEX `idx_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行日志表';

-- =============================================
-- 8. 初始化默认管理员账户
-- =============================================
INSERT IGNORE INTO `platform_user` (`username`, `password`, `email`, `role`, `status`, `remark`)
VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qiU1A8t8U1c1jK',
    'admin@test.com',
    'admin',
    'active',
    '平台管理员账户'
);

-- =============================================
-- 9. 初始化默认AI模型配置
-- =============================================
INSERT IGNORE INTO `ai_model_config` (`name`, `provider`, `model_type`, `status`, `is_default`, `remark`)
VALUES
    ('OpenAI GPT-4', 'openai', 'gpt-4', 'active', 1, '默认AI模型'),
    ('OpenAI GPT-3.5', 'openai', 'gpt-3.5-turbo', 'active', 0, '备用AI模型');

-- =============================================
-- 10. 初始化默认集成配置示例
-- =============================================
INSERT IGNORE INTO `integration_config` (`integration_type`, `name`, `base_url`, `auth_type`, `status`, `remark`)
VALUES
    ('jenkins', 'Jenkins', 'http://localhost:8080', 'token', 'inactive', 'Jenkins集成配置（需要填写Token）'),
    ('zentao', '禅道', 'http://localhost/zentao', 'basic', 'inactive', '禅道集成配置（需要填写账户）');

-- =============================================
-- 验证表创建
-- =============================================
SELECT '数据库初始化完成！' AS message;
SHOW TABLES;
