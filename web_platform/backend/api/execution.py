"""
执行监控API
测试执行的状态和日志
"""
from flask import Blueprint, request, jsonify
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

execution_bp = Blueprint('execution', __name__)


@execution_bp.route('/execution/<execution_id>/status', methods=['GET'])
def get_execution_status(execution_id):
    """获取执行状态"""
    try:
        from backend.services.test_executor import executor
        from backend.models.execution import Execution

        # 首先尝试从内存中获取（如果执行还在进行）
        status = executor.get_execution_status(execution_id)
        if status:
            return jsonify({
                'code': 200,
                'message': '获取成功',
                'data': status
            })

        # 如果内存中没有，从数据库获取 (模型层已自动解析 result_summary)
        db_status = Execution.find_by_execution_id(execution_id)
        if db_status:
            # 自动修复：如果执行已结束但状态仍为 running，修正为 failed
            status = db_status['status']
            if status == 'running' and db_status.get('end_time'):
                logger.info(f"执行记录 {execution_id} 已结束但状态为 running，自动修复为 failed")
                status = 'failed'
                # 可选：更新数据库状态
                try:
                    Execution.update_status(execution_id, 'failed', db_status.get('result_summary'))
                except Exception as e:
                    logger.error(f"自动修复执行状态失败: {e}")

            # 从数据库记录构建状态
            # 确保 result_summary 中包含 duration（优先使用数据库的 duration 字段）
            result_summary = db_status.get('result_summary') or {}
            db_duration = db_status.get('duration')
            if db_duration is not None and db_duration > 0:
                result_summary['duration'] = db_duration

            return jsonify({
                'code': 200,
                'message': '获取成功',
                'data': {
                    'execution_id': execution_id,
                    'task_id': db_status['task_id'],
                    'test_type': db_status.get('test_type', 'api'),
                    'status': status,
                    'start_time': db_status['start_time'].isoformat() if db_status.get('start_time') else None,
                    'end_time': db_status['end_time'].isoformat() if db_status.get('end_time') else None,
                    'result_summary': result_summary,
                    'exit_code': db_status.get('exit_code')
                }
            })

        return jsonify({'code': 404, 'message': '执行记录不存在'}), 404

    except Exception as e:
        logger.error(f"获取执行状态失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@execution_bp.route('/execution/<execution_id>/logs', methods=['GET'])
def get_execution_logs(execution_id):
    """获取执行日志"""
    try:
        from backend.services.test_executor import executor

        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 100))

        logs = executor.get_execution_logs(execution_id, offset, limit)

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'execution_id': execution_id,
                'offset': offset,
                'limit': limit,
                'logs': logs
            }
        })

    except Exception as e:
        logger.error(f"获取执行日志失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@execution_bp.route('/execution/<execution_id>/stop', methods=['POST'])
def stop_execution(execution_id):
    """停止执行"""
    try:
        from backend.services.test_executor import executor

        success = executor.stop_execution(execution_id)
        if success:
            return jsonify({
                'code': 200,
                'message': '执行已停止'
            })
        else:
            return jsonify({'code': 404, 'message': '执行记录不存在'}), 404

    except Exception as e:
        logger.error(f"停止执行失败: {e}")
        return jsonify({'code': 500, 'message': f'停止失败: {str(e)}'}), 500


@execution_bp.route('/executions/batch-delete', methods=['POST'])
def batch_delete_executions():
    """批量删除执行记录"""
    try:
        from backend.models.execution import Execution
        from backend.utils.database import Database

        json_data = request.get_json(silent=True)
        if not json_data or 'execution_ids' not in json_data:
            return jsonify({'code': 400, 'message': '缺少 execution_ids 参数'}), 400

        execution_ids = json_data['execution_ids']
        if not isinstance(execution_ids, list) or len(execution_ids) == 0:
            return jsonify({'code': 400, 'message': 'execution_ids 必须是非空数组'}), 400

        deleted_count = 0
        for execution_id in execution_ids:
            try:
                # 删除执行日志
                sql_delete_logs = "DELETE FROM execution_log WHERE execution_id = %s"
                Database.execute_update(sql_delete_logs, (execution_id,))

                # 删除执行记录
                sql_delete_exec = "DELETE FROM test_execution WHERE execution_id = %s"
                Database.execute_update(sql_delete_exec, (execution_id,))

                deleted_count += 1
            except Exception as e:
                logger.error(f"删除执行记录失败: execution_id={execution_id}, error={e}")

        return jsonify({
            'code': 200,
            'message': f'成功删除 {deleted_count} 条执行记录',
            'data': {'deleted_count': deleted_count}
        })

    except Exception as e:
        logger.error(f"批量删除执行记录失败: {e}")
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}'}), 500


@execution_bp.route('/executions', methods=['GET'])
def get_executions():
    """获取执行历史列表 - 从内存和数据库获取"""
    try:
        from backend.services.test_executor import executor
        from backend.models.execution import Execution
        from datetime import datetime

        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))

        executions = []

        # 从内存获取正在运行的执行
        for exec_id, info in executor.running_executions.items():
            duration = None
            if info.get('start_time'):
                start_time = datetime.fromisoformat(info['start_time'])
                duration = int((datetime.now() - start_time).total_seconds())

            executions.append({
                'id': info.get('id'),
                'execution_id': exec_id,
                'task_id': info.get('task_id'),
                'task_name': info.get('task_name'),
                'run_number': info.get('run_number', 1),
                'test_type': info.get('test_type', 'api'),
                'test_scene': info.get('test_scene', 'other'),
                'status': info.get('status'),
                'start_time': info.get('start_time'),
                'end_time': info.get('end_time'),
                'result_summary': info.get('result_summary'),
                'duration': duration,
                'trigger_type': info.get('trigger_type', 'manual')
            })
        
        # 从数据库获取历史执行记录 (模型层已自动解析 result_summary)
        db_result = Execution.find_all(page=1, page_size=100)
        if db_result and db_result.get('items'):
            for db_exec in db_result['items']:
                # 避免重复
                if not any(e['execution_id'] == db_exec['execution_id'] for e in executions):
                    # 优先使用result_summary中的duration，其次是数据库的duration
                    duration = None
                    if db_exec.get('result_summary') and db_exec['result_summary'].get('duration'):
                        duration = db_exec['result_summary']['duration']
                    else:
                        duration = db_exec.get('duration')
                    
                    executions.append({
                        'id': db_exec.get('id'),
                        'execution_id': db_exec['execution_id'],
                        'task_id': db_exec['task_id'],
                        'task_name': db_exec.get('task_name'),
                        'run_number': db_exec.get('run_number', 1),
                        'test_type': db_exec.get('test_type', 'api'),
                        'test_scene': db_exec.get('test_scene', 'other'),
                        'status': db_exec['status'],
                        'start_time': db_exec['start_time'].isoformat() if db_exec.get('start_time') else None,
                        'end_time': db_exec['end_time'].isoformat() if db_exec.get('end_time') else None,
                        'result_summary': db_exec.get('result_summary'),
                        'duration': duration,
                        'trigger_type': db_exec.get('trigger_type', 'manual')
                    })

        executions.sort(key=lambda x: x['start_time'] or '', reverse=True)

        total = len(executions)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_executions = executions[start:end]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'items': paginated_executions
            }
        })

    except Exception as e:
        logger.error(f"获取执行列表失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@execution_bp.route('/executions/stats', methods=['GET'])
def get_execution_stats():
    """获取执行统计 - 基于所有历史数据聚合"""
    try:
        from backend.utils.database import Database

        # 1. 总执行次数
        sql_total = "SELECT COUNT(*) as total FROM test_execution"
        total_result = Database.execute_query(sql_total, fetch_one=True)
        total_executions = total_result['total'] if total_result else 0

        # 2. 成功次数
        sql_success = "SELECT COUNT(*) as count FROM test_execution WHERE status = 'success'"
        success_result = Database.execute_query(sql_success, fetch_one=True)
        success_count = success_result['count'] if success_result else 0

        # 3. 失败次数
        sql_failed = "SELECT COUNT(*) as count FROM test_execution WHERE status = 'failed'"
        failed_result = Database.execute_query(sql_failed, fetch_one=True)
        failed_count = failed_result['count'] if failed_result else 0

        # 4. 执行中次数
        sql_running = "SELECT COUNT(*) as count FROM test_execution WHERE status = 'running'"
        running_result = Database.execute_query(sql_running, fetch_one=True)
        running_count = running_result['count'] if running_result else 0

        # 5. 已停止次数
        sql_stopped = "SELECT COUNT(*) as count FROM test_execution WHERE status = 'stopped'"
        stopped_result = Database.execute_query(sql_stopped, fetch_one=True)
        stopped_count = stopped_result['count'] if stopped_result else 0

        # 6. 总测试用例数（从 test_case_result 聚合）
        sql_cases = """
            SELECT
                COUNT(*) as total_cases,
                SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_cases,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_cases,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_cases,
                SUM(CASE WHEN status IN ('error', 'broken') THEN 1 ELSE 0 END) as error_cases
            FROM test_case_result
        """
        cases_result = Database.execute_query(sql_cases, fetch_one=True)

        # 7. 计算通过率（基于用例级别）
        total_cases = cases_result['total_cases'] if cases_result else 0
        passed_cases = cases_result['passed_cases'] if cases_result else 0
        case_pass_rate = round((passed_cases / total_cases) * 100, 1) if total_cases > 0 else 0

        # 8. 计算执行级别通过率
        exec_pass_rate = round((success_count / total_executions) * 100, 1) if total_executions > 0 else 0

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'total_executions': total_executions,
                'success_count': success_count,
                'failed_count': failed_count,
                'running_count': running_count,
                'stopped_count': stopped_count,
                'total_cases': total_cases,
                'passed_cases': passed_cases,
                'failed_cases': cases_result['failed_cases'] if cases_result else 0,
                'skipped_cases': cases_result['skipped_cases'] if cases_result else 0,
                'error_cases': cases_result['error_cases'] if cases_result else 0,
                'case_pass_rate': case_pass_rate,
                'exec_pass_rate': exec_pass_rate
            }
        })

    except Exception as e:
        logger.error(f"获取执行统计失败: {e}")
        return jsonify({'code': 500, 'message': f'获取统计失败: {str(e)}'}), 500
