"""
执行记录数据模型
已修复：引用 platform_user 表而非 user 表
"""
import json
from backend.utils.database import Database


class Execution:
    """测试执行记录模型"""

    @staticmethod
    def create(execution_id: str, task_id: int, user_id: int = None,
               trigger_type: str = 'manual') -> int:
        """创建执行记录"""
        sql = """
            INSERT INTO test_execution (execution_id, task_id, user_id, status, trigger_type, start_time)
            VALUES (%s, %s, %s, 'pending', %s, NOW())
        """
        return Database.execute_insert(sql, (execution_id, task_id, user_id, trigger_type))

    @staticmethod
    def find_by_execution_id(execution_id: str):
        """根据execution_id查找执行记录"""
        sql = "SELECT * FROM test_execution WHERE execution_id = %s"
        return Database.execute_query(sql, (execution_id,), fetch_one=True)

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
        return Database.execute_query(sql, (task_id, limit))

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
        if result_summary:
            summary_json = json.dumps(result_summary)
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
            SELECT e.*, t.name as task_name, t.test_type, u.username as executor_name
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
