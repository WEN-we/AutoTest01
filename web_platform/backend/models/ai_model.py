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
            SELECT * FROM ai_model_config
            WHERE is_active = TRUE
            ORDER BY priority DESC, id ASC
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
        sql = "SELECT * FROM ai_model_config WHERE id = %s"
        return Database.execute_query(sql, (model_id,), fetch_one=True)

    @staticmethod
    def create(data: dict, user_id: int) -> int:
        """创建AI模型配置"""
        config = data.get('config', {})
        if isinstance(config, dict):
            config = json.dumps(config)

        sql = """
            INSERT INTO ai_model_config
            (model_type, model_name, api_key, base_url, model_id, priority, config, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
        """
        return Database.execute_insert(sql, (
            data['model_type'],
            data['model_name'],
            data.get('api_key', ''),
            data.get('base_url', ''),
            data.get('model_id', ''),
            data.get('priority', 0),
            config,
            user_id
        ))

    @staticmethod
    def update(model_id: int, data: dict):
        """更新AI模型配置"""
        updates = []
        params = []

        fields = ['model_name', 'api_key', 'base_url', 'model_id', 'priority', 'is_active']
        for field in fields:
            if field in data:
                updates.append(f"{field} = %s")
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
        sql = "UPDATE ai_model_config SET is_active = FALSE WHERE id = %s"
        Database.execute_update(sql, (model_id,))
