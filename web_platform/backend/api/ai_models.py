"""
AI模型配置API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.ai_model import AIModel
from backend.utils.decorators import login_required
from backend.utils.response import success_response, error_response
import requests
import json

ai_models_bp = Blueprint('ai_models', __name__)


# 各模型的默认API地址和模型ID
MODEL_CONFIGS = {
    'qwen': {
        'default_base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'default_model': 'qwen-turbo'
    },
    'deepseek': {
        'default_base_url': 'https://api.deepseek.com/v1',
        'default_model': 'deepseek-chat'
    },
    'zhipu': {
        'default_base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'default_model': 'glm-4-flash'
    },
    'doubao': {
        'default_base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'default_model': 'ep-20240805163033-r5m2d'
    },
    'openai': {
        'default_base_url': 'https://api.openai.com/v1',
        'default_model': 'gpt-3.5-turbo'
    }
}


@ai_models_bp.route('', methods=['GET'])
@login_required
def get_models():
    """获取AI模型列表"""
    try:
        models = AIModel.find_all()
        # 隐藏API Key
        for model in models:
            if model.get('api_key') and len(model['api_key']) > 8:
                model['api_key'] = model['api_key'][:4] + '****' + model['api_key'][-4:]
        return success_response(data={"models": models})
    except Exception as e:
        print(f"获取AI模型列表失败: {e}")
        return error_response("获取AI模型列表失败", 500)


@ai_models_bp.route('', methods=['POST'])
@login_required
def create_model():
    """创建AI模型配置"""
    try:
        data = request.get_json()

        if not data.get('model_type') or not data.get('model_name'):
            return error_response("模型类型和名称不能为空")

        model_id = AIModel.create(data, request.current_user_id)

        return success_response(
            data={"model_id": model_id},
            message="模型配置创建成功"
        )
    except Exception as e:
        print(f"创建AI模型失败: {e}")
        return error_response("创建AI模型失败", 500)


@ai_models_bp.route('/<int:model_id>', methods=['PUT'])
@login_required
def update_model(model_id):
    """更新AI模型配置"""
    try:
        data = request.get_json()
        AIModel.update(model_id, data)
        return success_response(message="模型配置更新成功")
    except Exception as e:
        print(f"更新AI模型失败: {e}")
        return error_response("更新AI模型失败", 500)


@ai_models_bp.route('/<int:model_id>', methods=['DELETE'])
@login_required
def delete_model(model_id):
    """删除AI模型配置"""
    try:
        AIModel.delete(model_id)
        return success_response(message="模型配置已删除")
    except Exception as e:
        print(f"删除AI模型失败: {e}")
        return error_response("删除AI模型失败", 500)


@ai_models_bp.route('/<int:model_id>/test', methods=['POST'])
@login_required
def test_model(model_id):
    """测试模型连接 - 参考CC Switch的多阶段测试方法"""
    try:
        model = AIModel.find_by_id(model_id)

        if not model:
            return error_response("模型不存在", 404)

        # 获取模型配置
        api_key = model.get('api_key', '')
        base_url = model.get('base_url', '')
        model_id_param = model.get('model_id', '')
        model_type = model.get('model_type', '')

        if not api_key:
            return error_response("API Key不能为空")

        # 使用默认配置
        config = MODEL_CONFIGS.get(model_type, {})
        if not base_url:
            base_url = config.get('default_base_url', '')
        if not model_id_param:
            model_id_param = config.get('default_model', '')

        if not base_url:
            return error_response("API地址不能为空")

        # 确保base_url末尾没有斜杠
        base_url = base_url.rstrip('/')
        
        # 智能处理test_url：
        # 如果用户输入的URL已经包含/chat/completions，直接使用
        # 否则自动追加/chat/completions
        if '/chat/completions' in base_url:
            test_url = base_url
        else:
            test_url = f"{base_url}/chat/completions"
        
        # 记录测试开始时间
        import time
        start_time = time.time()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # 使用最小化请求进行验证
        payload = {
            "model": model_id_param if model_id_param else config.get('default_model', 'qwen-turbo'),
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "stream": False
        }

        try:
            response = requests.post(
                test_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            elapsed_time = round((time.time() - start_time) * 1000)  # 毫秒

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    # 验证响应结构
                    if 'choices' not in response_data and 'error' not in response_data:
                        return error_response("连接失败: 响应格式异常")
                    
                    if 'error' in response_data:
                        error_msg = response_data['error'].get('message', '未知错误')
                        return error_response(f"连接失败: {error_msg}", 400)
                    
                    # 验证模型ID
                    actual_model = response_data.get('model', model_id_param)
                    
                    return success_response(
                        data={
                            "status": "success",
                            "message": "模型连接正常",
                            "model_id": actual_model,
                            "url": test_url,
                            "latency_ms": elapsed_time,
                            "test_phases": {
                                "connectivity": "passed",
                                "authentication": "passed",
                                "model_available": "passed"
                            }
                        },
                        message="模型连接测试成功"
                    )
                except json.JSONDecodeError:
                    return error_response("连接失败: 响应解析错误", 500)
            
            else:
                # 解析错误信息
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', error_msg)
                    elif 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    if response.text:
                        error_msg = response.text[:200]
                
                # 根据状态码提供具体建议
                # 注意：不使用401/403状态码返回，避免前端拦截为登录过期
                if response.status_code == 401 or response.status_code == 403:
                    return error_response(f"模型API认证失败: {error_msg}", 400)
                elif response.status_code == 429:
                    return error_response(f"请求过于频繁: {error_msg}", response.status_code)
                elif response.status_code == 404:
                    return error_response(f"模型或地址不存在: {error_msg}", response.status_code)
                else:
                    return error_response(
                        f"连接失败: {error_msg}",
                        response.status_code if response.status_code >= 400 else 500
                    )

        except requests.exceptions.Timeout:
            return error_response("连接超时，请检查网络或API地址", 504)
        except requests.exceptions.ConnectionError:
            return error_response("无法连接到API服务器，请检查API地址和网络连接", 502)
        except requests.exceptions.SSLError:
            return error_response("SSL证书验证失败，请检查API地址", 500)
        except Exception as e:
            return error_response(f"连接异常: {str(e)}", 500)

    except Exception as e:
        print(f"测试模型连接失败: {e}")
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
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model_id": "qwen-turbo",
                "description": "阿里云通义千问"
            },
            {
                "type": "deepseek",
                "name": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1",
                "model_id": "deepseek-chat",
                "description": "DeepSeek官方模型"
            },
            {
                "type": "zhipu",
                "name": "智谱AI",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "model_id": "glm-4-flash",
                "description": "智谱AI GLM-4"
            },
            {
                "type": "doubao",
                "name": "豆包",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model_id": "ep-20240805163033-r5m2d",
                "description": "字节跳动豆包"
            },
            {
                "type": "openai",
                "name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "model_id": "gpt-3.5-turbo",
                "description": "OpenAI GPT"
            }
        ]
        return success_response(data={"preset_models": preset_models})
    except Exception as e:
        print(f"获取预设模型失败: {e}")
        return error_response("获取预设模型失败", 500)
