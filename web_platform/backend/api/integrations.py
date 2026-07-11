"""
集成配置API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.integration import Integration
from backend.utils.decorators import login_required
from backend.utils.response import success_response, error_response

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('', methods=['GET'])
@login_required
def get_integrations():
    """获取集成列表"""
    try:
        integration_type = request.args.get('type')
        integrations = Integration.find_all(integration_type)

        # 隐藏敏感信息
        for integration in integrations:
            if integration.get('password'):
                integration['password'] = '********'
            if integration.get('api_token'):
                integration['api_token'] = '********'

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


@integrations_bp.route('/test/<int:integration_id>', methods=['POST'])
@login_required
def test_integration_by_id(integration_id):
    """测试特定集成配置的连接"""
    import sys
    print(f"\n>>> [集成测试] 测试配置ID={integration_id}", flush=True)
    sys.stdout.flush()
    try:
        config = Integration.find_by_id(integration_id)
        if not config:
            return error_response("配置不存在", 404)

        integration_type = config.get('integration_type')

        if integration_type == 'jenkins':
            from backend.api.jenkins import check_status_for_config
            result = check_status_for_config(config)
            data = result.get_json()
            if data.get('code') == 200 and data.get('data', {}).get('connected'):
                return success_response(data=data.get('data'), message="测试成功")
            return result
        elif integration_type == 'zentao':
            from backend.api.zentao import check_status_for_config
            result = check_status_for_config(config)
            data = result.get_json()
            if data.get('code') == 200 and data.get('data', {}).get('connected'):
                return success_response(data=data.get('data'), message="测试成功")
            return result
        else:
            return error_response(f"不支持的集成类型: {integration_type}", 400)
    except Exception as e:
        print(f">>> [集成测试] 异常: {e}", flush=True)
        return error_response("测试连接失败", 500)


@integrations_bp.route('/<int:integration_id>/default', methods=['POST'])
@login_required
def set_default_integration(integration_id):
    """设置指定配置为默认配置"""
    try:
        config = Integration.find_by_id(integration_id)
        if not config:
            return error_response("配置不存在", 404)

        integration_type = config.get('integration_type')
        Integration.set_default(integration_id, integration_type)

        return success_response(message="已设为默认配置")
    except Exception as e:
        print(f"设置默认配置失败: {e}")
        return error_response("设置默认配置失败", 500)


@integrations_bp.route('/<integration_type>/test', methods=['POST'])
@login_required
def test_integration(integration_type):
    """测试集成连接（按类型，测试默认配置）"""
    import sys
    print(f"\n>>> [集成测试] 收到测试请求: type={integration_type}", flush=True)
    sys.stdout.flush()
    try:
        # 优先测试默认配置
        config = Integration.find_default_by_type(integration_type)
        if not config:
            # 没有默认配置，则测试第一条可用配置
            config = Integration.find_by_type_with_credentials(integration_type)

        if not config:
            return error_response(f"未找到{integration_type}的配置", 404)

        if integration_type == 'jenkins':
            from backend.api.jenkins import check_status_for_config
            print(f">>> [集成测试] 正在测试 Jenkins 配置ID={config.get('id')}...", flush=True)
            result = check_status_for_config(config)
            data = result.get_json()
            if data.get('code') == 200 and data.get('data', {}).get('connected'):
                return success_response(data=data.get('data'), message="测试成功")
            return result
        elif integration_type == 'zentao':
            from backend.api.zentao import check_status_for_config
            print(f">>> [集成测试] 正在测试 禅道 配置ID={config.get('id')}...", flush=True)
            result = check_status_for_config(config)
            data = result.get_json()
            if data.get('code') == 200 and data.get('data', {}).get('connected'):
                return success_response(data=data.get('data'), message="测试成功")
            return result
        else:
            return error_response(f"不支持的集成类型: {integration_type}", 400)

    except Exception as e:
        print(f">>> [集成测试] 异常: {e}", flush=True)
        return error_response("测试连接失败", 500)
