@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ==============================
echo  质量平台一键启动（全链路集中化）
echo  MySQL 检查 -^> 被测服务 8090 -^> 平台 8081 -^> 执行节点 9101/9102
echo ==============================

if exist .venv\Scripts\python.exe (
    set PY=.venv\Scripts\python.exe
) else (
    echo [提示] 未找到 .venv，使用系统 python（依赖需已安装）
    set PY=python
)

%PY% -m quality_platform.scripts.orchestrate --workers %*
echo.
echo 常用操作：
echo   查看状态  %PY% -m quality_platform.scripts.orchestrate --status
echo   停止全部  %PY% -m quality_platform.scripts.orchestrate --stop
echo   平台地址  http://127.0.0.1:8081  （admin / admin123）
pause
