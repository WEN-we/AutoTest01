@echo off
rem ============================================================
rem 一键搭建可复现的本地测试环境（Windows）
rem 用法：双击本文件 或在项目根目录执行  setup_env.bat
rem 产出：.venv 虚拟环境（依赖来自 requirements-lock.txt 精确锁定版本）
rem 使用：.venv\Scripts\python.exe -m pytest tests/test_platform/ -v
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo [1/4] 检查 Python ...
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.11+ 并加入 PATH
    exit /b 1
)

echo [2/4] 创建虚拟环境 .venv ...
if exist .venv\Scripts\python.exe (
    echo        .venv 已存在，跳过创建（如需重建请先删除 .venv 目录）
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] venv 创建失败
        exit /b 1
    )
)

echo [3/4] 安装依赖（优先锁定版本 requirements-lock.txt） ...
if exist requirements-lock.txt (
    .venv\Scripts\python.exe -m pip install --upgrade pip -q
    .venv\Scripts\python.exe -m pip install -r requirements-lock.txt
) else (
    echo        未找到锁定文件，回退安装 requirements-ci.txt
    .venv\Scripts\python.exe -m pip install --upgrade pip -q
    .venv\Scripts\python.exe -m pip install -r requirements-ci.txt
)
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络
    exit /b 1
)

echo [4/4] 自检：跑平台单元测试 ...
.venv\Scripts\python.exe -m pytest tests/test_platform/ -q --no-header
if errorlevel 1 (
    echo [错误] 自检失败，请把上方输出反馈给维护者
    exit /b 1
)

echo.
echo ============================================================
echo 环境就绪！常用命令：
echo   运行单元测试: .venv\Scripts\python.exe -m pytest tests/test_platform/ -v
echo   启动质量平台: .venv\Scripts\python.exe -m quality_platform.app
echo   运行冒烟测试: .venv\Scripts\python.exe run_all_smoke.py
echo ============================================================
