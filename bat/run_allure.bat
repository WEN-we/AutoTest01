@echo off
chcp 65001 >nul
cls

:: ==============================
:: 自动获取当前时间戳（用来命名独立报告）
:: ==============================
set datetime=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set datetime=%datetime: =0%
set report_name=测试报告_%datetime%

echo ==============================
echo  开始执行自动化测试
echo  本次报告将独立保存为：%report_name%
echo ==============================

:: 1. 运行测试用例
pytest D:\Pthon.Object\PythonProject3\tests --alluredir=allure-results

:: 2. 生成【独立报告】→ 不会覆盖旧的！
allure generate allure-results -o %report_name% --clean

:: 3. 清理临时文件
rd /s /q "allure-results"

echo.
echo ==============================
echo  ✅ 全新独立报告已生成：%report_name%
echo  ✅ 历史报告全部保留，互不影响
echo ==============================

:: 可选：自动打开本次新报告
allure open %report_name%

pause