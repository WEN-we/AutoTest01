"""手动测试 pytest 执行"""
import subprocess
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

project_root = r"D:\Pthon.Object\PythonProject3"
test_path = "test_ui"
pytest_path = os.path.join(project_root, '.venv', 'Scripts', 'pytest.exe')
tests_dir = os.path.join(project_root, 'tests')
test_full_path = os.path.join(tests_dir, test_path)

cmd = f'"{pytest_path}" "{test_full_path}" -v --tb=short'

print(f"命令: {cmd}")
print(f"工作目录: {project_root}")
print(f"测试文件路径: {test_full_path}")
print(f"测试文件是否存在: {os.path.exists(test_full_path)}")
print(f"pytest路径是否存在: {os.path.exists(pytest_path)}")

# 检查 tests 目录下有什么
print(f"\ntests 目录内容:")
for item in os.listdir(tests_dir):
    print(f"  - {item}")

# 如果 test_ui 是目录，检查里面的文件
test_ui_path = os.path.join(tests_dir, 'test_ui')
if os.path.exists(test_ui_path) and os.path.isdir(test_ui_path):
    print(f"\ntest_ui 目录内容:")
    for item in os.listdir(test_ui_path):
        print(f"  - {item}")

print("\n" + "="*60)
print("执行 pytest...")
print("="*60)

try:
    result = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60
    )

    print("\n标准输出:")
    print(result.stdout)

    if result.stderr:
        print("\n标准错误:")
        print(result.stderr)

    print(f"\n返回码: {result.returncode}")

except subprocess.TimeoutExpired:
    print("执行超时（60秒）")
except Exception as e:
    print(f"执行错误: {e}")
