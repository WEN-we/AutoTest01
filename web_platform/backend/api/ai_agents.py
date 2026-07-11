"""
AI智能体API
企业级AI测试智能体管理接口 - 数据库持久化版本
"""
from flask import Blueprint, request, jsonify
import logging
import uuid
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_agents_bp = Blueprint('ai_agents', __name__)

# 内存中保存Agent实例（用于运行时），元数据保存到数据库
agent_instances = {}


def get_agent_service():
    """获取Agent服务"""
    try:
        from agents.test_agent import TestAgent
        return TestAgent
    except Exception as e:
        logger.error(f"加载Agent服务失败: {e}")
        return None


# 模拟Agent类，用于当真实Agent服务不可用时
class MockAgent:
    """模拟Agent类 - 提供与TestAgent兼容的工具模拟"""
    
    def __init__(self, initial_skill='test_expert'):
        self.current_skill = initial_skill
        self.state = 'idle'
        self.stats = {'total_actions': 0, 'success_count': 0, 'failed_count': 0}
    
    def get_current_skill_info(self):
        return {'id': self.current_skill, 'name': '测试专家', 'role': '测试专家'}
    
    def list_available_skills(self):
        return [
            {'id': 'test_expert', 'name': '测试专家', 'description': '专注于软件测试的AI助手'},
            {'id': 'code_analyzer', 'name': '代码分析师', 'description': '分析和优化代码的AI助手'}
        ]
    
    def switch_skill(self, skill_id):
        self.current_skill = skill_id
        return {
            'success': True, 
            'message': f'已切换到角色: {skill_id}',
            'skill_info': {'id': skill_id, 'name': skill_id}
        }
    
    def check_action_permission(self, action):
        return {'allowed': True}
    
    def execute_action(self, action, **kwargs):
        """执行指定动作 - 模拟各工具的执行结果"""
        import time
        
        if action == 'analyze_page':
            page = kwargs.get('page', {})
            url = kwargs.get('url', '') or (page.get('url') if isinstance(page, dict) else '')
            return {
                'success': True,
                'action': action,
                'result': {
                    'page_info': {
                        'title': '模拟页面',
                        'url': url or 'https://example.com',
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                    },
                    'elements': [
                        {'type': 'input', 'identifier': 'username', 'locator': '#username', 'purpose': '用户名输入'},
                        {'type': 'input', 'identifier': 'password', 'locator': '#password', 'purpose': '密码输入'},
                        {'type': 'button', 'identifier': 'login', 'locator': '#loginBtn', 'purpose': '登录按钮'}
                    ],
                    'business_logic': '用户登录功能',
                    'test_suggestions': ['测试正常登录', '测试错误密码', '测试空输入验证']
                }
            }
        
        elif action == 'generate_test_cases':
            return {
                'success': True,
                'action': action,
                'result': {
                    'test_cases': [
                        {
                            'id': 'TC-001',
                            'name': '正常登录测试',
                            'description': '使用正确的用户名和密码登录',
                            'priority': 'high',
                            'steps': [
                                {'step_num': 1, 'action': 'input', 'element': '#username', 'value': 'testuser'},
                                {'step_num': 2, 'action': 'input', 'element': '#password', 'value': 'password123'},
                                {'step_num': 3, 'action': 'click', 'element': '#loginBtn'},
                                {'step_num': 4, 'action': 'assert', 'element': '.welcome-msg', 'expected_result': '欢迎'}
                            ]
                        }
                    ]
                }
            }
        
        elif action == 'execute_test_step':
            step = kwargs.get('step', {})
            return {
                'success': True,
                'action': action,
                'result': {
                    'step': step,
                    'success': True,
                    'retry': 0,
                    'message': f'步骤执行成功: {step.get("action", "unknown")}'
                }
            }
        
        elif action == 'execute_test_suite':
            test_cases = kwargs.get('test_cases', [])
            return {
                'success': True,
                'action': action,
                'result': {
                    'total': len(test_cases),
                    'passed': len(test_cases),
                    'failed': 0,
                    'duration': 1.23,
                    'results': []
                }
            }
        
        elif action == 'assert_result':
            actual = kwargs.get('actual', '')
            expected = kwargs.get('expected', '')
            assertion_type = kwargs.get('assertion_type', 'equal')
            
            if assertion_type == 'equal':
                success = str(actual) == str(expected)
            elif assertion_type == 'contain':
                success = str(expected) in str(actual)
            else:
                success = True
                
            return {
                'success': True,
                'action': action,
                'result': {
                    'success': success,
                    'assertion_type': assertion_type,
                    'actual': actual,
                    'expected': expected,
                    'message': '断言验证通过' if success else '断言验证失败'
                }
            }
        
        elif action == 'analyze_test_result':
            return {
                'success': True,
                'action': action,
                'result': {
                    'overall_status': 'passed',
                    'root_cause': '',
                    'failure_category': '',
                    'repair_suggestions': [],
                    'risk_assessment': '低风险',
                    'confidence': 0.95
                }
            }
        
        elif action == 'generate_test_report':
            test_results = kwargs.get('test_results', [])
            return {
                'success': True,
                'action': action,
                'result': {
                    'report_id': f'REP-MOCK',
                    'generated_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'summary': {
                        'total': len(test_results),
                        'passed': len(test_results),
                        'failed': 0,
                        'pass_rate': 100.0
                    }
                }
            }
        
        elif action == 'take_screenshot':
            return {
                'success': True,
                'action': action,
                'result': {
                    'success': True,
                    'path': '/mock/screenshot.png',
                    'name': kwargs.get('name', 'screenshot')
                }
            }
        
        else:
            return {
                'success': True,
                'action': action,
                'result': f'模拟执行: {action}，参数: {kwargs}'
            }
    
    def execute_with_skill_check(self, action, **params):
        """执行操作前检查Skill权限"""
        permission_check = self.check_action_permission(action)
        if not permission_check.get("allowed", True):
            return {
                'status': 'rejected',
                'message': permission_check.get('message', '权限不足'),
                'suggested_skill': permission_check.get('suggested_skill')
            }
        
        self.stats['total_actions'] += 1
        result = self.execute_action(action, **params)
        
        if result.get('success'):
            self.stats['success_count'] += 1
        else:
            self.stats['failed_count'] += 1
            
        return result
    
    def get_statistics(self):
        return {
            'total_tests': self.stats['total_actions'],
            'passed': self.stats['success_count'],
            'failed': self.stats['failed_count'],
            'current_state': self.state,
            'current_skill': self.get_current_skill_info()
        }


def _ensure_agent_instance(agent_id: str, agent_data: dict):
    """确保Agent实例存在于内存中"""
    if agent_id not in agent_instances:
        TestAgent = get_agent_service()
        current_skill = agent_data.get('current_skill', 'test_expert')
        
        if TestAgent:
            try:
                agent = TestAgent(initial_skill=current_skill)
                agent_instances[agent_id] = agent
            except Exception as e:
                logger.error(f"创建真实Agent实例失败，使用模拟Agent: {e}")
                agent = MockAgent(initial_skill=current_skill)
                agent_instances[agent_id] = agent
        else:
            logger.warning("Agent服务不可用，使用模拟Agent")
            agent = MockAgent(initial_skill=current_skill)
            agent_instances[agent_id] = agent
    
    return agent_instances.get(agent_id)


@ai_agents_bp.route('/ai-agents', methods=['GET'])
def list_agents():
    """列出所有AI智能体"""
    try:
        from backend.models.ai_agent import AIAgent
        
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        status = request.args.get('status', None)
        
        result = AIAgent.find_all(page=page, page_size=page_size, status=status)
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'total': result['total'],
                'items': result['items']
            }
        })
    except Exception as e:
        logger.error(f"列出AI智能体失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents', methods=['POST'])
def create_agent():
    """创建AI智能体"""
    try:
        from backend.models.ai_agent import AIAgent
        
        json_data = request.get_json(silent=True)
        if not json_data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        agent_id = str(uuid.uuid4())[:8]
        name = json_data.get('name', f"TestAgent_{agent_id}")
        description = json_data.get('description', '')
        initial_skill = json_data.get('skill', 'test_expert')
        config = json_data.get('config', {})

        # 保存到数据库
        AIAgent.create(
            agent_id=agent_id,
            name=name,
            description=description,
            current_skill=initial_skill,
            config=config
        )

        # 创建Agent实例到内存
        TestAgent = get_agent_service()
        if TestAgent:
            agent = TestAgent(initial_skill=initial_skill)
            agent_instances[agent_id] = agent

        return jsonify({
            'code': 200,
            'message': '创建成功',
            'data': {
                'agent_id': agent_id,
                'name': name,
                'current_skill': initial_skill
            }
        })
    except Exception as e:
        logger.error(f"创建AI智能体失败: {e}")
        return jsonify({'code': 500, 'message': f'创建失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """获取AI智能体详情"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        # 确保内存中有实例
        agent = _ensure_agent_instance(agent_id, agent_data)
        
        # 获取运行时状态
        runtime_status = 'idle'
        runtime_skill_info = None
        runtime_stats = None
        
        if agent:
            if hasattr(agent, 'state') and hasattr(agent.state, 'value'):
                runtime_status = agent.state.value
            elif hasattr(agent, 'state'):
                runtime_status = str(agent.state)
            else:
                runtime_status = 'idle'
            runtime_skill_info = agent.get_current_skill_info()
            runtime_stats = agent.get_statistics()

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'agent_id': agent_id,
                'name': agent_data['name'],
                'description': agent_data.get('description', ''),
                'status': runtime_status,
                'current_skill': runtime_skill_info or agent_data.get('current_skill'),
                'created_at': agent_data['created_at'].isoformat() if agent_data.get('created_at') else None,
                'last_active': agent_data['last_active'].isoformat() if agent_data.get('last_active') else None,
                'statistics': runtime_stats or agent_data.get('statistics', {}),
                'skill_history': agent_data.get('skill_history', [])
            }
        })
    except Exception as e:
        logger.error(f"获取AI智能体详情失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """删除AI智能体"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        # 从数据库删除
        AIAgent.delete(agent_id)
        
        # 从内存移除
        if agent_id in agent_instances:
            del agent_instances[agent_id]

        return jsonify({'code': 200, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除AI智能体失败: {e}")
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """更新AI智能体"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404
        
        json_data = request.get_json(silent=True)
        if not json_data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400
        
        # 更新数据库
        update_fields = {}
        if 'name' in json_data:
            update_fields['name'] = json_data['name']
        if 'description' in json_data:
            update_fields['description'] = json_data['description']
        if 'config' in json_data:
            update_fields['config'] = json_data['config']
        
        if update_fields:
            AIAgent.update(agent_id, **update_fields)
        
        return jsonify({'code': 200, 'message': '更新成功'})
    except Exception as e:
        logger.error(f"更新AI智能体失败: {e}")
        return jsonify({'code': 500, 'message': f'更新失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/skills', methods=['GET'])
def list_skills(agent_id):
    """列出可用的Skill"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        agent = _ensure_agent_instance(agent_id, agent_data)
        skills = agent.list_available_skills() if agent else []

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {'skills': skills}
        })
    except Exception as e:
        logger.error(f"列出Skill失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/skills', methods=['POST'])
def switch_skill(agent_id):
    """切换Skill"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        json_data = request.get_json(silent=True)
        if not json_data or 'skill_id' not in json_data:
            return jsonify({'code': 400, 'message': '缺少 skill_id 参数'}), 400

        skill_id = json_data['skill_id']
        agent = _ensure_agent_instance(agent_id, agent_data)
        
        if not agent:
            return jsonify({'code': 500, 'message': 'Agent实例不可用'}), 500
        
        result = agent.switch_skill(skill_id)

        if result['success']:
            # 更新数据库
            AIAgent.update_skill(agent_id, skill_id)

        return jsonify({
            'code': 200 if result['success'] else 400,
            'message': result['message'],
            'data': result.get('skill_info')
        })
    except Exception as e:
        logger.error(f"切换Skill失败: {e}")
        return jsonify({'code': 500, 'message': f'切换失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/skills/current', methods=['GET'])
def get_current_skill(agent_id):
    """获取当前Skill"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        agent = _ensure_agent_instance(agent_id, agent_data)
        skill_info = agent.get_current_skill_info() if agent else None

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {'current_skill': skill_info or agent_data.get('current_skill')}
        })
    except Exception as e:
        logger.error(f"获取当前Skill失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/execute', methods=['POST'])
def execute_action(agent_id):
    """执行操作"""
    try:
        from backend.models.ai_agent import AIAgent, AIAgentExecutionLog
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        json_data = request.get_json(silent=True)
        if not json_data or 'action' not in json_data:
            return jsonify({'code': 400, 'message': '缺少 action 参数'}), 400

        action = json_data['action']
        params = json_data.get('params', {})

        agent = _ensure_agent_instance(agent_id, agent_data)
        if not agent:
            return jsonify({'code': 500, 'message': 'Agent实例不可用'}), 500
        
        # 更新状态为运行中
        AIAgent.update_status(agent_id, 'running')
        
        # 记录执行日志
        log_id = AIAgentExecutionLog.create(
            agent_id=agent_id,
            action=action,
            skill=agent_data.get('current_skill'),
            input_params=params
        )
        
        start_time = time.time()
        
        try:
            result = agent.execute_with_skill_check(action, **params)
            duration = time.time() - start_time
            
            # 更新执行日志
            AIAgentExecutionLog.complete(
                log_id=log_id,
                output=result,
                status='success',
                duration=duration
            )
            
            # 更新统计信息
            stats = agent.get_statistics()
            AIAgent.update_statistics(agent_id, stats)
            
            return jsonify({
                'code': 200,
                'message': '执行完成',
                'data': result
            })
        except Exception as exec_error:
            duration = time.time() - start_time
            AIAgentExecutionLog.complete(
                log_id=log_id,
                status='failed',
                error_message=str(exec_error),
                duration=duration
            )
            raise exec_error
        finally:
            AIAgent.update_status(agent_id, 'idle')
            
    except Exception as e:
        logger.error(f"执行操作失败: {e}")
        return jsonify({'code': 500, 'message': f'执行失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/status', methods=['GET'])
def get_agent_status(agent_id):
    """获取智能体状态"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        agent = _ensure_agent_instance(agent_id, agent_data)
        status = agent.state.value if agent and hasattr(agent, 'state') else agent_data.get('status', 'idle')
        skill_info = agent.get_current_skill_info() if agent else None

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'status': status,
                'current_skill': skill_info or agent_data.get('current_skill')
            }
        })
    except Exception as e:
        logger.error(f"获取智能体状态失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/statistics', methods=['GET'])
def get_agent_statistics(agent_id):
    """获取统计信息"""
    try:
        from backend.models.ai_agent import AIAgent
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404

        agent = _ensure_agent_instance(agent_id, agent_data)
        stats = agent.get_statistics() if agent else agent_data.get('statistics', {})

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/<agent_id>/logs', methods=['GET'])
def get_agent_logs(agent_id):
    """获取执行日志"""
    try:
        from backend.models.ai_agent import AIAgent, AIAgentExecutionLog
        
        agent_data = AIAgent.find_by_agent_id(agent_id)
        if not agent_data:
            return jsonify({'code': 404, 'message': '智能体不存在'}), 404
        
        limit = request.args.get('limit', 100, type=int)
        logs = AIAgentExecutionLog.find_by_agent(agent_id, limit)
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {'logs': logs}
        })
    except Exception as e:
        logger.error(f"获取执行日志失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


@ai_agents_bp.route('/ai-agents/skills', methods=['GET'])
def list_all_skills():
    """列出所有可用的Skill(不依赖具体Agent)"""
    try:
        skills = []
        try:
            from agents.skill_manager import skill_manager
            skills = skill_manager.list_skills()
        except Exception as e:
            logger.warning(f"加载真实skill_manager失败，使用默认Skill列表: {e}")
            # 使用默认Skill列表
            skills = [
                {'id': 'test_expert', 'name': '测试专家', 'description': '专注于软件测试的AI助手'},
                {'id': 'code_analyzer', 'name': '代码分析师', 'description': '分析和优化代码的AI助手'},
                {'id': 'ai_test_agent', 'name': 'AI测试代理', 'description': 'AI驱动的测试自动化助手'},
                {'id': 'report_expert', 'name': '报告专家', 'description': '生成和分析测试报告的AI助手'}
            ]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {'skills': skills}
        })
    except Exception as e:
        logger.error(f"列出所有Skill失败: {e}")
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500
