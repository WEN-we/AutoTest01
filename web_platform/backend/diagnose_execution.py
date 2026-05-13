"""测试执行诊断工具"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.test_executor import executor
import json

print("="*70)
print("测试执行引擎诊断")
print("="*70)

# 检查项目根目录
print(f"\n1. 项目根目录: {executor.project_root}")
print(f"   目录存在: {os.path.exists(executor.project_root)}")

# 检查 tests 目录
tests_dir = os.path.join(executor.project_root, 'tests')
print(f"\n2. tests目录: {tests_dir}")
print(f"   目录存在: {os.path.exists(tests_dir)}")
if os.path.exists(tests_dir):
    print(f"   子目录: {os.listdir(tests_dir)}")

# 检查 pytest 路径
pytest_path = executor._get_pytest_path()
print(f"\n3. pytest路径: {pytest_path}")
print(f"   路径存在: {os.path.exists(pytest_path)}")

# 检查测试路径
test_path = 'test_ui'
test_full_path = os.path.join(tests_dir, test_path)
print(f"\n4. 测试路径:")
print(f"   相对路径: {test_path}")
print(f"   完整路径: {test_full_path}")
print(f"   路径存在: {os.path.exists(test_full_path)}")

if os.path.exists(test_full_path):
    if os.path.isdir(test_full_path):
        print(f"   (是目录) 目录内容: {os.listdir(test_full_path)}")
    else:
        print(f"   (是文件) 文件大小: {os.path.getsize(test_full_path)} bytes")

# 检查 Python 可执行文件
python_exe = executor._get_python_executable()
print(f"\n5. Python可执行文件: {python_exe}")
print(f"   路径存在: {os.path.exists(python_exe)}")

# 构建并显示命令
cmd = executor._build_command('ui', test_path)
print(f"\n6. 执行的命令:")
print(f"   {cmd}")

print("\n" + "="*70)
print("正在检查运行中的执行任务...")
print("="*70)

if executor.running_executions:
    print(f"\n当前运行中的执行任务数量: {len(executor.running_executions)}")
    for exec_id, info in executor.running_executions.items():
        print(f"\n执行ID: {exec_id}")
        print(f"  任务ID: {info['task_id']}")
        print(f"  测试类型: {info['test_type']}")
        print(f"  测试路径: {info['test_path']}")
        print(f"  状态: {info['status']}")
        print(f"  开始时间: {info['start_time']}")
        print(f"  结束时间: {info['end_time']}")
        print(f"  进程对象: {info['process']}")
        print(f"  日志行数: {len(info['log_lines'])}")

        if info['log_lines']:
            print(f"\n  最近10条日志:")
            for log in info['log_lines'][-10:]:
                print(f"    [{log['timestamp']}] {log['message']}")
else:
    print("\n当前没有运行中的执行任务")

print("\n" + "="*70)
print("诊断完成")
print("="*70)
