-- 为 test_execution 表添加 test_type 字段
-- 执行此SQL以更新数据库结构

USE test_auto;

-- 添加 test_type 字段（如果不存在）
ALTER TABLE test_execution 
ADD COLUMN IF NOT EXISTS test_type VARCHAR(50) DEFAULT 'api' COMMENT '测试类型' AFTER trigger_type;

-- 添加索引
ALTER TABLE test_execution 
ADD INDEX IF NOT EXISTS idx_test_type (test_type);

-- 验证
DESCRIBE test_execution;
