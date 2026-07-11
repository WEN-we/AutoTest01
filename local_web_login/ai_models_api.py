"""
AI模型配置API
适配web_platform数据库表结构
"""
from flask import Blueprint, request, jsonify
from local_web_login.backend_server import (
    login_required, success_response, error_response,
    Database
)
import requests
import json
from utils.tools.logger import log as logger

ai_models_bp = Blueprint('ai_models', __name__, url_prefix='/api/ai-models')


def _format_model(model):
    """格式化模型数据，适配前端"""
    if not model:
        return model
    if model.get('config') and isinstance(model['config'], str):
        try:
            model['config'] = json.loads(model['config'])
        except Exception:
            pass
    if model.get('api_key') and len(model.get('api_key', '')) > 10:
        model['api_key'] = model['api_key'][:4] + '****' + model['api_key'][-4:]
    model['model_name'] = model.get('name', '')
    model['base_url'] = model.get('api_endpoint', '')
    model['is_active'] = model.get('status') == 'active'
    return model


@ai_models_bp.route('', methods=['GET'])
@login_required
def get_ai_models():
    """获取AI模型列表"""
    try:
        sql = """
            SELECT * FROM ai_model_config
            WHERE status = 'active'
            ORDER BY priority DESC, id ASC
        """
        models = Database.execute_query(sql)
        for model in models:
            _format_model(model)
        return jsonify(success_response(data={"models": models}))
    except Exception as e:
        logger.error(f"获取AI模型列表失败: {e}")
        return error_response("获取AI模型列表失败", 500)


@ai_models_bp.route('/<int:model_id>', methods=['GET'])
@login_required
def get_model_detail(model_id):
    """获取模型详情"""
    try:
        sql = "SELECT * FROM ai_model_config WHERE id = %s"
        model = Database.execute_query(sql, (model_id,), fetch_one=True)
        if not model:
            return error_response("模型不存在", 404)
        _format_model(model)
        return jsonify(success_response(data=model))
    except Exception as e:
        logger.error(f"获取模型详情失败: {e}")
        return error_response("获取模型详情失败", 500)


@ai_models_bp.route('', methods=['POST'])
@login_required
def create_model():
    """创建AI模型配置"""
    try:
        data = request.get_json()

        model_type = data.get('model_type', '').strip()
        model_name = data.get('model_name', '').strip() or data.get('name', '').strip()
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '') or data.get('api_endpoint', '')
        model_id_str = data.get('model_id', '')
        priority = data.get('priority', 0)
        config = data.get('config', {})
        provider = data.get('provider', model_type)

        if not model_type or not model_name:
            return error_response("模型类型和名称不能为空")

        if isinstance(config, dict):
            config = json.dumps(config)

        sql = """
            INSERT INTO ai_model_config
            (name, provider, model_type, api_endpoint, model_id, api_key, priority, config, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', %s)
        """

        Database.execute_update(
            sql,
            (model_name, provider, model_type, base_url, model_id_str, api_key, priority, config, request.current_user['id'])
        )

        result = Database.execute_query("SELECT LAST_INSERT_ID() as id", fetch_one=True)

        logger.info(f"创建AI模型配置成功: {model_name}")

        return jsonify(success_response(
            data={"model_id": result['id']},
            message="模型配置创建成功"
        ))
    except Exception as e:
        logger.error(f"创建AI模型失败: {e}")
        return error_response("创建AI模型失败", 500)


@ai_models_bp.route('/<int:model_id>', methods=['PUT'])
@login_required
def update_model(model_id):
    """更新AI模型配置"""
    try:
        data = request.get_json()

        updates = []
        params = []

        if 'model_name' in data or 'name' in data:
            updates.append("name = %s")
            params.append(data.get('name') or data.get('model_name'))

        if 'api_key' in data:
            updates.append("api_key = %s")
            params.append(data['api_key'])

        if 'base_url' in data or 'api_endpoint' in data:
            updates.append("api_endpoint = %s")
            params.append(data.get('api_endpoint') or data.get('base_url'))

        if 'model_id' in data:
            updates.append("model_id = %s")
            params.append(data['model_id'])

        if 'priority' in data:
            updates.append("priority = %s")
            params.append(data['priority'])

        if 'is_active' in data:
            updates.append("status = %s")
            params.append('active' if data['is_active'] else 'inactive')

        if 'config' in data:
            updates.append("config = %s")
            params.append(json.dumps(data['config']))

        if not updates:
            return error_response("没有需要更新的字段")

        updates.append("updated_at = NOW()")
        sql = "UPDATE ai_model_config SET " + ", ".join(updates) + " WHERE id = %s"
        params.append(model_id)

        Database.execute_update(sql, tuple(params))

        logger.info(f"更新AI模型配置成功: {model_id}")

        return jsonify(success_response(message="模型配置更新成功"))
    except Exception as e:
        logger.error(f"更新AI模型失败: {e}")
        return error_response("更新AI模型失败", 500)


@ai_models_bp.route('/<int:model_id>', methods=['DELETE'])
@login_required
def delete_model(model_id):
    """删除AI模型配置"""
    try:
        sql = "UPDATE ai_model_config SET status = 'inactive' WHERE id = %s"
        affected = Database.execute_update(sql, (model_id,))

        if affected == 0:
            return error_response("模型不存在", 404)

        logger.info(f"删除AI模型配置: {model_id}")

        return jsonify(success_response(message="模型配置已删除"))
    except Exception as e:
        logger.error(f"删除AI模型失败: {e}")
        return error_response("删除AI模型失败", 500)


@ai_models_bp.route('/<int:model_id>/test', methods=['POST'])
@login_required
def test_model_connection(model_id):
    """测试模型连接"""
    try:
        sql = "SELECT * FROM ai_model_config WHERE id = %s AND status = 'active'"
        model = Database.execute_query(sql, (model_id,), fetch_one=True)

        if not model:
            return error_response("模型不存在或已禁用", 404)

        api_key = model['api_key']
        base_url = model['api_endpoint']
        model_id_str = model['model_id']
        model_type = model.get('provider', model.get('model_type', ''))

        test_prompt = "你好，这是一个测试消息。请回复'测试成功'。"

        if model_type in ('qwen', 'doubao', 'deepseek', 'zhipu', 'openai'):
            if model_type == 'qwen':
                url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            elif model_type == 'zhipu':
                url = base_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            elif model_type == 'doubao':
                url = base_url or "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
            elif model_type == 'deepseek':
                url = base_url or "https://api.deepseek.com/v1/chat/completions"
            elif model_type == 'openai':
                url = f"{base_url.rstrip('/')}/chat/completions" if base_url else "https://api.openai.com/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model_id_str,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 100,
                "temperature": 0.7
            }
        else:
            return error_response(f"不支持的模型类型: {model_type}")

        logger.info(f"测试模型连接: {model_type}, URL: {url}")

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            usage = result.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)

            return jsonify(success_response(
                data={
                    "status": "success",
                    "tokens_used": total_tokens,
                    "response_time": response.elapsed.total_seconds()
                },
                message="模型连接测试成功"
            ))
        else:
            logger.error(f"模型API返回错误: {response.status_code} - {response.text}")
            return error_response(f"模型API返回错误: {response.status_code}", 400)

    except requests.exceptions.Timeout:
        logger.error("模型连接超时")
        return error_response("模型连接超时", 408)
    except requests.exceptions.RequestException as e:
        logger.error(f"模型连接失败: {e}")
        return error_response(f"模型连接失败: {str(e)}", 500)
    except Exception as e:
        logger.error(f"测试模型连接失败: {e}")
        return error_response("测试连接失败", 500)


@ai_models_bp.route('/preset', methods=['GET'])
@login_required
def get_preset_models():
    """获取预设模型列表"""
    try:
        preset_models = [
            {
                "type": "qwen",
                "name": "通义千问",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "model_id": "qwen-turbo",
                "description": "阿里云通义千问模型"
            },
            {
                "type": "qwen",
                "name": "通义千问-DeepSeek",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "model_id": "deepseek-v3",
                "description": "阿里云DeepSeek模型"
            },
            {
                "type": "zhipu",
                "name": "智谱AI",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model_id": "glm-4-flash",
                "description": "智谱AI GLM-4模型"
            },
            {
                "type": "doubao",
                "name": "豆包",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                "model_id": "doubao-seed-2-0-mini-260428",
                "description": "字节跳动豆包模型"
            },
            {
                "type": "deepseek",
                "name": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1/chat/completions",
                "model_id": "deepseek-chat",
                "description": "DeepSeek官方模型"
            },
            {
                "type": "openai",
                "name": "OpenAI GPT",
                "base_url": "https://api.openai.com/v1",
                "model_id": "gpt-3.5-turbo",
                "description": "OpenAI GPT-3.5模型"
            }
        ]

        return jsonify(success_response(data={"preset_models": preset_models}))
    except Exception as e:
        logger.error(f"获取预设模型失败: {e}")
        return error_response("获取预设模型失败", 500)
