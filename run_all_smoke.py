import os
import subprocess
import sys

# 添加项目根目录到 Python 路径，确保能导入 utils 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.tools.path_manager import get_test_path, get_path


def main() -> int:
    """
    一键运行冒烟测试集（API + UI）。
    
    测试用例路径：
    - tests/test_smoke/test_smoke_api.py (API 冒烟测试)
    - tests/test_smoke/test_smoke_ui.py (UI 冒烟测试)

    测试报告路径：
    - report/pytest-html/report.html

    - 其它端（Android/iOS/Windows/Linux GUI/Service）默认不收集，除非：
      - 显式传入 --run-all；或
      - 设置 ENABLE_<TARGET>=1（例如 ENABLE_ANDROID=1）
    """
    # 使用路径管理器获取测试目录路径
    smoke_test_path = get_test_path('test_smoke')
    
    # 获取报告目录路径
    report_dir = get_path('report', 'pytest-html')
    report_path = os.path.join(report_dir, 'report.html')
    
    # 确保报告目录存在
    os.makedirs(report_dir, exist_ok=True)
    
    project_root = get_path()
    
    # 切换到项目根目录
    original_cwd = os.getcwd()
    os.chdir(project_root)
    
    try:
        # 构建 pytest 命令，直接运行冒烟测试目录
        args = [
            sys.executable,
            "-m",
            "pytest",
            smoke_test_path,  # 直接指定冒烟测试目录
            "--timeout=60",
            f"--html={report_path}",  # 指定报告路径
            "--self-contained-html",
            "--tb=short",
        ]
        
        # 如果需要运行所有端测试
        if "--run-all" in sys.argv:
            args.append("--run-all")
        
        print(f"=== 运行冒烟测试 ===")
        print(f"项目根目录: {project_root}")
        print(f"冒烟测试目录: {smoke_test_path}")
        print(f"测试报告路径: {report_path}")
        print(f"执行命令: {' '.join(args)}")
        print("=" * 50)
        
        return subprocess.call(args)
        
    finally:
        # 恢复原工作目录
        os.chdir(original_cwd)


if __name__ == "__main__":
    raise SystemExit(main())