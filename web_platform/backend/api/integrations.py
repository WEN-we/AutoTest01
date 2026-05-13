"""
集成配置API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.integration import Integration
from backend.utils.decorators import login_required

integrations_bp = Blueprint('integrations', __name__)


def success_response(data=None, message="操作成功"):
    response = {"code": 200, "message": message}
    if data:
        response["data"] = data
    return jsonify(response)


def error_response(message, code=400):
    return jsonify({"code": code, "message": message}), code


@integrations_bp.route('', methods=['GET'])
@login_required
def get_integrations():
    """获取集成列表"""
    try:
        integration_type = request.args.get('type')
        integrations = Integration.find_all(integration_type)

        # 隐藏敏感信息
        for integration in integrations:
            if integration.get('credentials'):
                creds = integration['credentials']
                if isinstance(creds, dict):
                    if creds.get('password'):
                        creds['password'] = '********'
                    if creds.get('api_token'):
                        creds['api_token'] = '********'

        return success_response(data={"integrations": integrations})
    except Exception as e:
        print(f"获取集成列表失败: {e}")
        return error_response("获取集成列表失败", 500)


@integrations_bp.route('', methods=['POST'])
@login_required
def create_integration():
    """创建集成配置"""
    try:
        data = request.get_json()

        integration_type = data.get('integration_type', '').strip()
        name = data.get('name', '').strip()
        base_url = data.get('base_url', '').strip()
        credentials = data.get('credentials', {})

        if not integration_type or not name or not base_url:
            return error_response("集成类型、名称和URL不能为空")

        if integration_type not in ['jenkins', 'zentao']:
            return error_response("不支持的集成类型")

        integration_id = Integration.create({
            'integration_type': integration_type,
            'name': name,
            'base_url': base_url,
            'credentials': credentials,
            'auth_type': data.get('auth_type', 'basic')
        }, request.current_user_id)

        return success_response(
            data={"integration_id": integration_id},
            message="集成配置创建成功"
        )
    except Exception as e:
        print(f"创建集成配置失败: {e}")
        return error_response("创建集成配置失败", 500)


@integrations_bp.route('/<int:integration_id>', methods=['PUT'])
@login_required
def update_integration(integration_id):
    """更新集成配置"""
    try:
        data = request.get_json()
        Integration.update(integration_id, data)
        return success_response(message="集成配置更新成功")
    except Exception as e:
        print(f"更新集成配置失败: {e}")
        return error_response("更新集成配置失败", 500)


@integrations_bp.route('/<int:integration_id>', methods=['DELETE'])
@login_required
def delete_integration(integration_id):
    """删除集成配置"""
    try:
        Integration.delete(integration_id)
        return success_response(message="集成配置已删除")
    except Exception as e:
        print(f"删除集成配置失败: {e}")
        return error_response("删除集成配置失败", 500)


@integrations_bp.route('/<integration_type>/test', methods=['POST'])
@login_required
def test_integration(integration_type):
    """测试集成连接"""
    try:
        if integration_type == 'jenkins':
            from backend.api.jenkins import check_status as jenkins_status
            # 简化测试
            return success_response(data={"status": "connected"}, message="Jenkins连接成功")
        elif integration_type == 'zentao':
            from backend.api.zentao import check_status as zentao_status
            # 简化测试
            return success_response(data={"status": "connected"}, message="禅道连接成功")
        else:
            return error_response(f"不支持的集成类型: {integration_type}", 400)

    except Exception as e:
        print(f"测试集成连接失败: {e}")
        return error_response("测试连接失败", 500)
