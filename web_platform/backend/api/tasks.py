"""
任务管理API
测试任务的CRUD操作，支持四种测试场景
已修复：使用 MySQL 数据库存储任务
已修复：API 路径统一（/api/tasks + 空路径）
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.tools.path_manager import get_path

from backend.models.task import Task
from backend.models.execution import Execution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)

TEST_TYPES = [
    ('api', 'API测试'),
    ('ui', 'UI测试'),
    ('smoke', '冒烟测试'),
    ('android', 'Android测试'),
    ('ios', 'iOS测试'),
    ('windows', 'Windows测试'),
    ('linux', 'Linux测试'),
    ('harmony', '鸿蒙测试'),
    ('service', '服务测试'),
    ('performance', '性能测试'),
    ('ai', 'AI测试'),
    ('whitebox', '白盒测试')
]

TEST_PATHS = {
    'api': 'test_api',
    'ui': 'test_ui',
    'smoke': 'test_smoke',
    'android': 'test_android',
    'ios': 'test_ios',
    'windows': 'test_windows',
    'linux': 'test_linux',
    'harmony': 'test_harmony',
    'service': 'test_service',
    'performance': 'test_performance',
    'ai': 'test_ai',
    'whitebox': 'test_whitebox'
}

TEST_SCENES = {
    'platform': {
        'name': '测试平台本身',
        'description': '测试 web_platform 自身功能',
        'default_config': {
            'base_url': 'http://localhost:8081',
            'port': 8081,
            'auth_type': 'token',
            'auto_login': True
        }
    },
    'external': {
        'name': '测试外部网站',
        'description': '测试互联网上的网站或API',
        'default_config': {
            'base_url': '',
            'port': 443,
            'auth_type': 'none',
            'auto_login': False
        }
    },
    'local': {
        'name': '测试本地服务',
        'description': '测试本地运行的服务',
        'default_config': {
            'base_url': 'http://localhost',
            'port': 8080,
            'auth_type': 'token',
            'auto_login': True
        }
    },
    'other': {
        'name': '其他',
        'description': '自定义测试场景',
        'default_config': {
            'base_url': '',
            'port': 80,
            'auth_type': 'none',
            'auto_login': False
        }
    }
}


@tasks_bp.route('/scenes', methods=['GET'])
def get_test_scenes():
    """获取所有测试场景"""
    scenes = []
    for key, value in TEST_SCENES.items():
        scenes.append({
            'value': key,
            'label': value['name'],
            'description': value['description']
        })
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': scenes
    })


@tasks_bp.route('/scenes/<scene>/config', methods=['GET'])
def get_scene_config(scene):
    """获取指定场景的默认配置"""
    if scene not in TEST_SCENES:
        return jsonify({'code': 404, 'message': '场景不存在'}), 404

    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': TEST_SCENES[scene]['default_config']
    })


@tasks_bp.route('/test-types', methods=['GET'])
def get_test_types():
    """获取所有测试类型"""
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': [{'value': k, 'label': v} for k, v in TEST_TYPES]
    })


@tasks_bp.route('', methods=['POST'])
def create_task():
    """创建任务"""
    try:
        data = request.get_json()

        name = data.get('name')
        if not name:
            return jsonify({'code': 400, 'message': '任务名称不能为空'}), 400

        scene = data.get('scene', 'other')
        scene_config = TEST_SCENES.get(scene, TEST_SCENES['other'])['default_config'].copy()

        user_config = data.get('scene_config', {})
        scene_config.update(user_config)

        env_config = {
            'TEST_SCENE': scene,
            'BASE_URL': scene_config.get('base_url', ''),
            'PORT': str(scene_config.get('port', 8080)),
            'AUTH_TYPE': scene_config.get('auth_type', 'none'),
            'AUTO_LOGIN': str(scene_config.get('auto_login', False)).lower()
        }

        if scene_config.get('auth_type') == 'token' and scene_config.get('token'):
            env_config['AUTH_TOKEN'] = scene_config['token']
        elif scene_config.get('auth_type') == 'cookie' and scene_config.get('cookie'):
            env_config['AUTH_COOKIE'] = scene_config['cookie']

        test_type = data.get('test_type', 'api')
        test_path = data.get('test_path') or TEST_PATHS.get(test_type, 'test_api')

        task_id = Task.create(
            name=name,
            description=data.get('description', ''),
            test_type=test_type,
            test_path=test_path,
            test_scene=scene,
            env_config=env_config,
            created_by=data.get('created_by')
        )

        task = Task.find_by_id(task_id)

        logger.info(f"任务创建成功: {name}, 场景: {scene}")
        return jsonify({
            'code': 200,
            'message': '创建成功',
            'data': _format_task(task)
        })

    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'创建失败: {str(e)}'}), 500


@tasks_bp.route('', methods=['GET'])
def get_tasks():
    """获取任务列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        test_type = request.args.get('test_type')
        scene = request.args.get('scene')
        status = request.args.get('status')
        search = request.args.get('search')

        result = Task.get_all(
            page=page,
            page_size=page_size,
            test_type=test_type,
            test_scene=scene,
            status=status,
            search=search
        )

        tasks = [_format_task(t) for t in result['items']]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'items': tasks
            }
        })

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    task = Task.find_by_id(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': _format_task(task)
    })


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    task = Task.find_by_id(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    try:
        data = request.get_json()

        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        if 'scene' in data:
            updates['test_scene'] = data['scene']
        if 'test_type' in data:
            updates['test_type'] = data['test_type']
        if 'test_path' in data:
            updates['test_path'] = data['test_path']
        if 'env_config' in data:
            updates['env_config'] = data['env_config']
        if 'status' in data:
            updates['status'] = data['status']

        if updates:
            Task.update(task_id, **updates)

        task = Task.find_by_id(task_id)
        logger.info(f"任务更新成功: {task_id}")
        return jsonify({
            'code': 200,
            'message': '更新成功',
            'data': _format_task(task)
        })

    except Exception as e:
        logger.error(f"更新任务失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'更新失败: {str(e)}'}), 500


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    task = Task.find_by_id(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    try:
        Task.delete(task_id)
        logger.info(f"任务删除成功: {task_id}")
        return jsonify({
            'code': 200,
            'message': '删除成功'
        })

    except Exception as e:
        logger.error(f"删除任务失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}'}), 500


@tasks_bp.route('/<int:task_id>/execute', methods=['POST'])
def execute_task(task_id):
    """执行任务"""
    task = Task.find_by_id(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    try:
        from backend.services.test_executor import executor

        env_config = task.get('env_config', {})
        if isinstance(env_config, str):
            import json as json_module
            env_config = json_module.loads(env_config)

        # 先更新任务状态为 running
        Task.update_status(task_id, 'running')

        execution_id = executor.execute_task(
            task_id=task_id,
            test_type=task['test_type'],
            test_path=task['test_path'],
            env_config=env_config
        )

        logger.info(f"任务执行启动: {task_id}, execution_id={execution_id}, 场景={task['test_scene']}")
        return jsonify({
            'code': 200,
            'message': '执行已启动',
            'data': {
                'execution_id': execution_id,
                'task_id': task_id,
                'scene': task['test_scene']
            }
        })

    except Exception as e:
        logger.error(f"执行任务失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'执行失败: {str(e)}'}), 500


@tasks_bp.route('/<int:task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止任务执行"""
    task = Task.find_by_id(task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    try:
        from backend.services.test_executor import executor

        execution_id = request.args.get('execution_id')
        if execution_id:
            executor.stop_execution(execution_id)
            # 使用 update_status 方法更新任务状态，确保时间字段正确更新
            Task.update_status(task_id, 'idle')
            logger.info(f"任务执行已停止: {task_id}")
            return jsonify({
                'code': 200,
                'message': '执行已停止'
            })
        else:
            return jsonify({'code': 400, 'message': '缺少execution_id参数'}), 400

    except Exception as e:
        logger.error(f"停止任务失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'message': f'停止失败: {str(e)}'}), 500


def _format_task(task):
    """格式化任务数据"""
    if not task:
        return None

    scene = task.get('test_scene', 'other')
    scene_name = TEST_SCENES.get(scene, {}).get('name', '其他')
    
    # 获取执行统计信息
    stats = Task.get_execution_stats(task['id'])

    return {
        'id': task['id'],
        'name': task['name'],
        'description': task.get('description', ''),
        'test_type': task['test_type'],
        'test_type_name': dict(TEST_TYPES).get(task['test_type'], task['test_type']),
        'test_path': task.get('test_path', ''),
        'scene': scene,
        'scene_name': scene_name,
        'env_config': task.get('env_config', {}),
        'status': task.get('status', 'idle'),
        'run_count': stats['run_count'],
        'last_run_at': stats['last_run_at'].isoformat() if stats['last_run_at'] else None,
        'created_by': task.get('created_by'),
        'created_at': task.get('created_at'),
        'updated_at': task.get('updated_at')
    }
