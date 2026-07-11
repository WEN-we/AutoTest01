#!/usr/bin/env python3
"""
检查数据库中的用户数据
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.database import Database


def check_users():
    """检查用户数据"""
    try:
        # 查询所有用户
        sql = "SELECT id, username, password, status, login_attempts, locked_until FROM platform_user"
        users = Database.execute_query(sql)
        
        print("=== 数据库中的用户 ===")
        for user in users:
            print(f"\nID: {user['id']}")
            print(f"用户名: {user['username']}")
            print(f"密码哈希: {user['password'][:50]}...")
            print(f"状态: {user['status']}")
            print(f"登录尝试次数: {user['login_attempts']}")
            print(f"锁定时间: {user['locked_until']}")
        
        return True
    except Exception as e:
        print(f"查询失败: {e}")
        return False


if __name__ == '__main__':
    print("正在检查数据库用户...")
    check_users()
