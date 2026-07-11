"""
执行记录数据模型
已修复：引用 platform_user 表而非 user 表
已修复：自动解析 result_summary JSON
"""
import json
from backend.utils.database import Database


def _parse_result_summary(record):
    """辅助函数：解析 result_summary JSON"""
    if record and 'result_summary' in record:
        rs = record['result_summary']
        if rs and isinstance(rs, str):
            try:
                record['result_summary'] = json.loads(rs)
            except:
                record['result_summary'] = None
    return record


class Execution:
    """测试执行记录模型"""

    @staticmethod
    def create(execution_id: str, task_id: int, user_id: int = None,
               trigger_type: str = 'manual', test_type: str = 'api',
               test_scene: str = 'other', task_name: str = None) -> tuple:
        """创建执行记录
        Returns:
            tuple: (record_id, run_number)
        """
        # 计算此任务的执行序号
        # 使用单个SQL查询获取最大序号（同时考虑已存在的记录）
        max_sql = """
            SELECT COALESCE(MAX(run_number), 0) as max_num 
            FROM test_execution 
            WHERE task_id = %s
        """
        max_result = Database.execute_query(max_sql, (task_id,), fetch_one=True)
        run_number = (max_result['max_num'] if max_result else 0) + 1
        
        sql = """
            INSERT INTO test_execution (execution_id, task_id, task_name, run_number, user_id, status, trigger_type, test_type, test_scene, start_time)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s, NOW())
        """
        record_id = Database.execute_insert(sql, (execution_id, task_id, task_name, run_number, user_id, trigger_type, test_type, test_scene))
        return record_id, run_number

    @staticmethod
    def find_by_execution_id(execution_id: str):
        """根据execution_id查找执行记录"""
        sql = "SELECT * FROM test_execution WHERE execution_id = %s"
        record = Database.execute_query(sql, (execution_id,), fetch_one=True)
        return _parse_result_summary(record)

    @staticmethod
    def find_by_task(task_id: int, limit=10):
        """根据任务ID查找执行记录"""
        sql = """
            SELECT e.*, u.username as executor_name
            FROM test_execution e
            LEFT JOIN platform_user u ON e.user_id = u.id
            WHERE e.task_id = %s
            ORDER BY e.start_time DESC
            LIMIT %s
        """
        results = Database.execute_query(sql, (task_id, limit))
        if results:
            return [_parse_result_summary(r) for r in results]
        return results

    @staticmethod
    def update_status(execution_id: str, status: str, result_summary: dict = None):
        """更新执行状态"""
        if result_summary:
            summary_json = json.dumps(result_summary)
            sql = """
                UPDATE test_execution
                SET status = %s, result_summary = %s
                WHERE execution_id = %s
            """
            Database.execute_update(sql, (status, summary_json, execution_id))
        else:
            sql = "UPDATE test_execution SET status = %s WHERE execution_id = %s"
            Database.execute_update(sql, (status, execution_id))

    @staticmethod
    def complete(execution_id: str, status: str, result_summary: dict = None):
        """完成执行记录"""
        try:
            if result_summary:
                # 确保 result_summary 中的所有值都是可 JSON 序列化的
                safe_summary = {}
                for key, value in result_summary.items():
                    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                        safe_summary[key] = value
                    else:
                        safe_summary[key] = str(value)
                summary_json = json.dumps(safe_summary)
                sql = """
                    UPDATE test_execution
                    SET status = %s, result_summary = %s,
                        end_time = NOW(),
                        duration = TIMESTAMPDIFF(SECOND, start_time, NOW())
                    WHERE execution_id = %s
                """
                Database.execute_update(sql, (status, summary_json, execution_id))
            else:
                sql = """
                    UPDATE test_execution
                    SET status = %s, end_time = NOW(),
                        duration = TIMESTAMPDIFF(SECOND, start_time, NOW())
                    WHERE execution_id = %s
                """
                Database.execute_update(sql, (status, execution_id))
        except Exception as e:
            # 如果更新失败，至少尝试更新状态字段
            try:
                sql = """
                    UPDATE test_execution
                    SET status = %s, end_time = NOW(),
                        duration = TIMESTAMPDIFF(SECOND, start_time, NOW())
                    WHERE execution_id = %s
                """
                Database.execute_update(sql, (status, execution_id))
            except Exception as e2:
                raise e2 from e

    @staticmethod
    def find_all(page=1, page_size=20, task_id: int = None, status: str = None):
        """获取所有执行记录（分页）"""
        offset = (page - 1) * page_size

        if task_id:
            where_clause = "WHERE e.task_id = %s"
            params = [task_id, page_size, offset]
            count_params = [task_id]
        elif status:
            where_clause = "WHERE e.status = %s"
            params = [status, page_size, offset]
            count_params = [status]
        else:
            where_clause = ""
            params = [page_size, offset]
            count_params = []

        sql = f"""
            SELECT e.*, t.name as task_name, t.test_type, t.test_scene, u.username as executor_name
            FROM test_execution e
            LEFT JOIN test_task t ON e.task_id = t.id
            LEFT JOIN platform_user u ON e.user_id = u.id
            {where_clause}
            ORDER BY e.start_time DESC
            LIMIT %s OFFSET %s
        """

        count_sql = f"SELECT COUNT(*) as total FROM test_execution e {where_clause}"

        results = Database.execute_query(sql, tuple(params))
        total = Database.execute_query(count_sql, tuple(count_params), fetch_one=True)['total']

        # 解析所有 result_summary
        if results:
            results = [_parse_result_summary(r) for r in results]

        return {
            'items': results,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def delete_by_task(task_id: int):
        """删除任务的所有执行记录"""
        sql = "DELETE FROM test_execution WHERE task_id = %s"
        Database.execute_update(sql, (task_id,))

    @staticmethod
    def get_statistics():
        """获取执行统计"""
        sql = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                AVG(duration) as avg_duration
            FROM test_execution
        """
        return Database.execute_query(sql, fetch_one=True)
