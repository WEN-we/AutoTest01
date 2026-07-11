"""
Allure报告生成工具
支持从数据库测试用例结果生成Allure报告
"""
import os
import sys
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from backend.utils.database import Database

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.tools.path_manager import (
    get_path, get_reports_path, get_allure_results_path,
    get_allure_report_path, get_venv_scripts_path
)


class AllureReportGenerator:
    """Allure报告生成器"""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or get_path()
        self.reports_dir = get_reports_path()
        self.allure_results_dir = get_allure_results_path()
        self.allure_report_dir = get_allure_report_path()
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.allure_results_dir, exist_ok=True)
        os.makedirs(self.allure_report_dir, exist_ok=True)

    def generate_from_db(self, execution_id: str, output_dir: str = None) -> str:
        """从数据库生成Allure报告
        Args:
            execution_id: 执行UUID
            output_dir: 输出目录（可选，默认 reports/allure-results/{execution_id}）
        Returns:
            报告结果目录路径
        """
        if output_dir is None:
            output_dir = os.path.join(self.allure_results_dir, execution_id)
        os.makedirs(output_dir, exist_ok=True)

        # 获取测试用例结果
        case_results = self._get_case_results_from_db(execution_id)

        # 生成Allure JSON文件
        self._generate_allure_json(case_results, output_dir, execution_id)

        # 生成环境信息
        self._generate_environment_json(output_dir)

        # 生成categories.json
        self._generate_categories_json(output_dir)

        # 生成executor.json
        self._generate_executor_json(output_dir, execution_id)

        return output_dir

    def _get_case_results_from_db(self, execution_id: str) -> List[Dict]:
        """从数据库获取测试用例结果"""
        sql = """
            SELECT * FROM test_case_result
            WHERE execution_id = %s
            ORDER BY id
        """
        return Database.execute_query(sql, (execution_id,))

    def _generate_allure_json(self, case_results: List[Dict], output_dir: str, execution_id: str):
        """生成Allure JSON结果文件"""
        from datetime import datetime, timedelta

        for i, case in enumerate(case_results):
            test_result = self._convert_to_allure_result(case, execution_id)
            test_uuid = str(uuid.uuid4())
            with open(os.path.join(output_dir, f"{test_uuid}-result.json"), 'w', encoding='utf-8') as f:
                json.dump(test_result, f, ensure_ascii=False, indent=2)

    def _convert_to_allure_result(self, case: Dict, execution_id: str) -> Dict:
        """转换为Allure结果格式"""
        # Allure状态映射
        status_map = {
            'passed': 'passed',
            'failed': 'failed',
            'skipped': 'skipped',
            'error': 'broken',
            'broken': 'broken'
        }

        allure_status = status_map.get(case['status'], 'broken')

        # 构建结果对象
        result = {
            'uuid': str(uuid.uuid4()),
            'name': case['case_name'],
            'fullName': case['case_path'],
            'historyId': f"{case['case_path']}-{execution_id}",
            'status': allure_status,
            'statusDetails': {},
            'stage': 'finished',
            'start': int((datetime.now().timestamp() - case.get('duration', 0)) * 1000),
            'stop': int(datetime.now().timestamp() * 1000),
            'labels': [
                {
                    'name': 'suite',
                    'value': self._extract_suite(case['case_path'])
                },
                {
                    'name': 'parentSuite',
                    'value': self._extract_parent_suite(case['case_path'])
                }
            ],
            'links': [],
            'parameters': []
        }

        # 添加状态详情
        if allure_status in ['failed', 'broken']:
            result['statusDetails'] = {
                'known': False,
                'muted': False,
                'flaky': False,
                'message': case.get('error_message', ''),
                'trace': case.get('stack_trace', '')
            }

        # 添加附件
        if case.get('stdout'):
            self._add_attachment(result, 'stdout', case['stdout'], 'text/plain')
        if case.get('stderr'):
            self._add_attachment(result, 'stderr', case['stderr'], 'text/plain')

        return result

    def _extract_suite(self, case_path: str) -> str:
        """从测试路径提取测试套件"""
        parts = case_path.replace('::', '/').split('/')
        if len(parts) >= 2:
            return parts[-2] if parts[-1] else parts[-3]
        return 'Tests'

    def _extract_parent_suite(self, case_path: str) -> str:
        """从测试路径提取父套件"""
        parts = case_path.replace('::', '/').split('/')
        if len(parts) >= 3:
            return parts[-3]
        return 'Test Suite'

    def _add_attachment(self, result: Dict, name: str, content: str, mime_type: str):
        """添加附件"""
        if 'attachments' not in result:
            result['attachments'] = []

        attachment_uuid = str(uuid.uuid4())
        attachment_file = f"{attachment_uuid}.txt"
        result['attachments'].append({
            'name': name,
            'type': mime_type,
            'source': attachment_file
        })

        # 保存附件内容（实际应用中需要保存到文件）
        pass

    def _generate_environment_json(self, output_dir: str):
        """生成environment.properties"""
        env_content = """
Python={python_version}
Platform={platform}
AllureVersion={allure_version}
        """.strip().format(
            python_version=os.sys.version,
            platform=os.sys.platform,
            allure_version='2.25.0'
        )
        with open(os.path.join(output_dir, 'environment.properties'), 'w', encoding='utf-8') as f:
            f.write(env_content)

    def _generate_categories_json(self, output_dir: str):
        """生成categories.json"""
        categories = [
            {
                'name': 'Product defects',
                'matchedStatuses': ['failed'],
                'description': 'Tests that failed, usually due to a product defect'
            },
            {
                'name': 'Test defects',
                'matchedStatuses': ['broken'],
                'description': 'Tests that are broken'
            },
            {
                'name': 'Skipped',
                'matchedStatuses': ['skipped'],
                'description': 'Tests that are skipped'
            }
        ]
        with open(os.path.join(output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

    def _generate_executor_json(self, output_dir: str, execution_id: str):
        """生成executor.json"""
        executor = {
            'name': 'Test Automation Platform',
            'type': 'test_platform',
            'url': 'http://localhost:8081',
            'buildOrder': int(execution_id[:8], 16) if execution_id and len(execution_id) >= 8 else 1,
            'buildName': f"Build {execution_id[:8]}" if execution_id else "Build",
            'reportUrl': f"http://localhost:8081/reports/allure-report/{execution_id}/index.html"
        }
        with open(os.path.join(output_dir, 'executor.json'), 'w', encoding='utf-8') as f:
            json.dump(executor, f, ensure_ascii=False, indent=2)

    def generate_html_report(self, results_dir: str, output_dir: str = None) -> str:
        """生成Allure HTML报告
        Args:
            results_dir: Allure结果目录
            output_dir: 输出目录（可选，默认 reports/allure-report/{execution_id}）
        Returns:
            报告HTML路径
        """
        if output_dir is None:
            execution_id = os.path.basename(results_dir)
            output_dir = os.path.join(self.allure_report_dir, execution_id)

        allure_path = self._get_allure_path()
        if not allure_path:
            return None

        try:
            import subprocess
            os.makedirs(output_dir, exist_ok=True)
            cmd = f'"{allure_path}" generate "{results_dir}" -o "{output_dir}" --clean'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return os.path.join(output_dir, 'index.html')
            else:
                return None

        except Exception as e:
            return None

    def _get_allure_path(self) -> Optional[str]:
        """获取Allure可执行文件路径"""
        allure_exe = shutil.which('allure')
        if allure_exe:
            return allure_exe
        venv_allure = get_venv_scripts_path('allure.exe')
        if os.path.exists(venv_allure):
            return venv_allure
        return None


class AllureResultsCollector:
    """Allure结果收集器 - 用于自动化测试框架直接使用
    在自动化测试框架中使用此类，可将结果保存到指定路径
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or get_allure_results_path()
        os.makedirs(self.output_dir, exist_ok=True)
        self.case_results = []

    def add_case_result(self, case_name: str, case_path: str, status: str,
                        duration: float = 0.0, stdout: str = None, stderr: str = None,
                        error_type: str = None, error_message: str = None,
                        stack_trace: str = None) -> None:
        """添加测试用例结果"""
        self.case_results.append({
            'case_name': case_name,
            'case_path': case_path,
            'status': status,
            'duration': duration,
            'stdout': stdout,
            'stderr': stderr,
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace
        })

    def save_results(self) -> str:
        """保存结果到指定路径
        Returns:
            结果目录路径
        """
        generator = AllureReportGenerator()
        # 使用临时的execution_id
        execution_id = str(uuid.uuid4())
        return generator._generate_allure_json(self.case_results, self.output_dir, execution_id)
