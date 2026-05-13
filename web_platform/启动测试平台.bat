@echo off
chcp 65001 >nul
title 测试平台Web - 启动脚本
echo ========================================
echo    测试平台Web - 启动脚本
echo ========================================
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"
set "PROJECT_DIR=%SCRIPT_DIR%.."

:: 检查虚拟环境
set "PYTHON_CMD=python"
if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo [信息] 使用虚拟环境 Python
    set "PYTHON_CMD=%PROJECT_DIR%\.venv\Scripts\python.exe"
) else (
    echo [信息] 使用系统 Python
    :: 检查Python是否安装
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到Python，请先安装Python 3.8+
        echo 下载地址: https://www.python.org/downloads/
        echo.
        echo 或者运行修复脚本: 修复Python环境.bat
        pause
        exit /b 1
    )
)

echo [信息] Python路径: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: 检查依赖
echo [1/4] 检查Python依赖...
%PYTHON_CMD% -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖，请稍候...
    %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt"
    %PYTHON_CMD% -m pip install flask flask-cors pymysql bcrypt pyjwt
)

:: 检查数据库
echo.
echo [2/4] 检查数据库配置...
echo.

:: 询问是否初始化数据库
set /p init_db="是否初始化数据库? (y/n): "
if /i "%init_db%"=="y" (
    echo [提示] 正在初始化数据库...
    %PYTHON_CMD% "%BACKEND_DIR%\scripts\init_database.py"
    echo.
)

:: 启动后端
echo [3/4] 启动后端服务 (http://127.0.0.1:8081)...
start "Web Backend" cmd /k "cd /d %BACKEND_DIR% && %PYTHON_CMD% app.py"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端
echo [4/4] 启动前端服务 (http://localhost:8082)...
start "Web Frontend" cmd /k "cd /d %FRONTEND_DIR% && %PYTHON_CMD% -m http.server 8082"

:: 打开浏览器
echo.
echo [完成] 正在打开浏览器...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8082/index.html

echo.
echo ========================================
echo    服务已启动！
echo    后端: http://127.0.0.1:8081
echo    前端: http://localhost:8082
echo.
echo    默认账户:
echo    用户名: admin
echo    密码:   change_me_in_production
echo ========================================
echo.
echo 按任意键退出此窗口（服务继续运行）...
pause >nul
