"""
AI智能体核心类 - 集成Skill系统
"""
import uuid
import time
from typing import Dict, List, Optional
from .skill_manager import skill_manager, Skill


class AIAgent:
    """AI智能体核心类 - 支持角色切换"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.agent_id = str(uuid.uuid4())[:8]
        self.name = config.get('name', 'AI智能体') if config else 'AI智能体'
        self.target_url = config.get('target_url', '') if config else ''
        self.scenario = config.get('scenario', '') if config else ''
        self.status = 'idle'  # idle/running/paused/completed/failed
        self.progress = 0
        self.current_step = 0
        self.total_steps = 0
        self.execution_logs = []
        self.results = {}
        self.created_at = time.time()
        
        # Skill系统集成
        self._current_skill: Optional[Skill] = None
        
    @property
    def current_skill(self) -> Optional[Skill]:
        """获取当前Skill"""
        return self._current_skill
    
    def load_skills(self) -> List[Dict]:
        """加载所有可用Skill"""
        skill_manager.load_skills()
        return skill_manager.list_skills()
    
    def switch_skill(self, skill_name: str) -> Dict:
        """切换到指定角色Skill"""
        if skill_manager.activate_skill(skill_name):
            self._current_skill = skill_manager.get_current_skill()
            return {
                'status': 'success',
                'message': f'已切换到「{self._current_skill.role}」角色',
                'skill': {
                    'name': self._current_skill.name,
                    'role': self._current_skill.role,
                    'description': self._current_skill.description,
                    'capabilities': self._current_skill.capabilities
                }
            }
        return {
            'status': 'error',
            'message': f'未找到Skill: {skill_name}'
        }
    
    def check_action(self, action: str) -> Dict:
        """检查当前角色是否允许执行该操作"""
        if not self._current_skill:
            return {
                'allowed': True,
                'message': '未选择角色，允许所有操作'
            }
        
        if self._current_skill.can_do(action):
            return {
                'allowed': True,
                'message': f'当前角色「{self._current_skill.role}」可以执行此操作'
            }
        
        if self._current_skill.cannot_do(action):
            suggestion = skill_manager.suggest_switch(action)
            return {
                'allowed': False,
                'message': self._current_skill.get_rejection_response(),
                'suggestion': suggestion
            }
        
        return {
            'allowed': True,
            'message': f'当前角色「{self._current_skill.role}」未明确禁止此操作'
        }
    
    def execute_action(self, action: str, **kwargs) -> Dict:
        """执行操作（会先检查角色权限）"""
        check_result = self.check_action(action)
        
        if not check_result['allowed']:
            return {
                'status': 'rejected',
                'message': check_result['message'],
                'suggestion': check_result.get('suggestion')
            }
        
        # 执行实际操作
        result = self._do_action(action, **kwargs)
        
        return {
            'status': 'success',
            'action': action,
            'skill': self._current_skill.role if self._current_skill else '无',
            'data': result
        }
    
    def _do_action(self, action: str, **kwargs) -> Dict:
        """执行实际操作"""
        action_handlers = {
            'page_analysis': self._handle_page_analysis,
            'test_generation': self._handle_test_generation,
            'test_execution': self._handle_test_execution,
            'result_analysis': self._handle_result_analysis,
            'report_generation': self._handle_report_generation,
            'code_writing': self._handle_code_writing,
            'code_debugging': self._handle_code_debugging,
            'data_analysis': self._handle_data_analysis
        }
        
        handler = action_handlers.get(action)
        if handler:
            return handler(**kwargs)
        
        return {'message': f'未知操作: {action}', 'params': kwargs}
    
    def _handle_page_analysis(self, **kwargs) -> Dict:
        """处理页面分析"""
        url = kwargs.get('url', self.target_url)
        return {
            'type': 'page_analysis',
            'url': url,
            'result': {
                'elements_found': 15,
                'forms': 2,
                'buttons': 5,
                'inputs': 8,
                'links': 12,
                'analysis_summary': f'成功分析页面: {url}'
            }
        }
    
    def _handle_test_generation(self, **kwargs) -> Dict:
        """处理测试用例生成"""
        url = kwargs.get('url', self.target_url)
        return {
            'type': 'test_generation',
            'url': url,
            'result': {
                'steps_generated': 8,
                'test_cases': [
                    {'step': 1, 'action': '输入用户名', 'element': '#username'},
                    {'step': 2, 'action': '输入密码', 'element': '#password'},
                    {'step': 3, 'action': '点击登录', 'element': 'button[type="submit"]'},
                    {'step': 4, 'action': '验证登录成功', 'element': '#welcome'}
                ],
                'summary': '已生成测试用例'
            }
        }
    
    def _handle_test_execution(self, **kwargs) -> Dict:
        """处理测试执行"""
        return {
            'type': 'test_execution',
            'result': {
                'status': 'completed',
                'total_steps': 8,
                'passed_steps': 7,
                'failed_steps': 1,
                'duration': 12.5,
                'logs': [
                    '步骤1: 输入用户名 - 成功',
                    '步骤2: 输入密码 - 成功',
                    '步骤3: 点击登录 - 成功',
                    '步骤4: 验证结果 - 成功'
                ],
                'summary': '测试执行完成'
            }
        }
    
    def _handle_result_analysis(self, **kwargs) -> Dict:
        """处理结果分析"""
        return {
            'type': 'result_analysis',
            'result': {
                'overall_status': 'passed',
                'success_rate': 87.5,
                'analysis': '测试整体通过，建议关注失败的步骤',
                'suggestions': [
                    '检查元素定位是否正确',
                    '增加等待时间',
                    '优化测试数据'
                ]
            }
        }
    
    def _handle_report_generation(self, **kwargs) -> Dict:
        """处理报告生成"""
        return {
            'type': 'report_generation',
            'result': {
                'title': '自动化测试报告',
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'content': {
                    'summary': '测试执行完成',
                    'metrics': {
                        'total_cases': 10,
                        'passed': 8,
                        'failed': 2,
                        'success_rate': 80
                    },
                    'charts': ['执行趋势图', '成功率分布图']
                }
            }
        }
    
    def _handle_code_writing(self, **kwargs) -> Dict:
        """处理代码编写"""
        return {
            'type': 'code_writing',
            'result': {
                'language': kwargs.get('language', 'Python'),
                'code': 'print("Hello, World!")',
                'explanation': '简单的打印语句示例'
            }
        }
    
    def _handle_code_debugging(self, **kwargs) -> Dict:
        """处理代码调试"""
        return {
            'type': 'code_debugging',
            'result': {
                'issue': '变量未定义',
                'line': 15,
                'suggestion': '检查变量作用域或初始化',
                'fix': '在使用前定义变量'
            }
        }
    
    def _handle_data_analysis(self, **kwargs) -> Dict:
        """处理数据分析"""
        return {
            'type': 'data_analysis',
            'result': {
                'dataset': kwargs.get('dataset', 'test_data'),
                'insights': [
                    '测试成功率趋势上升',
                    '移动端测试耗时较长',
                    'API测试稳定性良好'
                ],
                'recommendations': ['优化移动端测试', '增加API测试覆盖率']
            }
        }
    
    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'progress': self.progress,
            'current_skill': {
                'name': self._current_skill.name,
                'role': self._current_skill.role
            } if self._current_skill else None,
            'created_at': self.created_at
        }
    
    def get_logs(self) -> List[str]:
        """获取执行日志"""
        return self.execution_logs
    
    def add_log(self, message: str):
        """添加日志"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.execution_logs.append(f'[{timestamp}] {message}')
