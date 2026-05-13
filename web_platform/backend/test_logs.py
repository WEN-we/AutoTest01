"""测试日志写入和读取"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.test_executor import executor
from backend.utils.database import Database

# 测试日志写入
test_execution_id = "test-log-execution-123"

print("="*70)
print("测试日志功能")
print("="*70)

# 模拟写入日志
print("\n1. 测试日志写入...")
executor._add_log(test_execution_id, "测试日志消息1")
executor._add_log(test_execution_id, "测试日志消息2")
executor._add_log(test_execution_id, "✅ 测试成功")

print("   日志已写入内存")

# 从数据库读取日志
print("\n2. 从数据库读取日志...")
sql = """
    SELECT * FROM execution_log 
    WHERE execution_id = %s 
    ORDER BY timestamp DESC
    LIMIT 10
"""
results = Database.execute_query(sql, (test_execution_id,))

if results:
    print(f"   找到 {len(results)} 条日志:")
    for row in results:
        print(f"     - [{row['timestamp']}] {row['message']}")
else:
    print("   ❌ 数据库中没有找到日志！")

# 从执行器读取日志
print("\n3. 从执行器读取日志...")
logs = executor.get_execution_logs(test_execution_id, 0, 10)
if logs:
    print(f"   找到 {len(logs)} 条日志:")
    for log in logs:
        print(f"     - [{log.get('timestamp')}] {log.get('message')}")
else:
    print("   ❌ 执行器中没有找到日志！")

print("\n" + "="*70)
print("测试完成")
print("="*70)
