"""
数据库迁移脚本 - 添加 priority 列到 ai_model_config 表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.database import Database

def add_priority_column():
    """添加 priority 列"""
    try:
        sql = "ALTER TABLE ai_model_config ADD COLUMN `priority` INT DEFAULT 0 COMMENT '优先级' AFTER `timeout`"
        Database.execute_update(sql)
        print("✅ priority 列添加成功")
    except Exception as e:
        error_msg = str(e)
        if "Duplicate column name" in error_msg or "1060" in error_msg:
            print("ℹ️  priority 列已存在，跳过")
        else:
            print(f"❌ 添加失败: {e}")

if __name__ == '__main__':
    add_priority_column()
