"""
测试执行引擎 - 核心模块
负责执行测试任务，支持多类型测试
"""
import os
import sys
import subprocess
import threading
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.tools.path_manager import get_path, get_web_platform_path

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

    def _get_python_executable(self) -> str:
        """获取Python可执行文件路径"""
        if sys.executable and 'python' in sys.executable.lower():
            return sys.executable

        venv_python = os.path.join(self.project_root, '.venv', 'Scripts', 'python.exe')
        if os.path.exists(venv_python):
            return venv_python

        return 'python'

    def _get_pytest_path(self) -> str:
        """获取pytest可执行文件路径"""
        venv_pytest = os.path.join(self.project_root, '.venv', 'Scripts', 'pytest.exe')
        if os.path.exists(venv_pytest):
            return venv_pytest

        return 'pytest'

    def execute_task(self, task_id: int, test_type: str, test_path: str = None,
                    env_config: Dict = None, timeout: int = 3600) -> str:
        """
        执行测试任务

        Args:
            task_id: 任务ID
            test_type: 测试类型（api, ui, smoke, android等）
            test_path: 测试路径（相对tests目录）
            env_config: 环境配置
            timeout: 超时时间（秒）

        Returns:
            execution_id: 执行ID
        """
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
            'exit_code': None
        }

        self.running_executions[execution_id] = execution_info

        try:
            from backend.models.execution import Execution
            Execution.create(execution_id, task_id, trigger_type='manual')
            logger.info(f"执行记录已创建: execution_id={execution_id}, task_id={task_id}")
        except Exception as e:
            logger.error(f"创建执行记录失败: {e}")

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
            # 将执行开始状态写入数据库
            self._update_db_status(execution_id, 'running')

            cmd = self._build_command(exec_info['test_type'], exec_info['test_path'])
            env = self._build_env(exec_info['env_config'])

            logger.info(f"执行命令: {cmd}")
            logger.info(f"工作目录: {self.project_root}")
            self._add_log(execution_id, f"执行命令: {cmd}")
            self._add_log(execution_id, f"工作目录: {self.project_root}")
            self._add_log(execution_id, f"Python路径: {self.python_exe}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                shell=True,
                cwd=self.project_root,
                text=True
            )

            exec_info['process'] = process

            for line in iter(process.stdout.readline, ''):
                if line:
                    line_str = line.strip()
                    if line_str:
                        self._add_log(execution_id, line_str)
                        self._notify_callbacks(execution_id, line_str)

            process.wait()
            exec_info['exit_code'] = process.returncode

            if process.returncode == 0:
                exec_info['status'] = 'success'
                self._add_log(execution_id, "✅ 测试执行成功！")
            else:
                exec_info['status'] = 'failed'
                self._add_log(execution_id, f"❌ 测试执行失败，退出码: {process.returncode}")

            exec_info['end_time'] = datetime.now().isoformat()

            self._generate_summary(execution_id)

            # 将执行完成状态写入数据库
            self._update_db_status(execution_id, exec_info['status'], exec_info['result_summary'])

        except Exception as e:
            logger.error(f"测试执行异常: {e}", exc_info=True)
            exec_info['status'] = 'failed'
            exec_info['end_time'] = datetime.now().isoformat()
            self._add_log(execution_id, f"❌ 测试执行异常: {str(e)}")
            self._add_log(execution_id, f"详细错误: {sys.exc_info()[0]}")
            self._update_db_status(execution_id, 'failed')

    def _update_db_status(self, execution_id: str, status: str, result_summary: dict = None):
        """更新数据库中的执行状态 - 同时更新 execution 和 task 表"""
        try:
            from backend.models.execution import Execution
            from backend.models.task import Task
            
            # 获取执行记录以获取 task_id
            exec_record = Execution.find_by_execution_id(execution_id)
            task_id = exec_record['task_id'] if exec_record else None
            
            if status in ['success', 'failed', 'stopped']:
                # 执行完成时使用 complete 方法
                Execution.complete(execution_id, status, result_summary)
                # 更新任务状态为空闲
                if task_id:
                    Task.update(task_id, status='idle')
            else:
                # 执行开始或进行中
                Execution.update_status(execution_id, status, result_summary)
                # 更新任务状态为运行中
                if task_id:
                    Task.update(task_id, status='running')
            logger.info(f"数据库状态已更新: execution_id={execution_id}, status={status}, task_id={task_id}")
        except Exception as e:
            logger.error(f"更新数据库状态失败: {e}")

    def _build_command(self, test_type: str, test_path: str) -> str:
        """构建pytest命令"""
        pytest_path = self._get_pytest_path()
        tests_dir = os.path.join(self.project_root, 'tests')

        if test_type == 'performance':
            cmd = f'"{self.python_exe}" -m locust -f {os.path.join(tests_dir, test_path)} --headless -u 10 -r 5 --run-time 30s --host http://localhost'
        else:
            test_full_path = os.path.join(tests_dir, test_path)
            cmd = f'"{pytest_path}" "{test_full_path}" -v --tb=short'

        return cmd

    def _build_env(self, env_config: Dict) -> Dict:
        """构建环境变量"""
        env = os.environ.copy()

        venv_scripts = os.path.join(self.project_root, '.venv', 'Scripts')
        if os.path.exists(venv_scripts):
            env['PATH'] = venv_scripts + os.pathsep + env.get('PATH', '')

        env['PYTHONPATH'] = self.project_root

        for key, value in env_config.items():
            env[key] = str(value)

        return env

    def _add_log(self, execution_id: str, message: str):
        """添加日志 - 同时写入内存和数据库"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        # 写入内存
        if execution_id in self.running_executions:
            self.running_executions[execution_id]['log_lines'].append(log_entry)
        
        # 写入数据库
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
        """生成测试结果摘要"""
        exec_info = self.running_executions[execution_id]
        log_lines = exec_info['log_lines']

        summary = {
            'total_lines': len(log_lines),
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'duration': None
        }

        for line in log_lines:
            msg = line.get('message', '')
            if 'PASSED' in msg or '✅' in msg or 'passed' in msg.lower():
                summary['passed'] += 1
            elif 'FAILED' in msg or '❌' in msg or 'failed' in msg.lower():
                summary['failed'] += 1
            elif 'SKIPPED' in msg or 'skipped' in msg.lower():
                summary['skipped'] += 1
            elif 'ERROR' in msg or '错误' in msg:
                summary['errors'] += 1

        if exec_info['start_time'] and exec_info['end_time']:
            start = datetime.fromisoformat(exec_info['start_time'])
            end = datetime.fromisoformat(exec_info['end_time'])
            summary['duration'] = int((end - start).total_seconds())

        exec_info['result_summary'] = summary

    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """获取执行状态"""
        if execution_id in self.running_executions:
            exec_info = self.running_executions[execution_id]
            return {
                'execution_id': execution_id,
                'task_id': exec_info['task_id'],
                'test_type': exec_info['test_type'],
                'test_path': exec_info['test_path'],
                'status': exec_info['status'],
                'start_time': exec_info['start_time'],
                'end_time': exec_info['end_time'],
                'result_summary': exec_info['result_summary'],
                'exit_code': exec_info['exit_code']
            }
        return None

    def get_execution_logs(self, execution_id: str, offset: int = 0, limit: int = 100) -> List[Dict]:
        """获取执行日志 - 优先从内存，备选从数据库"""
        # 优先从内存获取（实时日志）
        if execution_id in self.running_executions:
            log_lines = self.running_executions[execution_id]['log_lines']
            if log_lines:
                return log_lines[offset:offset + limit]
        
        # 从数据库获取（历史日志）
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
                        'timestamp': row['timestamp'].isoformat() if row.get('timestamp') else datetime.now().isoformat(),
                        'message': row['message']
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"从数据库获取日志失败: {e}")
        
        return []

    def stop_execution(self, execution_id: str) -> bool:
        """停止执行"""
        if execution_id in self.running_executions:
            exec_info = self.running_executions[execution_id]
            if exec_info['process']:
                exec_info['process'].terminate()
                exec_info['status'] = 'stopped'
                exec_info['end_time'] = datetime.now().isoformat()
                logger.info(f"测试执行已停止: {execution_id}")
                return True
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
