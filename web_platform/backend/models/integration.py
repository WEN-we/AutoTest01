"""
集成配置数据模型
"""
import json
from backend.utils.database import Database


class Integration:
    """集成配置模型"""

    @staticmethod
    def find_by_type_with_credentials(integration_type: str):
        """根据类型查找集成配置（优先返回默认配置，其次有凭证的配置）"""
        sql = """
            SELECT * FROM integration_config 
            WHERE integration_type = %s AND status = 'active' 
            ORDER BY 
                is_default DESC,
                CASE 
                    WHEN api_token IS NOT NULL AND api_token != '' AND username IS NOT NULL AND username != '' THEN 1
                    WHEN password IS NOT NULL AND password != '' AND username IS NOT NULL AND username != '' THEN 2
                    ELSE 3
                END ASC,
                id ASC
            LIMIT 1
        """
        integration = Database.execute_query(sql, (integration_type,), fetch_one=True)
        if integration:
            integration['is_active'] = integration.get('status') == 'active'
        return integration

    @staticmethod
    def find_default_by_type(integration_type: str):
        """查找指定类型的默认配置"""
        sql = """
            SELECT * FROM integration_config 
            WHERE integration_type = %s AND status = 'active' AND is_default = 1
            LIMIT 1
        """
        integration = Database.execute_query(sql, (integration_type,), fetch_one=True)
        if integration:
            integration['is_active'] = integration.get('status') == 'active'
        return integration

    @staticmethod
    def set_default(integration_id: int, integration_type: str):
        """设置默认配置（同类型其他配置取消默认）"""
        # 先取消同类型的所有默认
        sql_clear = """
            UPDATE integration_config 
            SET is_default = 0 
            WHERE integration_type = %s AND status = 'active'
        """
        Database.execute_update(sql_clear, (integration_type,))
        
        # 设置当前为默认
        sql_set = """
            UPDATE integration_config 
            SET is_default = 1 
            WHERE id = %s
        """
        Database.execute_update(sql_set, (integration_id,))

    @staticmethod
    def find_all(integration_type=None):
        """获取所有集成配置"""
        if integration_type:
            sql = "SELECT * FROM integration_config WHERE integration_type = %s AND status = 'active' ORDER BY id ASC"
            results = Database.execute_query(sql, (integration_type,))
        else:
            sql = "SELECT * FROM integration_config WHERE status = 'active' ORDER BY id ASC"
            results = Database.execute_query(sql)

        if results:
            for r in results:
                r['is_active'] = r.get('status') == 'active'
        return results

    @staticmethod
    def find_by_id(integration_id: int):
        """根据ID查找集成配置"""
        sql = "SELECT * FROM integration_config WHERE id = %s"
        integration = Database.execute_query(sql, (integration_id,), fetch_one=True)

        if integration:
            integration['is_active'] = integration.get('status') == 'active'

        return integration

    @staticmethod
    def find_by_type(integration_type: str):
        """根据类型查找集成配置"""
        sql = "SELECT * FROM integration_config WHERE integration_type = %s AND status = 'active' LIMIT 1"
        integration = Database.execute_query(sql, (integration_type,), fetch_one=True)

        if integration:
            integration['is_active'] = integration.get('status') == 'active'

        return integration

    @staticmethod
    def create(data: dict, user_id: int) -> int:
        """创建集成配置"""
        credentials = data.get('credentials', {})
        if not isinstance(credentials, dict):
            credentials = {}

        integration_type = data.get('integration_type', '')
        auth_type = data.get('auth_type', 'basic')

        username = None
        password = None
        api_token = None

        if integration_type == 'jenkins':
            username = credentials.get('username')
            api_token = credentials.get('api_token')
        elif integration_type == 'zentao':
            account = credentials.get('account')
            username = account
            password = credentials.get('password')

        sql = """
            INSERT INTO integration_config
            (integration_type, name, base_url, auth_type, username, password, api_token, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s)
        """
        return Database.execute_insert(sql, (
            integration_type,
            data['name'],
            data['base_url'],
            auth_type,
            username,
            password,
            api_token,
            user_id
        ))

    @staticmethod
    def update(integration_id: int, data: dict):
        """更新集成配置"""
        updates = []
        params = []

        field_mapping = {'name': 'name', 'base_url': 'base_url', 'auth_type': 'auth_type', 'is_active': 'status'}
        for field, db_field in field_mapping.items():
            if field in data:
                value = data[field]
                if field == 'is_active':
                    value = 'active' if value else 'inactive'
                updates.append(f"{db_field} = %s")
                params.append(value)

        # 处理credentials JSON格式（旧格式）
        if 'credentials' in data:
            credentials = data['credentials']
            if isinstance(credentials, dict):
                if 'username' in credentials or 'account' in credentials:
                    updates.append("username = %s")
                    params.append(credentials.get('username') or credentials.get('account'))
                if 'password' in credentials:
                    updates.append("password = %s")
                    params.append(credentials['password'])
                if 'api_token' in credentials:
                    updates.append("api_token = %s")
                    params.append(credentials['api_token'])

        # 处理直接字段格式（新格式，来自编辑弹窗）
        if 'username' in data:
            updates.append("username = %s")
            params.append(data['username'])
        if 'password' in data:
            updates.append("password = %s")
            params.append(data['password'])
        if 'api_token' in data:
            updates.append("api_token = %s")
            params.append(data['api_token'])
        if 'account' in data:
            updates.append("username = %s")
            params.append(data['account'])

        if updates:
            updates.append("updated_at = NOW()")
            sql = f"UPDATE integration_config SET {', '.join(updates)} WHERE id = %s"
            params.append(integration_id)
            Database.execute_update(sql, tuple(params))

    @staticmethod
    def delete(integration_id: int):
        """删除集成配置"""
        sql = "UPDATE integration_config SET status = 'inactive' WHERE id = %s"
        Database.execute_update(sql, (integration_id,))