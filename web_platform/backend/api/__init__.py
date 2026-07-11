"""
API蓝图初始化
"""
from .auth import auth_bp
from .tasks import tasks_bp
from .execution import execution_bp
from .ai_models import ai_models_bp
from .jenkins import jenkins_bp
from .zentao import zentao_bp
from .reports import reports_bp
from .integrations import integrations_bp
from .ai_agents import ai_agents_bp

__all__ = [
    'auth_bp', 'tasks_bp', 'execution_bp', 'ai_models_bp',
    'jenkins_bp', 'zentao_bp', 'reports_bp', 'integrations_bp',
    'ai_agents_bp'
]
