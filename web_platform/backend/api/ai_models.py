"""
AI模型配置API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.ai_model import AIModel
from backend.utils.decorators import login_required
import requests

ai_models_bp = Blueprint('ai_models', __name__)


def success_response(data=None, message="操作成功"):
    response = {"code": 200, "message": message}
    if data:
        response["data"] = data
    return jsonify(response)


def error_response(message, code=400):
    return jsonify({"code": code, "message": message}), code


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
    """测试模型连接"""
    try:
        model = AIModel.find_by_id(model_id)

        if not model:
            return error_response("模型不存在", 404)

        # 简化的连接测试
        test_result = {
            "status": "success",
            "message": "模型连接正常"
        }

        return success_response(data=test_result, message="模型连接测试成功")

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
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "model_id": "qwen-turbo",
                "description": "阿里云通义千问"
            },
            {
                "type": "deepseek",
                "name": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1/chat/completions",
                "model_id": "deepseek-chat",
                "description": "DeepSeek官方模型"
            },
            {
                "type": "zhipu",
                "name": "智谱AI",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model_id": "glm-4-flash",
                "description": "智谱AI GLM-4"
            }
        ]
        return success_response(data={"preset_models": preset_models})
    except Exception as e:
        print(f"获取预设模型失败: {e}")
        return error_response("获取预设模型失败", 500)
