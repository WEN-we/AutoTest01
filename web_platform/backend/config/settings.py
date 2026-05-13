"""
配置管理模块
从YAML文件加载配置，实现代码与配置分离
"""
import os
import yaml
from typing import Any, Optional


class Config:
    """配置管理类"""

    def __init__(self, env='development', config_dir=None):
        self.env = env
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        self._config = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        config_files = {
            'database': 'database.yaml',
            'app': 'app.yaml',
            'security': 'security.yaml',
            'integrations': 'integrations.yaml'
        }

        for key, filename in config_files.items():
            filepath = os.path.join(self.config_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._config[key] = data.get(self.env, data)

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


# 全局配置实例
config = Config(os.getenv('FLASK_ENV', 'development'))
