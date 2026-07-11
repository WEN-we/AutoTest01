"""
配置管理模块
从YAML文件加载配置，实现代码与配置分离

支持两个配置目录：
1. web_platform/backend/config/ - Web平台后端配置
2. config/ - 项目级通用配置（测试配置等）
"""
import os
import yaml
from typing import Any, Optional

from utils.tools.path_manager import get_path, get_web_platform_config_path


class Config:
    """配置管理类"""

    def __init__(self, env='development', config_dir=None):
        self.env = env
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = get_web_platform_config_path()
        self._config = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        # Web平台后端配置
        backend_config_files = {
            'database': 'database.yaml',
            'app': 'app.yaml',
            'security': 'security.yaml',
            'integrations': 'integrations.yaml'
        }

        for key, filename in backend_config_files.items():
            filepath = os.path.join(self.config_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._config[key] = data.get(self.env, data)

        # 项目级通用配置（测试相关）
        project_config_dir = get_path('config')
        project_config_files = {
            'app_config': 'app_config.yaml',
            'env_config': 'env_config.yaml',
            'ui_config': 'ui_config.yaml',
            'linux_config': 'linux_config.yaml'
        }

        for key, filename in project_config_files.items():
            filepath = os.path.join(project_config_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        # env_config 特殊处理：需要读取 active_env 对应的配置
                        if filename == 'env_config.yaml' and data:
                            active_env = data.get('active_env', 'test')
                            env_data = data.get(active_env, {})
                            self._config['env'] = env_data
                        else:
                            self._config[key] = data

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号访问
        例如：config.get('database.host')
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        # 处理环境变量占位符
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.environ.get(env_var, default)

        return value

    def get_database_config(self):
        """获取数据库配置"""
        return self.get('database')

    def get_app_config(self):
        """获取应用配置"""
        return self.get('app')

    def get_security_config(self):
        """获取安全配置"""
        return self.get('security')

    def get_env_config(self):
        """获取当前环境配置"""
        return self.get('env')

    def get_ui_config(self):
        """获取UI自动化配置"""
        return self.get('ui_config')

    def get_app_automation_config(self):
        """获取APP自动化配置"""
        return self.get('app_config')


# 全局配置实例
config = Config(os.getenv('FLASK_ENV', 'development'))
