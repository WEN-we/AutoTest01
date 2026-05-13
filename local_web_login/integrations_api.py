"""
集成配置API
"""
from flask import Blueprint, request, jsonify
from local_web_login.backend_server import (
    login_required, success_response, error_response,
    Database
)
from utils.tools.logger import log as logger
import json

integrations_bp = Blueprint('integrations', __name__, url_prefix='/api/integrations')


@integrations_bp.route('', methods=['GET'])
@login_required
def get_integrations():
    """获取集成列表"""
    try:
        integration_type = request.args.get('type')

        sql = "SELECT * FROM integration_config WHERE 1=1"
        params = []

        if integration_type:
            sql += " AND integration_type = %s"
            params.append(integration_type)

        sql += " ORDER BY integration_type, id"

        integrations = Database.execute_query(sql, tuple(params))

        for integration in integrations:
            if integration.get('credentials') and isinstance(integration['credentials'], str):
                try:
                    integration['credentials'] = json.loads(integration['credentials'])
                except:
                    pass

            if integration.get('config') and isinstance(integration['config'], str):
                try:
                    integration['config'] = json.loads(integration['config'])
                except:
                    pass

            if integration.get('credentials') and integration['credentials'].get('password'):
                integration['credentials']['password'] = '********'
            if integration.get('credentials') and integration['credentials'].get('api_token'):
                integration['credentials']['api_token'] = '********'

        return jsonify(success_response(data={"integrations": integrations}))
    except Exception as e:
        logger.error(f"获取集成列表失败: {e}")
        return error_response("获取集成列表失败", 500)


@integrations_bp.route('/<int:integration_id>', methods=['GET'])
@login_required
def get_integration_detail(integration_id):
    """获取集成详情"""
    try:
        sql = "SELECT * FROM integration_config WHERE id = %s"
        integration = Database.execute_query(sql, (integration_id,), fetch_one=True)

        if not integration:
            return error_response("集成不存在", 404)

        if integration.get('credentials') and isinstance(integration['credentials'], str):
            try:
                integration['credentials'] = json.loads(integration['credentials'])
            except:
                pass

        if integration.get('config') and isinstance(integration['config'], str):
            try:
                integration['config'] = json.loads(integration['config'])
            except:
                pass

        return jsonify(success_response(data=integration))
    except Exception as e:
        logger.error(f"获取集成详情失败: {e}")
        return error_response("获取集成详情失败", 500)


@integrations_bp.route('', methods=['POST'])
@login_required
def create_integration():
    """创建集成配置"""
    try:
        data = request.get_json()

        integration_type = data.get('integration_type', '').strip()
        name = data.get('name', '').strip()
        base_url = data.get('base_url', '').strip()
        auth_type = data.get('auth_type', 'api_key')
        credentials = data.get('credentials', {})
        config = data.get('config', {})

        if not integration_type or not name or not base_url:
            return error_response("集成类型、名称和URL不能为空")

        if integration_type not in ['jenkins', 'zentao', 'gitlab', 'jira']:
            return error_response("不支持的集成类型")

        if isinstance(credentials, dict):
            credentials = json.dumps(credentials)

        if isinstance(config, dict):
            config = json.dumps(config)

        sql = """
            INSERT INTO integration_config
            (integration_type, name, base_url, auth_type, credentials, config, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
        """

        Database.execute_update(
            sql,
            (integration_type, name, base_url, auth_type, credentials, config, request.current_user['id'])
        )

        result = Database.execute_query("SELECT LAST_INSERT_ID() as id", fetch_one=True)

        logger.info(f"创建集成配置成功: {name} ({integration_type})")

        return jsonify(success_response(
            data={"integration_id": result['id']},
            message="集成配置创建成功"
        ))
    except Exception as e:
        logger.error(f"创建集成配置失败: {e}")
        return error_response("创建集成配置失败", 500)


@integrations_bp.route('/<int:integration_id>', methods=['PUT'])
@login_required
def update_integration(integration_id):
    """更新集成配置"""
    try:
        data = request.get_json()

        sql = "UPDATE integration_config SET updated_at = NOW()"
        updates = []
        params = []

        if 'name' in data:
            updates.append("name = %s")
            params.append(data['name'])

        if 'base_url' in data:
            updates.append("base_url = %s")
            params.append(data['base_url'])

        if 'auth_type' in data:
            updates.append("auth_type = %s")
            params.append(data['auth_type'])

        if 'credentials' in data:
            updates.append("credentials = %s")
            params.append(json.dumps(data['credentials']))

        if 'is_active' in data:
            updates.append("is_active = %s")
            params.append(data['is_active'])

        if 'config' in data:
            updates.append("config = %s")
            params.append(json.dumps(data['config']))

        if not updates:
            return error_response("没有需要更新的字段")

        sql = "UPDATE integration_config SET " + ", ".join(updates) + " WHERE id = %s"
        params.append(integration_id)

        Database.execute_update(sql, tuple(params))

        logger.info(f"更新集成配置成功: {integration_id}")

        return jsonify(success_response(message="集成配置更新成功"))
    except Exception as e:
        logger.error(f"更新集成配置失败: {e}")
        return error_response("更新集成配置失败", 500)


@integrations_bp.route('/<int:integration_id>', methods=['DELETE'])
@login_required
def delete_integration(integration_id):
    """删除集成配置"""
    try:
        sql = "UPDATE integration_config SET is_active = FALSE WHERE id = %s"
        affected = Database.execute_update(sql, (integration_id,))

        if affected == 0:
            return error_response("集成不存在", 404)

        logger.info(f"删除集成配置: {integration_id}")

        return jsonify(success_response(message="集成配置已删除"))
    except Exception as e:
        logger.error(f"删除集成配置失败: {e}")
        return error_response("删除集成配置失败", 500)


@integrations_bp.route('/<integration_type>/test', methods=['POST'])
@login_required
def test_integration(integration_type):
    """测试集成连接"""
    try:
        integration_id = request.json.get('integration_id')

        if integration_type == 'jenkins':
            from local_web_login.jenkins_api import jenkins_api_request, get_jenkins_config
            config = get_jenkins_config()

            if not config:
                return error_response("Jenkins未配置", 400)

            response, error = jenkins_api_request('GET', 'api/json')

            if error:
                return error_response(error, 400)

            if response.status_code == 200:
                return jsonify(success_response(
                    data={"status": "connected"},
                    message="Jenkins连接成功"
                ))
            else:
                return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        elif integration_type == 'zentao':
            from local_web_login.zentao_api import zentao_get_session
            token_info, error = zentao_get_session()

            if error:
                return error_response(error, 400)

            return jsonify(success_response(
                data={"status": "connected"},
                message="禅道连接成功"
            ))

        else:
            return error_response(f"不支持的集成类型: {integration_type}", 400)

    except Exception as e:
        logger.error(f"测试集成连接失败: {e}")
        return error_response("测试连接失败", 500)
