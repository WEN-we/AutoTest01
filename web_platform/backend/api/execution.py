"""
执行监控API
测试执行的状态和日志
"""
from flask import Blueprint, request, jsonify
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

        # 如果内存中没有，从数据库获取
        db_status = Execution.find_by_execution_id(execution_id)
        if db_status:
            # 从数据库记录构建状态
            return jsonify({
                'code': 200,
                'message': '获取成功',
                'data': {
                    'execution_id': execution_id,
                    'task_id': db_status['task_id'],
                    'test_type': db_status.get('test_type', 'api'),
                    'status': db_status['status'],
                    'start_time': db_status['start_time'].isoformat() if db_status.get('start_time') else None,
                    'end_time': db_status['end_time'].isoformat() if db_status.get('end_time') else None,
                    'result_summary': db_status.get('result_summary'),
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

        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))

        executions = []
        
        # 从内存获取正在运行的执行
        for exec_id, info in executor.running_executions.items():
            executions.append({
                'execution_id': exec_id,
                'task_id': info.get('task_id'),
                'test_type': info.get('test_type'),
                'status': info.get('status'),
                'start_time': info.get('start_time'),
                'end_time': info.get('end_time'),
                'result_summary': info.get('result_summary')
            })
        
        # 从数据库获取历史执行记录
        db_result = Execution.find_all(page=1, page_size=100)
        if db_result and db_result.get('items'):
            for db_exec in db_result['items']:
                # 避免重复
                if not any(e['execution_id'] == db_exec['execution_id'] for e in executions):
                    executions.append({
                        'execution_id': db_exec['execution_id'],
                        'task_id': db_exec['task_id'],
                        'test_type': db_exec.get('test_type', 'api'),
                        'status': db_exec['status'],
                        'start_time': db_exec['start_time'].isoformat() if db_exec.get('start_time') else None,
                        'end_time': db_exec['end_time'].isoformat() if db_exec.get('end_time') else None,
                        'result_summary': db_exec.get('result_summary')
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
