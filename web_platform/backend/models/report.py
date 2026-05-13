"""
测试报告数据模型
"""
import json
from backend.utils.database import Database


class Report:
    """测试报告模型"""

    @staticmethod
    def find_all(page=1, page_size=20):
        """获取所有报告"""
        sql = """
            SELECT r.*, e.task_id, t.name as task_name
            FROM test_report r
            LEFT JOIN test_execution e ON r.execution_id = e.id
            LEFT JOIN test_task t ON e.task_id = t.id
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """
        count_sql = "SELECT COUNT(*) as total FROM test_report"

        reports = Database.execute_query(sql, (page_size, (page - 1) * page_size))
        total = Database.execute_query(count_sql, fetch_one=True)['total']

        for report in reports:
            if report.get('summary') and isinstance(report['summary'], str):
                try:
                    report['summary'] = json.loads(report['summary'])
                except:
                    pass

        return {
            'reports': reports,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def find_by_id(report_id: int):
        """根据ID查找报告"""
        sql = """
            SELECT r.*, e.task_id, t.name as task_name
            FROM test_report r
            LEFT JOIN test_execution e ON r.execution_id = e.id
            LEFT JOIN test_task t ON e.task_id = t.id
            WHERE r.id = %s
        """
        report = Database.execute_query(sql, (report_id,), fetch_one=True)

        if report and report.get('summary') and isinstance(report['summary'], str):
            try:
                report['summary'] = json.loads(report['summary'])
            except:
                pass

        return report
