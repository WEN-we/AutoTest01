"""
集成配置数据模型
"""
import json
from backend.utils.database import Database


class Integration:
    """集成配置模型"""

    @staticmethod
    def find_all(integration_type=None):
        """获取所有集成配置"""
        if integration_type:
            sql = "SELECT * FROM integration_config WHERE integration_type = %s AND is_active = TRUE ORDER BY id"
            return Database.execute_query(sql, (integration_type,))
        else:
            sql = "SELECT * FROM integration_config WHERE is_active = TRUE ORDER BY integration_type, id"
            return Database.execute_query(sql)

    @staticmethod
    def find_by_id(integration_id: int):
        """根据ID查找集成配置"""
        sql = "SELECT * FROM integration_config WHERE id = %s"
        integration = Database.execute_query(sql, (integration_id,), fetch_one=True)

        if integration and integration.get('credentials') and isinstance(integration['credentials'], str):
            try:
                integration['credentials'] = json.loads(integration['credentials'])
            except:
                pass

        return integration

    @staticmethod
    def find_by_type(integration_type: str):
        """根据类型查找集成配置"""
        sql = "SELECT * FROM integration_config WHERE integration_type = %s AND is_active = TRUE LIMIT 1"
        integration = Database.execute_query(sql, (integration_type,), fetch_one=True)

        if integration and integration.get('credentials') and isinstance(integration['credentials'], str):
            try:
                integration['credentials'] = json.loads(integration['credentials'])
            except:
                pass

        return integration

    @staticmethod
    def create(data: dict, user_id: int) -> int:
        """创建集成配置"""
        credentials = data.get('credentials', {})
        if isinstance(credentials, dict):
            credentials = json.dumps(credentials)

        sql = """
            INSERT INTO integration_config
            (integration_type, name, base_url, auth_type, credentials, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s)
        """
        return Database.execute_insert(sql, (
            data['integration_type'],
            data['name'],
            data['base_url'],
            data.get('auth_type', 'basic'),
            credentials,
            user_id
        ))

    @staticmethod
    def update(integration_id: int, data: dict):
        """更新集成配置"""
        updates = []
        params = []

        fields = ['name', 'base_url', 'auth_type', 'is_active']
        for field in fields:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])

        if 'credentials' in data:
            updates.append("credentials = %s")
            credentials = data['credentials']
            if isinstance(credentials, dict):
                credentials = json.dumps(credentials)
            params.append(credentials)

        if updates:
            updates.append("updated_at = NOW()")
            sql = f"UPDATE integration_config SET {', '.join(updates)} WHERE id = %s"
            params.append(integration_id)
            Database.execute_update(sql, tuple(params))

    @staticmethod
    def delete(integration_id: int):
        """删除集成配置"""
        sql = "UPDATE integration_config SET is_active = FALSE WHERE id = %s"
        Database.execute_update(sql, (integration_id,))
