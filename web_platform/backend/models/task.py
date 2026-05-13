"""
任务数据模型
"""
import json
from backend.utils.database import Database
from flask import request


class Task:
    """测试任务模型"""

    @staticmethod
    def find_all(filters=None, page=1, page_size=20):
        """获取任务列表"""
        sql = "SELECT * FROM test_task WHERE 1=1"
        count_sql = "SELECT COUNT(*) as total FROM test_task WHERE 1=1"
        params = []
        count_params = []

        if filters:
            if filters.get('status'):
                sql += " AND status = %s"
                count_sql += " AND status = %s"
                params.append(filters['status'])
                count_params.append(filters['status'])

            if filters.get('task_type'):
                sql += " AND task_type = %s"
                count_sql += " AND task_type = %s"
                params.append(filters['task_type'])
                count_params.append(filters['task_type'])

        # 排序和分页
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, (page - 1) * page_size])

        tasks = Database.execute_query(sql, tuple(params))
        total = Database.execute_query(count_sql, tuple(count_params), fetch_one=True)['total']

        # 处理JSON字段
        for task in tasks:
            if task.get('test_data') and isinstance(task['test_data'], str):
                try:
                    task['test_data'] = json.loads(task['test_data'])
                except:
                    pass
            if task.get('result_summary') and isinstance(task['result_summary'], str):
                try:
                    task['result_summary'] = json.loads(task['result_summary'])
                except:
                    pass

        return {
            'tasks': tasks,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def get_all(page=1, page_size=20, test_type=None, test_scene=None, status=None, search=None):
        """获取任务列表 - 适配API调用"""
        filters = {}
        if status:
            filters['status'] = status
        if test_type:
            filters['task_type'] = test_type
        if test_scene:
            filters['test_scene'] = test_scene

        sql = "SELECT * FROM test_task WHERE 1=1"
        count_sql = "SELECT COUNT(*) as total FROM test_task WHERE 1=1"
        params = []
        count_params = []

        if filters:
            if filters.get('status'):
                sql += " AND status = %s"
                count_sql += " AND status = %s"
                params.append(filters['status'])
                count_params.append(filters['status'])

            if filters.get('task_type'):
                sql += " AND task_type = %s"
                count_sql += " AND task_type = %s"
                params.append(filters['task_type'])
                count_params.append(filters['task_type'])

            if filters.get('test_scene'):
                sql += " AND test_scene = %s"
                count_sql += " AND test_scene = %s"
                params.append(filters['test_scene'])
                count_params.append(filters['test_scene'])

        if search:
            sql += " AND (name LIKE %s OR description LIKE %s)"
            count_sql += " AND (name LIKE %s OR description LIKE %s)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])
            count_params.extend([search_pattern, search_pattern])

        # 排序和分页
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, (page - 1) * page_size])

        tasks = Database.execute_query(sql, tuple(params))
        total = Database.execute_query(count_sql, tuple(count_params), fetch_one=True)['total']

        # 处理JSON字段
        for task in tasks:
            if task.get('test_data') and isinstance(task['test_data'], str):
                try:
                    task['test_data'] = json.loads(task['test_data'])
                except:
                    pass
            if task.get('result_summary') and isinstance(task['result_summary'], str):
                try:
                    task['result_summary'] = json.loads(task['result_summary'])
                except:
                    pass

        return {
            'items': tasks,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def find_by_id(task_id: int):
        """根据ID查找任务"""
        sql = "SELECT * FROM test_task WHERE id = %s"
        task = Database.execute_query(sql, (task_id,), fetch_one=True)

        if task and task.get('test_data') and isinstance(task['test_data'], str):
            try:
                task['test_data'] = json.loads(task['test_data'])
            except:
                pass

        if task and task.get('result_summary') and isinstance(task['result_summary'], str):
            try:
                task['result_summary'] = json.loads(task['result_summary'])
            except:
                pass

        return task

    @staticmethod
    def create(name=None, description=None, test_type=None, test_path=None, test_scene=None, 
               env_config=None, created_by=None, **kwargs):
        """创建任务 - 支持多种调用方式"""
        if isinstance(name, dict):
            data = name
            return Task._create_from_dict(data)
        
        test_data = env_config or {}
        if isinstance(test_data, dict):
            test_data = json.dumps(test_data)

        sql = """
            INSERT INTO test_task
            (name, description, test_type, test_path, test_scene, env_config, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, 'idle', %s)
        """
        return Database.execute_insert(sql, (
            name,
            description or '',
            test_type,
            test_path or '',
            test_scene or 'other',
            test_data,
            created_by
        ))

    @staticmethod
    def _create_from_dict(data: dict) -> int:
        """从字典创建任务"""
        test_data = data.get('env_config') or data.get('test_data') or {}
        if isinstance(test_data, dict):
            test_data = json.dumps(test_data)

        sql = """
            INSERT INTO test_task
            (name, description, test_type, test_path, test_scene, env_config, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, 'idle', %s)
        """
        return Database.execute_insert(sql, (
            data.get('name'),
            data.get('description', ''),
            data.get('test_type'),
            data.get('test_path', ''),
            data.get('test_scene', 'other'),
            test_data,
            data.get('created_by')
        ))

    @staticmethod
    def update(task_id: int, data=None, **kwargs):
        """更新任务 - 支持多种调用方式"""
        if data is None:
            data = {}
        elif not isinstance(data, dict):
            raise ValueError("data 参数必须是字典")
        
        data.update(kwargs)
        
        updates = []
        params = []

        fields = ['name', 'description', 'target_url', 'ai_model', 'status', 'test_path', 'test_scene', 'env_config']
        for field in fields:
            if field in data:
                value = data[field]
                if field == 'env_config' and isinstance(value, dict):
                    value = json.dumps(value)
                updates.append(f"{field} = %s")
                params.append(value)

        if 'test_data' in data:
            updates.append("test_data = %s")
            test_data = data['test_data']
            if isinstance(test_data, dict):
                test_data = json.dumps(test_data)
            params.append(test_data)

        if updates:
            updates.append("updated_at = NOW()")
            sql = f"UPDATE test_task SET {', '.join(updates)} WHERE id = %s"
            params.append(task_id)
            Database.execute_update(sql, tuple(params))

    @staticmethod
    def delete(task_id: int):
        """删除任务"""
        sql = "DELETE FROM test_task WHERE id = %s"
        Database.execute_update(sql, (task_id,))

    @staticmethod
    def update_status(task_id: int, status: str):
        """更新任务状态"""
        if status == 'running':
            sql = "UPDATE test_task SET status = %s, started_at = NOW() WHERE id = %s"
        elif status in ['success', 'failed', 'cancelled']:
            sql = "UPDATE test_task SET status = %s, finished_at = NOW() WHERE id = %s"
        else:
            sql = "UPDATE test_task SET status = %s WHERE id = %s"
        Database.execute_update(sql, (status, task_id))

    @staticmethod
    def get_statistics():
        """获取统计信息"""
        stats = {}

        sql = "SELECT status, COUNT(*) as count FROM test_task GROUP BY status"
        results = Database.execute_query(sql)

        for row in results:
            stats[row['status']] = row['count']

        total_sql = "SELECT COUNT(*) as total FROM test_task"
        total_result = Database.execute_query(total_sql, fetch_one=True)
        stats['total'] = total_result['total']

        # 获取最近30天的趋势
        trend_sql = """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM test_task
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        stats['daily_trend'] = Database.execute_query(trend_sql)

        return stats
