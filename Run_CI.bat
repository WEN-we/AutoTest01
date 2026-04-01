@echo off
echo on
cd /d %~dp0

:: 【企业标准】删除旧报告
if exist allure-results rd /s /q allure-results
if exist allure-report rd /s /q allure-report

:: 运行测试
call venv\Scripts\activate
pytest --alluredir=allure-results

:: 生成新报告
allure generate allure-results -o allure-report --clean

:: 发送测试报告通知
python send_email.py

echo.
echo ==========================
echo ✅ 全部执行完成
echo ==========================