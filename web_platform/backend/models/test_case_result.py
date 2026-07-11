"""
测试用例结果数据模型
存储每个测试用例的详细执行结果
"""
import json
from backend.utils.database import Database


class TestCaseResult:
    """测试用例结果模型"""

    @staticmethod
    def create(execution_id: str, case_name: str, case_path: str,
               status: str, duration: float = 0.0,
               stdout: str = None, stderr: str = None,
               error_type: str = None, error_message: str = None,
               stack_trace: str = None,
               attachments: list = None,
               metadata: dict = None) -> int:
        """创建测试用例结果
        Args:
            execution_id: 执行UUID
            case_name: 测试用例名称
            case_path: 测试用例路径
            status: 状态 (passed/failed/skipped/error/broken)
            duration: 执行时长（秒）
            stdout: 标准输出
            stderr: 标准错误
            error_type: 错误类型
            error_message: 错误信息
            stack_trace: 堆栈信息
            attachments: 附件列表
            metadata: 元数据
        Returns:
            记录ID
        """
        sql = """
            INSERT INTO test_case_result (
                execution_id, case_name, case_path, status,
                duration, stdout, stderr, error_type, error_message,
                stack_trace, attachments, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        attachments_json = json.dumps(attachments) if attachments else None
        metadata_json = json.dumps(metadata) if metadata else None
        return Database.execute_insert(sql, (
            execution_id, case_name, case_path, status,
            duration, stdout, stderr, error_type, error_message,
            stack_trace, attachments_json, metadata_json
        ))

    @staticmethod
    def find_by_execution(execution_id: str):
        """根据执行ID查找所有测试用例结果"""
        sql = """
            SELECT * FROM test_case_result
            WHERE execution_id = %s
            ORDER BY id
        """
        results = Database.execute_query(sql, (execution_id,))
        return TestCaseResult._parse_json_fields(results)

    @staticmethod
    def get_summary(execution_id: str):
        """获取执行的测试用例统计"""
        sql = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                SUM(CASE WHEN status = 'error' OR status = 'broken' THEN 1 ELSE 0 END) as errors,
                SUM(duration) as total_duration
            FROM test_case_result
            WHERE execution_id = %s
        """
        return Database.execute_query(sql, (execution_id,), fetch_one=True)

    @staticmethod
    def _parse_json_fields(results):
        """解析JSON字段"""
        if not results:
            return results
        if isinstance(results, dict):
            if results.get('attachments') and isinstance(results['attachments'], str):
                try:
                    results['attachments'] = json.loads(results['attachments'])
                except:
                    results['attachments'] = None
            if results.get('metadata') and isinstance(results['metadata'], str):
                try:
                    results['metadata'] = json.loads(results['metadata'])
                except:
                    results['metadata'] = None
            return results
        for r in results:
            TestCaseResult._parse_json_fields(r)
        return results
