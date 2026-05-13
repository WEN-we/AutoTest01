# 路径管理工具
# 用于统一管理项目中的文件路径，避免硬编码路径导致的问题

import os

class PathManager:
    """路径管理器"""
    
    def __init__(self):
        # 获取项目根目录
        self.root_dir = self._get_root_dir()
    
    def _get_root_dir(self):
        """获取项目根目录"""
        current_dir = os.path.abspath(__file__)
        # 向上查找，直到找到包含 .git 或 requirements.txt 的目录
        while current_dir != os.path.dirname(current_dir):
            if os.path.exists(os.path.join(current_dir, '.git')) or \
               os.path.exists(os.path.join(current_dir, 'requirements.txt')):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        return current_dir
    
    def get_path(self, *args):
        """获取基于根目录的路径"""
        return os.path.join(self.root_dir, *args)
    
    def get_config_path(self, config_file):
        """获取配置文件路径"""
        return self.get_path('config', config_file)
    
    def get_test_data_path(self, *args):
        """获取测试数据路径"""
        return self.get_path('test_data', *args)
    
    def get_test_path(self, *args):
        """获取测试文件路径"""
        return self.get_path('tests', *args)
    
    def get_utils_path(self, *args):
        """获取工具文件路径"""
        return self.get_path('utils', *args)
    
    def get_local_web_login_path(self, *args):
        """获取本地登录服务路径"""
        return self.get_path('local_web_login', *args)
    
    def get_report_path(self, *args):
        """获取报告路径"""
        return self.get_path('report', *args)
    
    def get_log_path(self, *args):
        """获取日志路径"""
        return self.get_path('logs', *args)
    
    def get_web_platform_path(self, *args):
        """获取web平台路径"""
        return self.get_path('web_platform', *args)
    
    def get_web_platform_backend_path(self, *args):
        """获取web平台后端路径"""
        return self.get_web_platform_path('backend', *args)
    
    def get_web_platform_frontend_path(self, *args):
        """获取web平台前端路径"""
        return self.get_web_platform_path('frontend', *args)
    
    def get_web_platform_config_path(self, *args):
        """获取web平台配置路径"""
        return self.get_web_platform_backend_path('config', *args)
    
    def get_web_platform_api_path(self, *args):
        """获取web平台API路径"""
        return self.get_web_platform_backend_path('api', *args)
    
    def get_web_platform_models_path(self, *args):
        """获取web平台模型路径"""
        return self.get_web_platform_backend_path('models', *args)
    
    def get_web_platform_services_path(self, *args):
        """获取web平台服务路径"""
        return self.get_web_platform_backend_path('services', *args)
    
    def get_reports_path(self, *args):
        """获取报告路径"""
        return self.get_path('web_platform', 'reports', *args)

# 单例模式，确保全局只有一个 PathManager 实例
path_manager = PathManager()

# 导出常用方法
get_path = path_manager.get_path
get_config_path = path_manager.get_config_path
get_test_data_path = path_manager.get_test_data_path
get_test_path = path_manager.get_test_path
get_utils_path = path_manager.get_utils_path
get_local_web_login_path = path_manager.get_local_web_login_path
get_report_path = path_manager.get_report_path
get_log_path = path_manager.get_log_path
get_web_platform_path = path_manager.get_web_platform_path
get_web_platform_backend_path = path_manager.get_web_platform_backend_path
get_web_platform_frontend_path = path_manager.get_web_platform_frontend_path
get_web_platform_config_path = path_manager.get_web_platform_config_path
get_web_platform_api_path = path_manager.get_web_platform_api_path
get_web_platform_models_path = path_manager.get_web_platform_models_path
get_web_platform_services_path = path_manager.get_web_platform_services_path
get_reports_path = path_manager.get_reports_path