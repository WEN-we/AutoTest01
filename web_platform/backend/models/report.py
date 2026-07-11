"""
测试报告数据模型
"""
import json
import logging
from backend.utils.database import Database

logger = logging.getLogger(__name__)


class Report:
    """测试报告模型"""

    @staticmethod
    def find_all(page=1, page_size=20):
        """获取所有报告 - 合并test_report表和test_execution聚合的数据"""
        all_reports = []
        covered_execution_ids = set()

        # 1. 从 test_report 表获取已有记录
        sql_report = """
            SELECT r.*, e.task_id, t.name as task_name
            FROM test_report r
            LEFT JOIN test_execution e ON r.execution_id = e.execution_id
            LEFT JOIN test_task t ON e.task_id = t.id
            ORDER BY r.created_at DESC
        """
        try:
            report_records = Database.execute_query(sql_report)
        except Exception as e:
            logger.error(f"查询test_report表失败: {e}")
            report_records = []

        for report in (report_records or []):
            if report.get('summary') and isinstance(report['summary'], str):
                try:
                    report['summary'] = json.loads(report['summary'])
                except:
                    pass
            # 确保 test_report 记录也有 duration 字段
            if report.get('duration') is None:
                report['duration'] = 0
            all_reports.append(report)
            if report.get('execution_id'):
                covered_execution_ids.add(report['execution_id'])

        # 2. 从 test_execution 聚合补充未覆盖的记录
        # 使用 LEFT JOIN 显示所有执行记录，无论是否有 test_case_result
        sql_exec = """
            SELECT
                e.execution_id,
                e.task_id,
                e.test_type,
                e.start_time,
                e.duration as exec_duration,
                e.result_summary,
                t.name as task_name,
                COUNT(cr.id) as total,
                SUM(CASE WHEN cr.status = 'passed' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN cr.status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN cr.status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                SUM(CASE WHEN cr.status IN ('error', 'broken') THEN 1 ELSE 0 END) as errors,
                SUM(cr.duration) as total_duration
            FROM test_execution e
            LEFT JOIN test_task t ON e.task_id = t.id
            LEFT JOIN test_case_result cr ON e.execution_id = cr.execution_id
            GROUP BY e.execution_id, e.task_id, e.test_type, e.start_time, e.duration, e.result_summary, t.name
            ORDER BY e.start_time DESC
        """
        try:
            exec_records = Database.execute_query(sql_exec)
        except Exception as e:
            logger.error(f"聚合查询test_execution失败: {e}")
            exec_records = []

        for row in (exec_records or []):
            execution_id = row['execution_id']
            if execution_id in covered_execution_ids:
                continue

            passed = int(row.get('passed') or 0)
            failed = int(row.get('failed') or 0)
            skipped = int(row.get('skipped') or 0)
            errors = int(row.get('errors') or 0)
            total_cases = int(row.get('total') or 0)

            # 耗时优先级：test_execution.duration > SUM(test_case_result.duration) > 0
            duration = row.get('exec_duration')
            if duration is None or duration == 0:
                duration = row.get('total_duration')
            if duration is None:
                duration = 0
            # 处理 Decimal 类型
            try:
                duration = float(duration)
            except (TypeError, ValueError):
                duration = 0
            duration = round(duration, 2)

            pass_rate = round((passed / total_cases) * 100, 2) if total_cases > 0 else 0.0

            # 解析 result_summary JSON
            result_summary = row.get('result_summary')
            if result_summary and isinstance(result_summary, str):
                try:
                    result_summary = json.loads(result_summary)
                except:
                    result_summary = {}
            elif not result_summary:
                result_summary = {}

            # 为补充记录生成report_name（从start_time和task_name推断测试类型）
            start_time = row.get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        ts_str = dt.strftime('%Y%m%d_%H%M%S')
                    except:
                        ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                else:
                    ts_str = start_time.strftime('%Y%m%d_%H%M%S')
            else:
                from datetime import datetime
                ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 优先使用 test_execution 表的 test_type 字段，其次从 task_name 推断
            test_type = row.get('test_type')
            if not test_type or test_type == 'unknown':
                task_name_lower = (row.get('task_name') or '').lower()
                inferred_type = 'unknown'
                for key in ['api', 'ui', 'smoke', 'android', 'ios', 'windows', 'linux', 'harmony', 'service', 'performance', 'ai', 'whitebox']:
                    if key in task_name_lower:
                        inferred_type = key
                        break
                test_type = inferred_type

            fallback_report_name = f"{ts_str}_{test_type}"

            all_reports.append({
                'id': execution_id,
                'execution_id': execution_id,
                'task_id': row.get('task_id'),
                'task_name': row.get('task_name') or result_summary.get('task_name') or '-',
                'report_name': fallback_report_name,
                'report_type': 'allure',
                'summary': {
                    'total': total_cases,
                    'passed': passed,
                    'failed': failed,
                    'skipped': skipped,
                    'errors': errors,
                    'duration': duration
                },
                'report_path': None,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'total': total_cases,
                'pass_rate': pass_rate,
                'duration': duration,
                'created_at': row.get('start_time')
            })
            covered_execution_ids.add(execution_id)

        # 3. 按创建时间降序排序（统一转换为字符串避免类型比较错误）
        def get_sort_key(r):
            created_at = r.get('created_at')
            if created_at is None:
                return ''
            if hasattr(created_at, 'isoformat'):
                return created_at.isoformat()
            return str(created_at)

        all_reports.sort(key=get_sort_key, reverse=True)

        # 4. 分页
        total = len(all_reports)
        start = (page - 1) * page_size
        end = start + page_size
        paged_reports = all_reports[start:end]

        return {
            'reports': paged_reports,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def _find_all_from_executions(page=1, page_size=20):
        """从 test_execution 和 test_case_result 表聚合生成报告数据"""
        from backend.models.execution import Execution
        from backend.models.test_case_result import TestCaseResult

        # 获取有测试用例结果的执行记录
        sql = """
            SELECT DISTINCT e.*, t.name as task_name
            FROM test_execution e
            LEFT JOIN test_task t ON e.task_id = t.id
            INNER JOIN test_case_result cr ON e.execution_id = cr.execution_id
            ORDER BY e.start_time DESC
            LIMIT %s OFFSET %s
        """
        count_sql = """
            SELECT COUNT(DISTINCT e.execution_id) as total
            FROM test_execution e
            INNER JOIN test_case_result cr ON e.execution_id = cr.execution_id
        """

        executions = Database.execute_query(sql, (page_size, (page - 1) * page_size))
        total_result = Database.execute_query(count_sql, fetch_one=True)
        total = total_result['total'] if total_result else 0

        reports = []
        for exec_record in executions:
            execution_id = exec_record['execution_id']

            # 获取该执行的测试用例统计
            summary = TestCaseResult.get_summary(execution_id)
            if not summary:
                summary = {}

            passed = summary.get('passed', 0) or 0
            failed = summary.get('failed', 0) or 0
            skipped = summary.get('skipped', 0) or 0
            errors = summary.get('errors', 0) or 0
            total_cases = summary.get('total', 0) or 0
            duration = summary.get('total_duration', 0) or 0
            if duration is None:
                duration = 0
            duration = int(float(duration))

            # 使用执行记录的 duration 如果 case_result 没有
            if duration == 0 and exec_record.get('duration'):
                duration = exec_record['duration']

            pass_rate = round((passed / total_cases) * 100, 2) if total_cases > 0 else 0.0

            # 解析 result_summary JSON
            result_summary = exec_record.get('result_summary')
            if result_summary and isinstance(result_summary, str):
                try:
                    result_summary = json.loads(result_summary)
                except:
                    result_summary = {}
            elif not result_summary:
                result_summary = {}

            # 生成report_name - 优先使用 test_execution 的 test_type 字段
            start_time = exec_record.get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    try:
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        ts_str = dt.strftime('%Y%m%d_%H%M%S')
                    except:
                        ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                else:
                    ts_str = start_time.strftime('%Y%m%d_%H%M%S')
            else:
                ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')

            test_type = exec_record.get('test_type')
            if not test_type or test_type == 'unknown':
                task_name_lower = (exec_record.get('task_name') or '').lower()
                inferred_type = 'unknown'
                for key in ['api', 'ui', 'smoke', 'android', 'ios', 'windows', 'linux', 'harmony', 'service', 'performance', 'ai', 'whitebox']:
                    if key in task_name_lower:
                        inferred_type = key
                        break
                test_type = inferred_type

            fallback_name = f"{ts_str}_{test_type}"

            # 构建报告数据 - 使用 execution_id 作为 id，确保前端可以正确查询详情
            report = {
                'id': execution_id,
                'execution_id': execution_id,
                'task_id': exec_record.get('task_id'),
                'task_name': exec_record.get('task_name') or result_summary.get('task_name') or '-',
                'report_name': fallback_name,
                'report_type': 'allure',
                'summary': {
                    'total': total_cases,
                    'passed': passed,
                    'failed': failed,
                    'skipped': skipped,
                    'errors': errors,
                    'duration': duration
                },
                'report_path': None,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'total': total_cases,
                'pass_rate': pass_rate,
                'duration': duration,
                'created_at': exec_record.get('start_time')
            }
            reports.append(report)

        return {
            'reports': reports,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def find_by_id(report_id: int):
        """根据ID查找报告 - 优先从test_report表获取，如果没有则从test_execution聚合生成"""
        # 首先尝试从 test_report 表获取
        sql = """
            SELECT r.*, e.task_id, t.name as task_name
            FROM test_report r
            LEFT JOIN test_execution e ON r.execution_id = e.execution_id
            LEFT JOIN test_task t ON e.task_id = t.id
            WHERE r.id = %s
        """
        report = Database.execute_query(sql, (report_id,), fetch_one=True)

        if report:
            if report.get('summary') and isinstance(report['summary'], str):
                try:
                    report['summary'] = json.loads(report['summary'])
                except:
                    pass
            return report

        # 如果 test_report 表没有，尝试通过 test_execution 的 id 找到 execution_id，再聚合生成
        sql_exec = "SELECT execution_id FROM test_execution WHERE id = %s"
        exec_record = Database.execute_query(sql_exec, (report_id,), fetch_one=True)
        if exec_record:
            return Report._find_by_execution_id_from_db(exec_record['execution_id'])

        return None

    @staticmethod
    def find_by_execution_id(execution_id: str):
        """根据execution_id查找报告"""
        sql = """
            SELECT r.*, e.task_id, t.name as task_name
            FROM test_report r
            LEFT JOIN test_execution e ON r.execution_id = e.execution_id
            LEFT JOIN test_task t ON e.task_id = t.id
            WHERE r.execution_id = %s
        """
        report = Database.execute_query(sql, (execution_id,), fetch_one=True)

        if report:
            if report.get('summary') and isinstance(report['summary'], str):
                try:
                    report['summary'] = json.loads(report['summary'])
                except:
                    pass
            return report

        # 如果 test_report 表没有，从 test_execution 聚合生成
        return Report._find_by_execution_id_from_db(execution_id)

    @staticmethod
    def _find_by_execution_id_from_db(execution_id: str):
        """从 test_execution 和 test_case_result 聚合生成报告数据"""
        from backend.models.execution import Execution
        from backend.models.test_case_result import TestCaseResult

        exec_record = Execution.find_by_execution_id(execution_id)
        if not exec_record:
            return None

        # 获取该执行的测试用例统计
        summary = TestCaseResult.get_summary(execution_id)
        if not summary:
            summary = {}

        passed = summary.get('passed', 0) or 0
        failed = summary.get('failed', 0) or 0
        skipped = summary.get('skipped', 0) or 0
        errors = summary.get('errors', 0) or 0
        total_cases = summary.get('total', 0) or 0
        duration = summary.get('total_duration', 0) or 0
        if duration is None:
            duration = 0
        duration = int(float(duration))

        # 使用执行记录的 duration 如果 case_result 没有
        if duration == 0 and exec_record.get('duration'):
            duration = exec_record['duration']

        pass_rate = round((passed / total_cases) * 100, 2) if total_cases > 0 else 0.0

        # 解析 result_summary JSON
        result_summary = exec_record.get('result_summary')
        if result_summary and isinstance(result_summary, str):
            try:
                result_summary = json.loads(result_summary)
            except:
                result_summary = {}
        elif not result_summary:
            result_summary = {}

        # 生成report_name - 优先使用 test_execution 的 test_type 字段
        start_time = exec_record.get('start_time')
        if start_time:
            if isinstance(start_time, str):
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    ts_str = dt.strftime('%Y%m%d_%H%M%S')
                except:
                    ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            else:
                ts_str = start_time.strftime('%Y%m%d_%H%M%S')
        else:
            ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')

        test_type = exec_record.get('test_type')
        if not test_type or test_type == 'unknown':
            task_name_lower = (exec_record.get('task_name') or '').lower()
            inferred_type = 'unknown'
            for key in ['api', 'ui', 'smoke', 'android', 'ios', 'windows', 'linux', 'harmony', 'service', 'performance', 'ai', 'whitebox']:
                if key in task_name_lower:
                    inferred_type = key
                    break
            test_type = inferred_type

        fallback_name = f"{ts_str}_{test_type}"

        return {
            'id': execution_id,
            'execution_id': execution_id,
            'task_id': exec_record.get('task_id'),
            'task_name': exec_record.get('task_name') or result_summary.get('task_name') or '-',
            'report_name': fallback_name,
            'report_type': 'allure',
            'summary': {
                'total': total_cases,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'duration': duration
            },
            'report_path': None,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'errors': errors,
            'total': total_cases,
            'pass_rate': pass_rate,
            'duration': duration,
            'created_at': exec_record.get('start_time')
        }

    @staticmethod
    def create(execution_id: str, report_type: str = 'allure', summary: dict = None, report_url: str = None, task_id: int = None, report_name: str = None):
        """创建报告记录

        Args:
            execution_id: 执行UUID
            report_type: 报告类型
            summary: 测试摘要统计
            report_url: 报告文件路径/URL
            task_id: 任务ID
            report_name: 报告名称（如 20250520_110530_api）
        """
        # 如果没有提供task_id，尝试从执行记录中获取
        if task_id is None:
            from backend.models.execution import Execution
            exec_record = Execution.find_by_execution_id(execution_id)
            if exec_record:
                task_id = exec_record.get('task_id', 0)
            else:
                task_id = 0

        # 从summary中提取统计数据
        passed = summary.get('passed', 0) if summary else 0
        failed = summary.get('failed', 0) if summary else 0
        skipped = summary.get('skipped', 0) if summary else 0
        errors = summary.get('errors', 0) if summary else 0
        total = summary.get('total', 0) if summary else 0
        duration = summary.get('duration', 0) if summary else 0
        pass_rate = round((passed / total) * 100, 2) if total > 0 else 0.0

        sql = """
            INSERT INTO test_report (
                execution_id, task_id, report_name, report_type, summary, report_path,
                passed, failed, skipped, errors, total, pass_rate, duration, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        summary_json = json.dumps(summary) if summary else None
        Database.execute_insert(sql, (
            execution_id, task_id, report_name, report_type, summary_json, report_url,
            passed, failed, skipped, errors, total, pass_rate, duration
        ))

        return Report.find_by_execution_id(execution_id)
