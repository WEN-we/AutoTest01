"""
测试执行引擎 - 核心模块
支持测试用例结果逐个存储到数据库，最后汇总生成Allure报告
"""
import os
import sys
import subprocess
import threading
import json
import uuid
import shutil
import re
from datetime import datetime
from typing import Dict, List, Optional, Callable
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.tools.path_manager import (
    get_path, get_tests_path, get_reports_path,
    get_allure_results_path, get_allure_report_path, get_venv_scripts_path
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestExecutor:
    """测试执行引擎"""

    TEST_TYPE_MAPPING = {
        'api': 'test_api',
        'ui': 'test_ui',
        'smoke': 'test_smoke',
        'android': 'test_android',
        'ios': 'test_ios',
        'windows': 'test_windows',
        'linux': 'test_linux',
        'harmony': 'test_harmony',
        'service': 'test_service',
        'performance': 'test_performance',
        'ai': 'test_ai',
        'whitebox': 'test_whitebox'
    }

    def __init__(self):
        self.running_executions: Dict[str, dict] = {}
        self.log_callbacks: Dict[str, List[Callable]] = {}
        self.project_root = get_path()
        self.python_exe = self._get_python_executable()
        self.reports_dir = get_reports_path()
        self.allure_results_dir = get_allure_results_path()
        self.allure_report_dir = get_allure_report_path()
        os.makedirs(self.allure_results_dir, exist_ok=True)
        os.makedirs(self.allure_report_dir, exist_ok=True)

    def _get_python_executable(self) -> str:
        """获取Python可执行文件路径"""
        if sys.executable and 'python' in sys.executable.lower():
            return sys.executable
        venv_python = get_venv_scripts_path('python.exe')
        if os.path.exists(venv_python):
            return venv_python
        return 'python'

    def _get_pytest_path(self) -> str:
        """获取pytest可执行文件路径"""
        venv_pytest = get_venv_scripts_path('pytest.exe')
        if os.path.exists(venv_pytest):
            return venv_pytest
        return 'pytest'

    def _get_allure_path(self) -> Optional[str]:
        """获取allure可执行文件路径"""
        allure_exe = shutil.which('allure')
        if allure_exe:
            return allure_exe
        venv_allure = get_venv_scripts_path('allure.exe')
        if os.path.exists(venv_allure):
            return venv_allure
        return None

    def execute_task(self, task_id: int, test_type: str, test_path: str = None,
                     env_config: Dict = None, timeout: int = 3600, trigger_type: str = 'manual') -> str:
        """执行测试任务"""
        execution_id = str(uuid.uuid4())

        if test_path is None:
            test_path = self.TEST_TYPE_MAPPING.get(test_type, 'test_api')

        execution_info = {
            'execution_id': execution_id,
            'task_id': task_id,
            'test_type': test_type,
            'test_path': test_path,
            'env_config': env_config or {},
            'timeout': timeout,
            'status': 'pending',
            'start_time': None,
            'end_time': None,
            'process': None,
            'thread': None,
            'log_lines': [],
            'result_summary': None,
            'exit_code': None,
            'trigger_type': trigger_type,
            'report_url': None
        }

        self.running_executions[execution_id] = execution_info

        try:
            from backend.models.execution import Execution
            from backend.models.task import Task

            task_name = None
            test_scene = 'other'
            try:
                task = Task.find_by_id(task_id)
                if task:
                    task_name = task.get('name')
                    test_scene = task.get('test_scene', 'other')
            except Exception as e:
                logger.warning(f"获取任务信息失败: {e}")

            if test_scene == 'other' and env_config:
                test_scene = env_config.get('test_scene', 'other')

            exec_record_id, run_number = Execution.create(
                execution_id, task_id, trigger_type='manual',
                test_type=test_type, test_scene=test_scene, task_name=task_name
            )

            execution_info['id'] = exec_record_id
            execution_info['task_name'] = task_name
            execution_info['test_scene'] = test_scene
            execution_info['run_number'] = run_number

            logger.info(f"执行记录已创建: id={exec_record_id}, execution_id={execution_id}, task_id={task_id}")
        except Exception as e:
            logger.error(f"创建执行记录失败: {e}")
            # 如果创建执行记录失败，标记执行信息为失败状态
            execution_info['status'] = 'failed'
            execution_info['result_summary'] = {
                'total': 0, 'passed': 0, 'failed': 0,
                'skipped': 0, 'errors': 0, 'duration': 0,
                'error_message': f'创建执行记录失败: {str(e)}'
            }
            # 不启动线程，直接返回
            return execution_id

        thread = threading.Thread(
            target=self._execute_test,
            args=(execution_id,),
            daemon=True
        )
        execution_info['thread'] = thread
        thread.start()

        logger.info(f"测试任务已启动: execution_id={execution_id}, task_id={task_id}, type={test_type}")
        return execution_id

    def _execute_test(self, execution_id: str):
        """执行测试的内部方法"""
        exec_info = self.running_executions[execution_id]

        exec_info['status'] = 'running'
        exec_info['start_time'] = datetime.now().isoformat()

        try:
            self._update_db_status(execution_id, 'running')

            cmd = self._build_command(exec_info['test_type'], exec_info['test_path'], execution_id)
            env = self._build_env(exec_info['env_config'], exec_info['test_type'])

            logger.info(f"执行命令: {cmd}")
            logger.info(f"工作目录: {self.project_root}")
            self._add_log(execution_id, f"执行命令: {cmd}")
            self._add_log(execution_id, f"工作目录: {self.project_root}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                shell=True,
                cwd=self.project_root,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            exec_info['process'] = process

            # 使用线程读取输出，避免阻塞主线程
            import threading
            output_thread = threading.Thread(
                target=self._process_test_output_thread,
                args=(process, execution_id),
                daemon=True
            )
            output_thread.start()

            # 等待进程结束
            exit_code = process.wait()
            exec_info['exit_code'] = exit_code

            # 等待输出线程完成（最多等5秒）
            output_thread.join(timeout=5)

            if exit_code == 0:
                exec_info['status'] = 'success'
                self._add_log(execution_id, "✅ 测试执行成功！")
            else:
                exec_info['status'] = 'failed'
                self._add_log(execution_id, f"❌ 测试执行失败，退出码: {exit_code}")

            exec_info['end_time'] = datetime.now().isoformat()

            # 计算实际执行耗时（秒）
            actual_duration = 0
            if exec_info.get('start_time'):
                start = datetime.fromisoformat(exec_info['start_time'])
                end = datetime.fromisoformat(exec_info['end_time'])
                actual_duration = int((end - start).total_seconds())

            # 生成摘要，异常不影响状态更新
            try:
                self._generate_summary(execution_id)
            except Exception as e:
                logger.error(f"生成摘要失败: {e}")
                if not exec_info.get('result_summary'):
                    exec_info['result_summary'] = {
                        'total': 0, 'passed': 0, 'failed': 0,
                        'skipped': 0, 'errors': 1, 'duration': actual_duration,
                        'error_message': f'生成摘要失败: {str(e)}'
                    }

            # 如果进程失败且没有测试用例结果，将错误记录到 errors
            if exit_code != 0:
                result_summary = exec_info.get('result_summary') or {}
                # 如果没有用例结果（total为0），说明进程启动就失败了
                if result_summary.get('total', 0) == 0:
                    result_summary['errors'] = (result_summary.get('errors', 0) or 0) + 1
                    result_summary['total'] = 1
                    if 'error_message' not in result_summary:
                        result_summary['error_message'] = f'测试进程异常退出，退出码: {exit_code}'
                    exec_info['result_summary'] = result_summary
                    # 保存一条错误用例结果到数据库，确保报告页面能显示
                    try:
                        from backend.models.test_case_result import TestCaseResult
                        TestCaseResult.create(
                            execution_id=execution_id,
                            case_name='test_execution',
                            case_path=exec_info.get('test_path', 'unknown'),
                            status='error',
                            duration=0,
                            error_message=f'测试进程异常退出，退出码: {exit_code}'
                        )
                    except Exception as e2:
                        logger.error(f"保存错误用例结果失败: {e2}")

            # 确保result_summary中有duration（优先使用实际计算的耗时）
            if not exec_info.get('result_summary'):
                exec_info['result_summary'] = {}
            if actual_duration > 0:
                exec_info['result_summary']['duration'] = actual_duration
            exec_info['duration'] = exec_info['result_summary'].get('duration', actual_duration)

            # 生成测试报告数据并存储到数据库（不生成文件到report文件夹）
            try:
                self._create_report_record(execution_id, exec_info)
                self._add_log(execution_id, "📊 测试报告已保存到数据库")
            except Exception as e:
                logger.error(f"保存报告到数据库失败: {e}")

            # 调试日志：检查 result_summary 内容
            result_summary = exec_info.get('result_summary')
            logger.info(f"准备更新数据库状态: execution_id={execution_id}, status={exec_info['status']}, result_summary={result_summary}")
            
            self._update_db_status(execution_id, exec_info['status'], result_summary)
            logger.info(f"数据库状态更新完成: execution_id={execution_id}")

        except Exception as e:
            logger.error(f"测试执行异常: {e}", exc_info=True)
            exec_info['status'] = 'failed'
            exec_info['end_time'] = datetime.now().isoformat()

            if not exec_info.get('result_summary'):
                exec_info['result_summary'] = {}

            if exec_info.get('start_time'):
                start_time = datetime.fromisoformat(exec_info['start_time'])
                end_time = datetime.fromisoformat(exec_info['end_time'])
                duration = int((end_time - start_time).total_seconds())
                exec_info['result_summary']['duration'] = duration
                exec_info['duration'] = duration

            self._add_log(execution_id, f"❌ 测试执行异常: {str(e)}")
            self._update_db_status(execution_id, 'failed', exec_info.get('result_summary'))

        finally:
            # 注意：不要在 finally 中删除 running_executions
            # 因为 _update_db_status 可能在 except 中被调用，需要 exec_info 仍然存在
            # 由调用方或定时清理机制负责清理
            logger.info(f"执行线程结束: execution_id={execution_id}, final_status={exec_info.get('status')}")
            pass

    def _process_test_output_thread(self, process, execution_id: str):
        """在线程中处理测试输出并保存用例结果

        支持多种pytest输出格式：
        1. 单行模式: tests/test.py::TestClass::test_method PASSED
        2. 跨行模式: tests/test.py::TestClass::test_method (日志...) 然后单独一行 PASSED/FAILED
        3. 带时间戳: 2026-05-21 16:31:36 | INFO | tests/test.py::TestClass::test_method PASSED
        """
        from backend.models.test_case_result import TestCaseResult

        case_start_time = None
        lines_processed = 0
        cases_found = 0
        pending_case_path = None

        # 匹配用例路径（支持前面有时间戳或日志前缀）
        # 格式: tests/test_ui/test_user_ui.py::TestUserUI::test_login[case0]
        test_path_pattern = re.compile(
            r'((?:tests/)?[\w/.-]+(?:::[\w\[\]]+)+)'
        )
        # 匹配用例路径+状态（同一行）
        test_complete_pattern = re.compile(
            r'((?:tests/)?[\w/.-]+(?:::[\w\[\]]+)+)\s+(PASSED|FAILED|SKIPPED|ERROR)(?:\s+.*)?$'
        )
        # 匹配单独的状态行（可能前面有时间戳）
        status_only_pattern = re.compile(
            r'(?:^|\s)(PASSED|FAILED|SKIPPED|ERROR)(?:\s+\[\s*\d+%\])?(?:\s*$)'
        )

        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    remaining = process.stdout.read()
                    if remaining:
                        for remaining_line in remaining.splitlines():
                            self._process_output_line(remaining_line.strip(), execution_id)
                    break

                line_str = line.strip()
                if not line_str:
                    continue

                lines_processed += 1
                self._add_log(execution_id, line_str)
                self._notify_callbacks(execution_id, line_str)

                # 先尝试匹配完整的单行模式（用例路径+状态在同一行）
                match_complete = test_complete_pattern.search(line_str)
                if match_complete:
                    case_path = match_complete.group(1)
                    status_str = match_complete.group(2)
                    pending_case_path = None

                    case_name = case_path.split('::')[-1]
                    status = self._map_pytest_status(status_str)

                    if case_start_time:
                        duration = (datetime.now() - case_start_time).total_seconds()
                    else:
                        duration = 0.0

                    try:
                        TestCaseResult.create(
                            execution_id=execution_id,
                            case_name=case_name,
                            case_path=case_path,
                            status=status,
                            duration=round(duration, 3)
                        )
                        cases_found += 1
                        logger.info(f"保存测试用例结果(单行): {case_name} = {status}, duration={duration:.3f}s")
                    except Exception as e:
                        logger.error(f"保存用例结果失败: {e}")

                    case_start_time = datetime.now()
                    continue

                # 尝试匹配用例开始行（跨行模式）
                # 确保这一行不包含 PASSED/FAILED/SKIPPED/ERROR
                if not re.search(r'\b(PASSED|FAILED|SKIPPED|ERROR)\b', line_str):
                    match_start = test_path_pattern.search(line_str)
                    if match_start:
                        # 验证这是一个有效的pytest用例路径（包含 ::）
                        path = match_start.group(1)
                        if '::' in path:
                            pending_case_path = path
                            continue

                # 尝试匹配状态行（跨行模式）
                match_status = status_only_pattern.search(line_str)
                if match_status and pending_case_path:
                    status_str = match_status.group(1)
                    case_path = pending_case_path
                    pending_case_path = None

                    case_name = case_path.split('::')[-1]
                    status = self._map_pytest_status(status_str)

                    if case_start_time:
                        duration = (datetime.now() - case_start_time).total_seconds()
                    else:
                        duration = 0.0

                    try:
                        TestCaseResult.create(
                            execution_id=execution_id,
                            case_name=case_name,
                            case_path=case_path,
                            status=status,
                            duration=round(duration, 3)
                        )
                        cases_found += 1
                        logger.info(f"保存测试用例结果(跨行): {case_name} = {status}, duration={duration:.3f}s")
                    except Exception as e:
                        logger.error(f"保存用例结果失败: {e}")

                    case_start_time = datetime.now()
                    continue

                if 'test session starts' in line_str:
                    case_start_time = datetime.now()

            logger.info(f"输出处理线程结束: execution_id={execution_id}, lines_processed={lines_processed}, cases_found={cases_found}")
        except Exception as e:
            logger.error(f"输出处理线程异常: {e}", exc_info=True)

    def _process_output_line(self, line_str: str, execution_id: str):
        """处理单行输出（用于读取剩余输出）"""
        from backend.models.test_case_result import TestCaseResult

        if not line_str:
            return

        self._add_log(execution_id, line_str)
        self._notify_callbacks(execution_id, line_str)

        # 尝试匹配完整的单行模式
        test_complete_pattern = re.compile(r'^((?:tests/)?[\w/.-]+(?:::[\w\[\]]+)+)\s+(PASSED|FAILED|SKIPPED|ERROR)(?:\s+.*)?$')
        match = test_complete_pattern.match(line_str)
        if match:
            case_path = match.group(1)
            status_str = match.group(2)
            case_name = case_path.split('::')[-1]
            status = self._map_pytest_status(status_str)

            try:
                TestCaseResult.create(
                    execution_id=execution_id,
                    case_name=case_name,
                    case_path=case_path,
                    status=status,
                    duration=0.0
                )
                logger.info(f"保存测试用例结果(剩余输出): {case_name} = {status}")
            except Exception as e:
                logger.error(f"保存用例结果失败(剩余输出): {e}")

    def _map_pytest_status(self, pytest_status: str) -> str:
        """映射pytest状态到我们的状态"""
        status_map = {
            'PASSED': 'passed',
            'FAILED': 'failed',
            'SKIPPED': 'skipped',
            'ERROR': 'error'
        }
        return status_map.get(pytest_status, 'broken')

    def _update_db_status(self, execution_id: str, status: str, result_summary: dict = None):
        """更新数据库中的执行状态 - 确保状态更新绝对可靠"""
        try:
            from backend.models.execution import Execution
            from backend.models.task import Task

            logger.info(f"_update_db_status 开始: execution_id={execution_id}, status={status}")

            exec_record = Execution.find_by_execution_id(execution_id)
            if not exec_record:
                logger.error(f"找不到执行记录: execution_id={execution_id}")
                return

            task_id = exec_record.get('task_id')
            logger.info(f"找到执行记录: execution_id={execution_id}, task_id={task_id}, current_db_status={exec_record.get('status')}")

            if status in ['success', 'failed', 'stopped']:
                logger.info(f"更新执行记录为完成状态: execution_id={execution_id}, status={status}")
                try:
                    Execution.complete(execution_id, status, result_summary)
                    logger.info(f"执行记录更新完成: execution_id={execution_id}")
                except Exception as e1:
                    logger.error(f"Execution.complete 失败，尝试降级更新: {e1}")
                    # 降级：至少更新状态和结束时间
                    Execution.update_status(execution_id, status)
                    logger.info(f"降级更新执行状态完成: execution_id={execution_id}")

                if task_id:
                    try:
                        logger.info(f"更新任务状态为 idle: task_id={task_id}")
                        Task.update_status(task_id, 'idle')
                        logger.info(f"任务状态更新完成: task_id={task_id}")
                    except Exception as e2:
                        logger.error(f"更新任务状态失败: task_id={task_id}, error={e2}")
            else:
                logger.info(f"更新执行记录为运行状态: execution_id={execution_id}, status={status}")
                Execution.update_status(execution_id, status, result_summary)
                if task_id:
                    Task.update_status(task_id, 'running')
        except Exception as e:
            logger.error(f"更新数据库状态失败: {e}", exc_info=True)

    def _create_report_record(self, execution_id: str, exec_info: dict):
        """创建报告记录 - 仅存储到数据库，不生成文件"""
        try:
            from backend.models.report import Report
            from backend.models.execution import Execution
            from backend.models.test_case_result import TestCaseResult
            from backend.utils.database import Database
            import json

            summary = exec_info.get('result_summary')
            test_type = exec_info.get('test_type', 'unknown')

            # 生成报告名称：时间戳_测试类型
            start_time = exec_info.get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    # 尝试解析ISO格式时间字符串
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        timestamp_str = dt.strftime('%Y%m%d_%H%M%S')
                    except:
                        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                else:
                    timestamp_str = start_time.strftime('%Y%m%d_%H%M%S')
            else:
                from datetime import datetime
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')

            report_name = f"{timestamp_str}_{test_type}"

            # 从数据库获取详细的测试用例结果作为报告数据
            case_results = TestCaseResult.find_by_execution(execution_id)
            report_data = {
                'execution_id': execution_id,
                'task_id': exec_info.get('task_id'),
                'task_name': exec_info.get('task_name'),
                'status': exec_info.get('status'),
                'start_time': exec_info.get('start_time'),
                'end_time': exec_info.get('end_time'),
                'duration': exec_info.get('duration', 0),
                'case_results': case_results or []
            }

            Report.create(
                execution_id=execution_id,
                report_type='allure',
                summary=summary,
                report_url=None,  # 不生成文件URL
                task_id=exec_info.get('task_id'),
                report_name=report_name
            )

            # 同时更新test_execution表的result_summary字段
            try:
                sql = "UPDATE test_execution SET result_summary = %s WHERE execution_id = %s"
                Database.execute_update(sql, (json.dumps(summary) if summary else None, execution_id))
            except Exception as e:
                logger.error(f"更新执行记录报告数据失败: {e}")

            logger.info(f"报告记录已保存到数据库: execution_id={execution_id}, report_name={report_name}")
        except Exception as e:
            logger.error(f"创建报告记录失败: {e}")

    def _build_command(self, test_type: str, test_path: str, execution_id: str) -> str:
        """构建pytest命令 - 通过平台执行时不生成allure文件，只输出日志"""
        pytest_path = self._get_pytest_path()
        tests_dir = get_tests_path()

        if test_type == 'performance':
            cmd = f'"{self.python_exe}" -m locust -f {os.path.join(tests_dir, test_path)} --headless -u 10 -r 5 --run-time 30s --host http://localhost'
        else:
            test_full_path = os.path.join(tests_dir, test_path)
            cmd = f'"{self.python_exe}" -u -m pytest "{test_full_path}" -v -s --tb=short --capture=no'
        return cmd

    def _build_env(self, env_config: Dict, test_type: str = None) -> Dict:
        """构建环境变量"""
        env = os.environ.copy()

        venv_scripts = get_venv_scripts_path()
        if os.path.exists(venv_scripts):
            env['PATH'] = venv_scripts + os.pathsep + env.get('PATH', '')

        env['PYTHONPATH'] = self.project_root
        env['PYTHONUNBUFFERED'] = '1'
        env['TEST_PLATFORM_EXECUTION'] = '1'

        for key, value in env_config.items():
            env[key] = str(value)

        return env

    def _generate_allure_report_from_db(self, execution_id: str) -> Optional[str]:
        """生成Allure报告 - 优先使用pytest生成的allure结果文件"""
        allure_results = os.path.join(self.allure_results_dir, execution_id)
        if os.path.exists(allure_results) and os.listdir(allure_results):
            logger.info(f"找到pytest生成的allure结果: {allure_results}")
        else:
            logger.warning(f"pytest未生成allure结果，尝试从数据库生成: {execution_id}")
            # 备用：从数据库生成allure结果文件
            from backend.services.allure_report_generator import AllureReportGenerator
            generator = AllureReportGenerator(self.project_root)
            allure_results = generator.generate_from_db(execution_id)
            if not allure_results:
                return None

        # 第二步：生成HTML报告
        allure_path = self._get_allure_path()
        if not allure_path:
            logger.error("未找到allure命令行工具，无法生成HTML报告")
            return f"/reports/allure-results/{execution_id}/"

        try:
            report_output_dir = os.path.join(self.allure_report_dir, execution_id)
            os.makedirs(report_output_dir, exist_ok=True)

            import subprocess
            cmd = f'"{allure_path}" generate "{allure_results}" -o "{report_output_dir}" --clean'
            logger.info(f"生成Allure报告: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info(f"Allure报告生成成功: {report_output_dir}")
                return f"/reports/allure-report/{execution_id}/index.html"
            else:
                logger.error(f"Allure报告生成失败: {result.stderr}")
                return f"/reports/allure-results/{execution_id}/"

        except Exception as e:
            logger.error(f"生成Allure报告异常: {e}")
            return f"/reports/allure-results/{execution_id}/"

    def _add_log(self, execution_id: str, message: str):
        """添加日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message
        }

        if execution_id in self.running_executions:
            self.running_executions[execution_id]['log_lines'].append(log_entry)

        try:
            from backend.utils.database import Database
            sql = """
                INSERT INTO execution_log (execution_id, log_level, message, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            Database.execute_insert(sql, (execution_id, 'INFO', message, datetime.now()))
        except Exception as e:
            logger.error(f"写入日志到数据库失败: {e}")

    def _generate_summary(self, execution_id: str):
        """从数据库生成测试结果摘要"""
        try:
            from backend.models.test_case_result import TestCaseResult

            summary = TestCaseResult.get_summary(execution_id)
            if summary:
                total_duration = summary.get('total_duration', 0)
                if total_duration is None:
                    total_duration = 0
                else:
                    total_duration = float(total_duration)
                self.running_executions[execution_id]['result_summary'] = {
                    'total': summary.get('total', 0),
                    'passed': summary.get('passed', 0),
                    'failed': summary.get('failed', 0),
                    'skipped': summary.get('skipped', 0),
                    'errors': summary.get('errors', 0),
                    'duration': int(total_duration)
                }
        except Exception as e:
            logger.error(f"生成测试摘要失败: {e}")

    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """获取执行状态"""
        if execution_id in self.running_executions:
            exec_info = self.running_executions[execution_id]
            # 如果内存中的状态是终态，但数据库可能还没更新，优先返回内存状态
            return {
                'execution_id': execution_id,
                'task_id': exec_info['task_id'],
                'test_type': exec_info['test_type'],
                'test_path': exec_info['test_path'],
                'status': exec_info['status'],
                'start_time': exec_info['start_time'],
                'end_time': exec_info['end_time'],
                'result_summary': exec_info['result_summary'],
                'exit_code': exec_info['exit_code'],
                'report_url': exec_info.get('report_url')
            }
        return None

    def cleanup_execution(self, execution_id: str):
        """清理已完成的执行记录"""
        if execution_id in self.running_executions:
            exec_info = self.running_executions[execution_id]
            # 只有终态才清理
            if exec_info.get('status') in ['success', 'failed', 'stopped']:
                del self.running_executions[execution_id]
                logger.info(f"清理已完成执行记录: execution_id={execution_id}")
                return True
        return False

    def get_execution_logs(self, execution_id: str, offset: int = 0, limit: int = 100) -> List[Dict]:
        """获取执行日志"""
        if execution_id in self.running_executions:
            log_lines = self.running_executions[execution_id]['log_lines']
            if log_lines:
                return log_lines[offset:offset + limit]

        try:
            from backend.utils.database import Database
            sql = """
                SELECT id, log_level, message, timestamp
                FROM execution_log
                WHERE execution_id = %s
                ORDER BY id ASC
                LIMIT %s OFFSET %s
            """
            results = Database.execute_query(sql, (execution_id, limit, offset))
            if results:
                return [
                    {
                        'timestamp': r['timestamp'].isoformat() if r.get('timestamp') else datetime.now().isoformat(),
                        'message': r['message']
                    }
                    for r in results
                ]
        except Exception as e:
            logger.error(f"从数据库获取日志失败: {e}")

        return []

    def stop_execution(self, execution_id: str) -> bool:
        """停止执行"""
        if execution_id in self.running_executions:
            exec_info = self.running_executions[execution_id]
            
            # 如果进程还在运行，终止它
            if exec_info.get('process') and exec_info['process'].poll() is None:
                exec_info['process'].terminate()
                try:
                    exec_info['process'].wait(timeout=5)
                except:
                    pass
            
            # 无论进程是否已结束，都更新状态为 stopped
            exec_info['status'] = 'stopped'
            exec_info['end_time'] = datetime.now().isoformat()
            
            if not exec_info.get('result_summary'):
                exec_info['result_summary'] = {
                    'total': 0, 'passed': 0, 'failed': 0,
                    'skipped': 0, 'errors': 0, 'duration': 0
                }
            
            self._update_db_status(execution_id, 'stopped', exec_info.get('result_summary'))
            self._add_log(execution_id, "执行已被停止")
            logger.info(f"测试执行已停止: {execution_id}")
            return True
        
        # 内存中没有，尝试从数据库更新
        try:
            from backend.models.execution import Execution
            db_record = Execution.find_by_execution_id(execution_id)
            if db_record and db_record.get('status') == 'running':
                summary = {
                    'total': 0, 'passed': 0, 'failed': 0,
                    'skipped': 0, 'errors': 0, 'duration': 0
                }
                self._update_db_status(execution_id, 'stopped', summary)
                return True
        except Exception as e:
            logger.error(f"从数据库停止执行失败: {e}")
        
        return False

    def register_log_callback(self, execution_id: str, callback: Callable):
        """注册日志回调"""
        if execution_id not in self.log_callbacks:
            self.log_callbacks[execution_id] = []
        self.log_callbacks[execution_id].append(callback)

    def unregister_log_callback(self, execution_id: str, callback: Callable):
        """取消注册日志回调"""
        if execution_id in self.log_callbacks:
            self.log_callbacks[execution_id].remove(callback)

    def _notify_callbacks(self, execution_id: str, message: str):
        """通知回调"""
        if execution_id in self.log_callbacks:
            for callback in self.log_callbacks[execution_id]:
                try:
                    callback(execution_id, message)
                except Exception as e:
                    logger.error(f"回调通知失败: {e}")


executor = TestExecutor()
