"""
测试报告生成插件
支持在自动化测试框架直接使用，生成Allure报告到指定路径

功能说明：
- 收集所有测试用例的执行结果到内存中
- 只有当所有测试用例执行完毕后，才统一生成报告
- 不会为每个测试用例单独生成报告

使用方法：
1. 在conftest.py中添加：
    from utils.test_report_plugin import TestReportPlugin
    
    @pytest.fixture(scope='session', autouse=True)
    def test_report():
        plugin = TestReportPlugin(output_dir='./my-allure-results')
        yield plugin
        plugin.generate_report()

2. 或者在pytest.ini中配置：
    [tool:pytest]
    addopts = --alluredir=./allure-results

3. 命令行直接使用：
    pytest tests/ --alluredir=./my-allure-results
    allure serve ./my-allure-results
"""
import os
import sys
import uuid
import json
import pytest
from typing import Dict, List, Optional
from datetime import datetime


class TestReportPlugin:
    """测试报告插件 - 用于自动化测试框架直接使用
    
    核心特性：
    - 所有测试用例结果先保存到内存列表中
    - 只有在 pytest_sessionfinish 钩子中才统一写入文件
    - 确保所有测试用例跑完后才生成报告
    """

    def __init__(self, output_dir: str = None):
        """初始化插件
        
        Args:
            output_dir: 报告输出目录，默认 './allure-results'
        """
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), 'allure-results')
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 存储所有测试用例结果，内存中收集
        self.test_results: List[Dict] = []
        
        # 标记是否已生成报告，防止重复生成
        self._report_generated = False

    def pytest_configure(self, config):
        """pytest配置钩子"""
        config.addinivalue_line(
            "markers", "allure: mark test with allure report"
        )

    def pytest_runtest_logreport(self, report):
        """记录测试结果到内存
        
        注意：这里只是收集结果到内存，不会写入文件
        只有在所有测试结束后才会写入文件
        """
        # 只记录实际的测试执行阶段，不记录setup/teardown
        if report.when == 'call':
            test_case = {
                'name': report.nodeid.split('::')[-1],
                'path': report.nodeid,
                'status': self._map_status(report.outcome),
                'duration': report.duration,
                'stdout': getattr(report, 'capstdout', None),
                'stderr': getattr(report, 'capstderr', None),
                'error_type': None,
                'error_message': None
            }
            
            # 提取错误信息
            if report.longreprtext:
                lines = report.longreprtext.split('\n')
                test_case['error_type'] = lines[0] if lines else 'Error'
                test_case['error_message'] = report.longreprtext
            
            self.test_results.append(test_case)

    def pytest_sessionfinish(self, session, exitstatus):
        """所有测试结束后统一生成报告
        
        这是一个重要的钩子，确保所有测试用例都执行完毕后
        才调用此方法生成报告文件
        """
        if self._report_generated:
            return
        
        self._generate_allure_report()
        self._report_generated = True

    def _map_status(self, outcome) -> str:
        """映射pytest状态到Allure状态"""
        if outcome == 'passed':
            return 'passed'
        elif outcome == 'failed':
            return 'failed'
        elif outcome == 'skipped':
            return 'skipped'
        else:
            return 'broken'

    def _generate_allure_report(self):
        """生成Allure报告文件
        
        重要：这个方法只在所有测试用例执行完毕后调用一次
        它会遍历内存中的所有测试结果，一次性写入文件
        """
        if not self.test_results:
            print(f"没有测试结果需要生成报告")
            return
        
        # 统计信息
        passed = sum(1 for r in self.test_results if r['status'] == 'passed')
        failed = sum(1 for r in self.test_results if r['status'] == 'failed')
        skipped = sum(1 for r in self.test_results if r['status'] == 'skipped')
        
        print(f"\n{'='*60}")
        print(f"正在生成Allure报告...")
        print(f"测试用例总数: {len(self.test_results)}")
        print(f"  - 通过: {passed}")
        print(f"  - 失败: {failed}")
        print(f"  - 跳过: {skipped}")
        print(f"输出目录: {self.output_dir}")
        print(f"{'='*60}\n")
        
        # 为每个测试用例生成一个JSON文件
        for result in self.test_results:
            allure_result = self._convert_to_allure_result(result)
            # Allure要求文件名格式: {uuid}-result.json
            result_uuid = str(uuid.uuid4())
            file_path = os.path.join(self.output_dir, f"{result_uuid}-result.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(allure_result, f, ensure_ascii=False, indent=2)
        
        # 生成附加文件
        self._generate_environment_properties()
        self._generate_categories_json()
        self._generate_executor_json()
        
        print(f"✅ Allure报告已生成: {self.output_dir}")
        print(f"   使用 'allure serve {self.output_dir}' 查看报告")

    def _convert_to_allure_result(self, result: Dict) -> Dict:
        """将测试结果转换为Allure JSON格式"""
        status = result['status']
        
        # 计算时间戳
        now_ms = int(datetime.now().timestamp() * 1000)
        duration_ms = int(result['duration'] * 1000) if result['duration'] else 0
        
        allure_result = {
            'uuid': str(uuid.uuid4()),
            'name': result['name'],
            'fullName': result['path'],
            'historyId': f"{result['path']}",
            'status': status,
            'statusDetails': {
                'known': False,
                'muted': False,
                'flaky': False
            },
            'stage': 'finished',
            'start': now_ms - duration_ms,
            'stop': now_ms,
            'description': '',
            'labels': [
                {'name': 'suite', 'value': self._extract_suite(result['path'])},
                {'name': 'host', 'value': os.environ.get('COMPUTERNAME', 'localhost')},
                {'name': 'thread', 'value': f"NonParallel{os.getpid()}"}
            ],
            'links': [],
            'parameters': []
        }
        
        # 为失败和错误的测试添加详细信息
        if status in ['failed', 'broken']:
            allure_result['statusDetails']['message'] = result.get('error_message', '')
            allure_result['statusDetails']['trace'] = result.get('error_message', '')
        
        # 添加输出作为附件
        if result.get('stdout'):
            allure_result['attachments'] = [{
                'name': 'stdout',
                'type': 'text/plain',
                'source': f"{uuid.uuid4()}-attachment.txt"
            }]
            # 保存附件内容
            attachment_path = os.path.join(self.output_dir, f"{uuid.uuid4()}-attachment.txt")
            try:
                with open(attachment_path, 'w', encoding='utf-8') as f:
                    f.write(result['stdout'])
            except:
                pass
        
        return allure_result

    def _extract_suite(self, path: str) -> str:
        """从测试路径提取测试套件名称"""
        # 例如: tests/api/test_user.py::test_login -> test_user
        parts = path.split('::')[0].split('/')
        if len(parts) >= 2:
            return parts[-1].replace('.py', '')
        return 'Tests'

    def _generate_environment_properties(self):
        """生成environment.properties文件"""
        env_content = f"""Python={sys.version.split()[0]}
Platform={sys.platform}
Host={os.environ.get('COMPUTERNAME', 'localhost')}
Timestamp={datetime.now().isoformat()}
"""
        with open(os.path.join(self.output_dir, 'environment.properties'), 'w', encoding='utf-8') as f:
            f.write(env_content)

    def _generate_categories_json(self):
        """生成categories.json文件"""
        categories = [
            {
                'name': '产品缺陷',
                'matchedStatuses': ['failed'],
                'description': '因产品缺陷导致的测试失败'
            },
            {
                'name': '测试缺陷',
                'matchedStatuses': ['broken'],
                'description': '测试本身存在问题导致的失败'
            },
            {
                'name': '已跳过',
                'matchedStatuses': ['skipped'],
                'description': '被跳过的测试'
            }
        ]
        with open(os.path.join(self.output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

    def _generate_executor_json(self):
        """生成executor.json文件"""
        executor = {
            'name': '自动化测试框架',
            'type': 'local',
            'buildOrder': int(datetime.now().timestamp()),
            'buildName': f"Build {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'buildUrl': ''
        }
        with open(os.path.join(self.output_dir, 'executor.json'), 'w', encoding='utf-8') as f:
            json.dump(executor, f, ensure_ascii=False, indent=2)

    def generate_report(self):
        """手动触发报告生成
        
        如果需要手动控制报告生成时机，可以调用此方法
        但请确保所有测试用例已经执行完毕
        """
        if not self._report_generated:
            self._generate_allure_report()
            self._report_generated = True


class ReportCollector:
    """编程式报告收集器
    
    适用于不通过pytest运行的自定义测试场景
    """

    def __init__(self, output_dir: str = None):
        """初始化收集器"""
        self.plugin = TestReportPlugin(output_dir)

    def add_result(self, name: str, path: str, status: str,
                   duration: float = 0.0, error_message: str = None):
        """添加单个测试结果
        
        Args:
            name: 测试名称
            path: 测试路径
            status: 结果状态 (passed/failed/skipped/broken)
            duration: 执行时长（秒）
            error_message: 错误信息（如果有）
        """
        self.plugin.test_results.append({
            'name': name,
            'path': path,
            'status': status,
            'duration': duration,
            'stdout': None,
            'stderr': None,
            'error_type': 'AssertionError' if status == 'failed' else None,
            'error_message': error_message
        })

    def add_pass(self, name: str, path: str, duration: float = 0.0):
        """添加通过的测试"""
        self.add_result(name, path, 'passed', duration)

    def add_fail(self, name: str, path: str, duration: float = 0.0, error: str = None):
        """添加失败的测试"""
        self.add_result(name, path, 'failed', duration, error)

    def add_skip(self, name: str, path: str, reason: str = None):
        """添加跳过的测试"""
        self.add_result(name, path, 'skipped', 0, reason)

    def generate(self):
        """生成Allure报告
        
        在所有测试执行完毕后调用此方法生成报告
        """
        self.plugin._generate_allure_report()

    @property
    def summary(self) -> Dict:
        """获取测试结果摘要"""
        results = self.plugin.test_results
        return {
            'total': len(results),
            'passed': sum(1 for r in results if r['status'] == 'passed'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'skipped': sum(1 for r in results if r['status'] == 'skipped'),
            'broken': sum(1 for r in results if r['status'] == 'broken'),
            'pass_rate': (sum(1 for r in results if r['status'] == 'passed') / len(results) * 100) if results else 0
        }


def report_collector(output_dir: str = None):
    """装饰器工厂
    
    用于包装测试函数，自动收集结果并生成报告
    
    Example:
        @report_collector(output_dir='./my-reports')
        def run_all_tests():
            # 执行测试逻辑
            collector.add_pass('test_1', 'tests/test_1.py::test_1')
            collector.add_fail('test_2', 'tests/test_2.py::test_2', error='断言失败')
    """
    collector = ReportCollector(output_dir)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(collector, *args, **kwargs)
            collector.generate()
            return result
        wrapper.collector = collector
        return wrapper
    
    return decorator


# 全局默认收集器实例
default_collector = ReportCollector()
