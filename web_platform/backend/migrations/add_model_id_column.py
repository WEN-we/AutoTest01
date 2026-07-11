"""
数据库迁移脚本 - 添加 model_id 列到 ai_model_config 表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.utils.database import Database

def add_model_id_column():
    """添加 model_id 列"""
    try:
        sql = "ALTER TABLE ai_model_config ADD COLUMN `model_id` VARCHAR(255) DEFAULT '' COMMENT '模型ID' AFTER `api_endpoint`"
        Database.execute_update(sql)
        print("✅ model_id 列添加成功")
    except Exception as e:
        error_msg = str(e)
        if "Duplicate column name" in error_msg or "1060" in error_msg:
            print("ℹ️  model_id 列已存在，跳过")
        else:
            print(f"❌ 添加失败: {e}")

if __name__ == '__main__':
    add_model_id_column()