-- =============================================
-- 添加 avatar_url 字段到 platform_user 表
-- =============================================

USE test_auto;

-- 添加 avatar_url 字段
ALTER TABLE `platform_user` 
ADD COLUMN IF NOT EXISTS `avatar_url` VARCHAR(500) NULL COMMENT '用户头像URL' 
AFTER `nickname`;

-- 验证字段添加
SHOW COLUMNS FROM `platform_user`;
