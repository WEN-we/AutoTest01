-- =============================================
-- 平台用户表 - 与 local_web_login 共用数据库
-- 数据库: test_auto
-- =============================================

-- 创建平台用户表（平台专用用户）
CREATE TABLE IF NOT EXISTS `platform_user` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `password` VARCHAR(255) NOT NULL COMMENT '密码（bcrypt加密）',
    `email` VARCHAR(100) COMMENT '邮箱',
    `nickname` VARCHAR(50) COMMENT '昵称',
    `role` ENUM('admin', 'user', 'viewer') DEFAULT 'user' COMMENT '角色：管理员/普通用户/查看者',
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

-- 创建默认管理员账户
-- 用户名: admin
-- 密码: change_me_in_production (bcrypt加密)
INSERT IGNORE INTO `platform_user` (`username`, `password`, `email`, `role`, `status`, `remark`)
VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qiU1A8t8U1c1jK',
    'admin@test.com',
    'admin',
    'active',
    '平台管理员账户'
);

-- 验证管理员账户
SELECT id, username, email, role, status FROM platform_user WHERE username = 'admin';
