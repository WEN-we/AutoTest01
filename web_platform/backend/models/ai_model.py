"""
AI模型配置数据模型
"""
import json
from backend.utils.database import Database


class AIModel:
    """AI模型配置模型"""

    @staticmethod
    def find_all():
        """获取所有AI模型配置"""
        sql = """
            SELECT id, name as model_name, provider, model_type, api_endpoint as base_url, model_id, api_key, 
                   api_version, max_tokens, temperature, timeout, priority, status, is_default, 
                   config, created_by, created_at, updated_at
            FROM ai_model_config
            WHERE status = 'active'
            ORDER BY is_default DESC, id ASC
        """
        models = Database.execute_query(sql)

        for model in models:
            if model.get('config') and isinstance(model['config'], str):
                try:
                    model['config'] = json.loads(model['config'])
                except:
                    pass

        return models

    @staticmethod
    def find_by_id(model_id: int):
        """根据ID查找模型"""
        sql = """
            SELECT id, name as model_name, provider, model_type, api_endpoint as base_url, model_id, api_key,
                   api_version, max_tokens, temperature, timeout, priority, status, is_default,
                   config, created_by, created_at, updated_at
            FROM ai_model_config WHERE id = %s
        """
        return Database.execute_query(sql, (model_id,), fetch_one=True)

    @staticmethod
    def create(data: dict, user_id: int) -> int:
        """创建AI模型配置"""
        config = data.get('config', {})
        if isinstance(config, dict):
            config = json.dumps(config)

        sql = """
            INSERT INTO ai_model_config
            (name, provider, model_type, api_endpoint, model_id, api_key, api_version, max_tokens, temperature, timeout, priority, status, is_default, config, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return Database.execute_insert(sql, (
            data.get('model_name', ''),
            data.get('provider', 'openai'),
            data.get('model_type', ''),
            data.get('base_url', ''),
            data.get('model_id', ''),
            data.get('api_key', ''),
            data.get('api_version', ''),
            data.get('max_tokens', 4000),
            data.get('temperature', 0.7),
            data.get('timeout', 60),
            data.get('priority', 0) or 0,
            'active',
            0,
            config,
            user_id
        ))

    @staticmethod
    def update(model_id: int, data: dict):
        """更新AI模型配置"""
        updates = []
        params = []

        fields = {'model_name': 'name', 'model_type': 'model_type', 'model_id': 'model_id', 'api_key': 'api_key', 'base_url': 'api_endpoint', 'api_version': 'api_version', 'max_tokens': 'max_tokens', 'temperature': 'temperature', 'timeout': 'timeout', 'priority': 'priority', 'status': 'status', 'is_default': 'is_default'}
        for field, db_field in fields.items():
            if field in data:
                updates.append(f"{db_field} = %s")
                params.append(data[field])

        if 'config' in data:
            updates.append("config = %s")
            config = data['config']
            if isinstance(config, dict):
                config = json.dumps(config)
            params.append(config)

        if updates:
            updates.append("updated_at = NOW()")
            sql = f"UPDATE ai_model_config SET {', '.join(updates)} WHERE id = %s"
            params.append(model_id)
            Database.execute_update(sql, tuple(params))

    @staticmethod
    def delete(model_id: int):
        """删除AI模型配置"""
        sql = "UPDATE ai_model_config SET status = 'inactive' WHERE id = %s"
        Database.execute_update(sql, (model_id,))
