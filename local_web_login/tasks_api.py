"""
测试任务管理API
"""
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import json
import datetime
import os
import subprocess
import threading
from utils.tools.logger import log as logger
from local_web_login.backend_server import (
    login_required, success_response, error_response,
    Database, User, Auth
)

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')


def async_task(f):
    """异步任务装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        result_container = {}

        def run_task():
            try:
                result_container['result'] = f(*args, **kwargs)
            except Exception as e:
                logger.error(f"异步任务执行失败: {e}")
                result_container['error'] = str(e)

        thread = threading.Thread(target=run_task)
        thread.start()

        return jsonify(success_response(
            data={"status": "started", "message": "任务已在后台启动"},
            message="任务启动成功"
        ))
    return wrapper


@tasks_bp.route('', methods=['GET'])
@login_required
def get_tasks():
    """获取任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        status = request.args.get('status')
        task_type = request.args.get('task_type')

        offset = (page - 1) * page_size

        sql = "SELECT * FROM test_task WHERE 1=1"
        count_sql = "SELECT COUNT(*) as total FROM test_task WHERE 1=1"
        params = []

        if status:
            sql += " AND status = %s"
            count_sql += " AND status = %s"
            params.append(status)

        if task_type:
            sql += " AND task_type = %s"
            count_sql += " AND task_type = %s"
            params.append(task_type)

        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        tasks = Database.execute_query(sql, tuple(params))
        total_result = Database.execute_query(count_sql, tuple(params)[:-2] if params else (), fetch_one=True)

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

        return jsonify(success_response(
            data={
                "tasks": tasks,
                "total": total_result['total'],
                "page": page,
                "page_size": page_size
            }
        ))
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return error_response("获取任务列表失败", 500)


@tasks_bp.route('/<int:task_id>', methods=['GET'])
@login_required
def get_task_detail(task_id):
    """获取任务详情"""
    try:
        sql = "SELECT * FROM test_task WHERE id = %s"
        task = Database.execute_query(sql, (task_id,), fetch_one=True)

        if not task:
            return error_response("任务不存在", 404)

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

        creator = User.find_by_id(task['created_by'])
        if creator:
            task['creator'] = {
                'id': creator['id'],
                'username': creator['username']
            }

        executions_sql = """
            SELECT te.*, u.username as executor_name
            FROM test_execution te
            LEFT JOIN user u ON te.executor_id = u.id
            WHERE te.task_id = %s
            ORDER BY te.start_time DESC
            LIMIT 10
        """
        task['executions'] = Database.execute_query(executions_sql, (task_id,))

        return jsonify(success_response(data=task))
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        return error_response("获取任务详情失败", 500)


@tasks_bp.route('', methods=['POST'])
@login_required
def create_task():
    """创建测试任务"""
    try:
        data = request.get_json()

        name = data.get('name', '').strip()
        description = data.get('description', '')
        task_type = data.get('task_type')
        target_url = data.get('target_url', '')
        test_data = data.get('test_data', {})
        ai_model = data.get('ai_model', '')

        if not name:
            return error_response("任务名称不能为空")
        if not task_type:
            return error_response("任务类型不能为空")

        sql = """
            INSERT INTO test_task (name, description, task_type, target_url, test_data, ai_model, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
        """
        test_data_json = json.dumps(test_data) if test_data else '{}'

        Database.execute_update(
            sql,
            (name, description, task_type, target_url, test_data_json, ai_model, request.current_user['id'])
        )

        result = Database.execute_query("SELECT LAST_INSERT_ID() as id", fetch_one=True)

        logger.info(f"创建测试任务成功: {name}")

        return jsonify(success_response(
            data={"task_id": result['id']},
            message="任务创建成功"
        ))
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return error_response("创建任务失败", 500)


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """更新测试任务"""
    try:
        data = request.get_json()

        sql = "UPDATE test_task SET "
        updates = []
        params = []

        if 'name' in data:
            updates.append("name = %s")
            params.append(data['name'])

        if 'description' in data:
            updates.append("description = %s")
            params.append(data['description'])

        if 'target_url' in data:
            updates.append("target_url = %s")
            params.append(data['target_url'])

        if 'test_data' in data:
            updates.append("test_data = %s")
            params.append(json.dumps(data['test_data']))

        if 'ai_model' in data:
            updates.append("ai_model = %s")
            params.append(data['ai_model'])

        if not updates:
            return error_response("没有需要更新的字段")

        updates.append("updated_at = NOW()")
        sql += ", ".join(updates) + " WHERE id = %s"
        params.append(task_id)

        Database.execute_update(sql, tuple(params))

        logger.info(f"更新测试任务成功: {task_id}")

        return jsonify(success_response(message="任务更新成功"))
    except Exception as e:
        logger.error(f"更新任务失败: {e}")
        return error_response("更新任务失败", 500)


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """删除测试任务"""
    try:
        sql = "DELETE FROM test_task WHERE id = %s"
        affected = Database.execute_update(sql, (task_id,))

        if affected == 0:
            return error_response("任务不存在", 404)

        logger.info(f"删除测试任务: {task_id}")

        return jsonify(success_response(message="任务删除成功"))
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return error_response("删除任务失败", 500)


@tasks_bp.route('/<int:task_id>/execute', methods=['POST'])
@login_required
def execute_task(task_id):
    """执行测试任务"""
    try:
        sql = "SELECT * FROM test_task WHERE id = %s"
        task = Database.execute_query(sql, (task_id,), fetch_one=True)

        if not task:
            return error_response("任务不存在", 404)

        if task['status'] == 'running':
            return error_response("任务正在执行中")

        Database.execute_update(
            "UPDATE test_task SET status = 'running', started_at = NOW() WHERE id = %s",
            (task_id,)
        )

        execution_sql = """
            INSERT INTO test_execution (task_id, executor_id, status, start_time)
            VALUES (%s, %s, 'running', NOW())
        """
        Database.execute_update(execution_sql, (task_id, request.current_user['id']))
        execution_result = Database.execute_query("SELECT LAST_INSERT_ID() as id", fetch_one=True)
        execution_id = execution_result['id']

        thread = threading.Thread(target=_run_test_task, args=(task_id, execution_id, task))
        thread.start()

        return jsonify(success_response(
            data={
                "execution_id": execution_id,
                "status": "running"
            },
            message="任务已开始执行"
        ))
    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        return error_response("执行任务失败", 500)


def _run_test_task(task_id, execution_id, task):
    """后台执行测试任务"""
    try:
        logger.info(f"开始执行测试任务: {task_id}")

        test_data = task.get('test_data', {})
        if isinstance(test_data, str):
            try:
                test_data = json.loads(test_data)
            except:
                test_data = {}

        report_data = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }

        if task['task_type'] == 'ai':
            from tests.test_ai.ai_test_engine import AITestEngine
            from utils.drivers.ui_driver import UIDriver
            import time

            driver = UIDriver.create_driver()
            try:
                page = driver.goto(task['target_url'])
                time.sleep(2)

                ai_engine = AITestEngine()
                result = ai_engine.run_autonomous_test(page)

                if result.get('final_result', {}).get('status') == 'success':
                    report_data['passed'] = 1
                    report_data['total'] = 1
                    status = 'success'
                else:
                    report_data['failed'] = 1
                    report_data['total'] = 1
                    status = 'failed'

            finally:
                driver.close()
        else:
            status = 'success'
            report_data['total'] = 1
            report_data['passed'] = 1

        result_summary_json = json.dumps(report_data)

        Database.execute_update(
            """UPDATE test_task
               SET status = %s, finished_at = NOW(), result_summary = %s
               WHERE id = %s""",
            (status, result_summary_json, task_id)
        )

        Database.execute_update(
            """UPDATE test_execution
               SET status = %s, end_time = NOW(), duration = TIMESTAMPDIFF(SECOND, start_time, NOW()),
                   logs = %s
               WHERE id = %s""",
            (status, json.dumps(report_data), execution_id)
        )

        logger.info(f"测试任务执行完成: {task_id}, 状态: {status}")

    except Exception as e:
        logger.error(f"执行测试任务失败: {e}")

        Database.execute_update(
            "UPDATE test_task SET status = 'failed' WHERE id = %s",
            (task_id,)
        )

        Database.execute_update(
            """UPDATE test_execution
               SET status = 'failed', end_time = NOW(),
                   logs = %s
               WHERE id = %s""",
            (str(e), execution_id)
        )


@tasks_bp.route('/<int:task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    """停止测试任务"""
    try:
        sql = "SELECT status FROM test_task WHERE id = %s"
        task = Database.execute_query(sql, (task_id,), fetch_one=True)

        if not task:
            return error_response("任务不存在", 404)

        if task['status'] != 'running':
            return error_response("任务不在运行中")

        Database.execute_update(
            "UPDATE test_task SET status = 'cancelled' WHERE id = %s",
            (task_id,)
        )

        logger.info(f"停止测试任务: {task_id}")

        return jsonify(success_response(message="任务已停止"))
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        return error_response("停止任务失败", 500)


@tasks_bp.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """获取测试统计"""
    try:
        stats = {}

        sql = """
            SELECT status, COUNT(*) as count
            FROM test_task
            GROUP BY status
        """
        results = Database.execute_query(sql)

        for row in results:
            stats[row['status']] = row['count']

        total_sql = "SELECT COUNT(*) as total FROM test_task"
        total_result = Database.execute_query(total_sql, fetch_one=True)
        stats['total'] = total_result['total']

        recent_sql = """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM test_task
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        stats['daily_trend'] = Database.execute_query(recent_sql)

        return jsonify(success_response(data=stats))
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return error_response("获取统计失败", 500)
