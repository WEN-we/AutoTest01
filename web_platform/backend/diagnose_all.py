"""
完整的测试平台诊断工具
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8081"
API_BASE = f"{BASE_URL}/api"

print("="*70)
print("测试平台诊断工具")
print("="*70)

# 测试1：登录获取token
print("\n【测试1】用户登录")
print("-"*70)
login_data = {
    "username": "admin",
    "password": "change_me_in_production"
}
try:
    resp = requests.post(f"{API_BASE}/auth/login", json=login_data)
    print(f"状态码: {resp.status_code}")
    result = resp.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get('code') == 200:
        token = result['data']['token']
        headers = {'Authorization': f'Bearer {token}'}
        print(f"✅ 登录成功，token: {token[:20]}...")
    else:
        print(f"❌ 登录失败")
        sys.exit(1)
except Exception as e:
    print(f"❌ 请求失败: {e}")
    sys.exit(1)

# 测试2：获取执行记录列表
print("\n【测试2】获取执行记录列表")
print("-"*70)
try:
    resp = requests.get(f"{API_BASE}/executions", headers=headers)
    print(f"状态码: {resp.status_code}")
    result = resp.json()
    print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
    
    if result.get('code') == 200:
        executions = result['data']['items']
        print(f"\n执行记录数量: {len(executions)}")
        
        # 统计
        success_count = sum(1 for e in executions if e.get('status') == 'success')
        failed_count = sum(1 for e in executions if e.get('status') == 'failed')
        running_count = sum(1 for e in executions if e.get('status') == 'running')
        
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"运行中: {running_count}")
        
        if executions:
            print(f"\n最新的5条执行记录:")
            for i, exec in enumerate(executions[:5], 1):
                print(f"  {i}. ID: {exec.get('execution_id')[:20]}...")
                print(f"     任务ID: {exec.get('task_id')}")
                print(f"     状态: {exec.get('status')}")
                print(f"     开始时间: {exec.get('start_time')}")
                print(f"     结果摘要: {exec.get('result_summary')}")
                print()
    else:
        print(f"❌ 获取失败: {result.get('message')}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试3：获取任务列表
print("\n【测试3】获取任务列表")
print("-"*70)
try:
    resp = requests.get(f"{API_BASE}/tasks?page_size=100", headers=headers)
    print(f"状态码: {resp.status_code}")
    result = resp.json()
    
    if result.get('code') == 200:
        tasks = result['data']['items']
        print(f"任务数量: {len(tasks)}")
        
        if tasks:
            print(f"\n任务列表:")
            for i, task in enumerate(tasks[:5], 1):
                print(f"  {i}. ID: {task.get('id')}, 名称: {task.get('name')}")
                print(f"     状态: {task.get('status')}")
                print(f"     类型: {task.get('test_type')}")
                print()
    else:
        print(f"❌ 获取失败: {result.get('message')}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试4：检查数据库中的执行记录
print("\n【测试4】检查数据库中的执行记录")
print("-"*70)
try:
    from backend.models.execution import Execution
    db_executions = Execution.find_all(page=1, page_size=10)
    
    if db_executions:
        print(f"数据库执行记录数量: {len(db_executions)}")
        for i, exec in enumerate(db_executions[:3], 1):
            print(f"\n  记录{i}:")
            print(f"    execution_id: {exec.get('execution_id')}")
            print(f"    task_id: {exec.get('task_id')}")
            print(f"    status: {exec.get('status')}")
            print(f"    start_time: {exec.get('start_time')}")
            print(f"    end_time: {exec.get('end_time')}")
            print(f"    result_summary: {exec.get('result_summary')}")
    else:
        print("❌ 数据库中没有执行记录")
except Exception as e:
    print(f"❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()

# 测试5：获取特定执行记录的状态和日志
print("\n【测试5】获取特定执行记录的状态和日志")
print("-"*70)
try:
    from backend.models.execution import Execution
    from backend.services.test_executor import executor
    
    # 获取最新的执行记录
    db_executions = Execution.find_all(page=1, page_size=1)
    if db_executions:
        latest_exec = db_executions[0]
        exec_id = latest_exec['execution_id']
        
        print(f"测试执行ID: {exec_id}")
        
        # 获取状态
        status = executor.get_execution_status(exec_id)
        print(f"\n从内存获取状态: {status}")
        
        # 获取数据库状态
        db_status = Execution.find_by_execution_id(exec_id)
        print(f"从数据库获取状态: {db_status}")
        
        # 获取日志
        logs = executor.get_execution_logs(exec_id, 0, 100)
        print(f"\n日志数量: {len(logs)}")
        if logs:
            print("最近5条日志:")
            for log in logs[-5:]:
                print(f"  [{log.get('timestamp')}] {log.get('message')[:100]}")
        else:
            print("❌ 没有日志！")
    else:
        print("没有执行记录可以测试")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("诊断完成")
print("="*70)
