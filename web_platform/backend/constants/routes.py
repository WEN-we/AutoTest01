"""
路由常量定义
集中管理所有URL路由和API前缀
"""

# API蓝图前缀
API_PREFIXES = {
    'auth': '/api/auth',
    'tasks': '/api/tasks',
    'execution': '/api',
    'ai_models': '/api/ai-models',
    'ai_agents': '/api',
    'integrations': '/api/integrations',
    'jenkins': '/api/integrations/jenkins',
    'zentao': '/api/integrations/zentao',
    'reports': '/api/reports'
}

# 前端路由映射（路径 -> 文件名）
FRONTEND_ROUTES = [
    {'path': '/', 'file': 'index.html'},
    {'path': '/index.html', 'file': 'index.html'},
    {'path': '/dashboard', 'file': 'dashboard.html'},
    {'path': '/dashboard.html', 'file': 'dashboard.html'},
    {'path': '/tasks', 'file': 'tasks.html'},
    {'path': '/tasks.html', 'file': 'tasks.html'},
    {'path': '/tasks/create', 'file': 'tasks-create.html'},
    {'path': '/tasks-create.html', 'file': 'tasks-create.html'},
    {'path': '/execution-list.html', 'file': 'execution-list.html'},
    {'path': '/jenkins', 'file': 'jenkins.html'},
    {'path': '/jenkins.html', 'file': 'jenkins.html'},
    {'path': '/zentao', 'file': 'zentao.html'},
    {'path': '/zentao.html', 'file': 'zentao.html'},
    {'path': '/integrations', 'file': 'integrations.html'},
    {'path': '/integrations.html', 'file': 'integrations.html'},
    {'path': '/reports', 'file': 'reports.html'},
    {'path': '/reports.html', 'file': 'reports.html'},
    {'path': '/ai-models', 'file': 'ai-models.html'},
    {'path': '/ai-models.html', 'file': 'ai-models.html'},
    {'path': '/ai-agents', 'file': 'ai-agents.html'},
    {'path': '/ai-agents.html', 'file': 'ai-agents.html'},
    {'path': '/ai-agents-detail.html', 'file': 'ai-agents-detail.html'},
]

# 动态路由模板（需要参数）
DYNAMIC_ROUTES = [
    {'path': '/tasks/<task_id>', 'file': 'tasks-detail.html'},
    {'path': '/tasks-detail.html', 'file': 'tasks-detail.html'},
    {'path': '/execution/<execution_id>', 'file': 'execution-monitor.html'},
    {'path': '/execution-monitor.html', 'file': 'execution-monitor.html'},
    {'path': '/ai-agents/<agent_id>', 'file': 'ai-agents-detail.html'},
    {'path': '/report-detail.html', 'file': 'report-detail.html'},
]

# 静态资源路由
STATIC_ROUTES = {
    'static': '/static/<path:filename>',
    'avatars': '/uploads/avatars/<path:filename>',
    'allure_report': '/reports/allure-report/<path:filename>',
    'allure_results': '/reports/allure-results/<path:filename>'
}
