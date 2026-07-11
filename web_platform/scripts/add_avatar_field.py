#!/usr/bin/env python3
"""
添加 avatar_url 字段到 platform_user 表
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.database import Database


def add_avatar_url_field():
    """添加 avatar_url 字段"""
    try:
        # 检查字段是否已存在
        check_sql = """
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'platform_user' 
              AND COLUMN_NAME = 'avatar_url'
        """
        result = Database.execute_query(check_sql, fetch_one=True)
        
        if result and result.get('count', 0) > 0:
            print("avatar_url 字段已存在，无需添加")
            return True
        
        # 添加字段
        alter_sql = """
            ALTER TABLE `platform_user` 
            ADD COLUMN `avatar_url` VARCHAR(500) NULL COMMENT '用户头像URL' 
            AFTER `nickname`
        """
        Database.execute_update(alter_sql)
        print("成功添加 avatar_url 字段！")
        
        # 验证添加
        verify_sql = "SHOW COLUMNS FROM `platform_user`"
        columns = Database.execute_query(verify_sql)
        print("\n表结构:")
        for col in columns:
            print(f"  - {col['Field']}: {col['Type']}")
            
        return True
    except Exception as e:
        print(f"添加字段失败: {e}")
        return False


if __name__ == '__main__':
    print("正在添加 avatar_url 字段...")
    success = add_avatar_url_field()
    sys.exit(0 if success else 1)
