"""
AI 大模型调用客户端
支持多模型自动调用和fallback机制
"""
import os
import requests
import json
from utils.tools.logger import log as logger
from utils.tools.config_reader import ConfigReader


class AIClient:
    """AI 大模型调用客户端"""

    def __init__(self, models=None, default_model=None):
        """
        初始化 AI 客户端
        
        Args:
            models: 模型配置列表，每个元素包含 type, api_key, base_url
            default_model: 默认模型类型
        """
        # 打印所有环境变量，检查是否能读取到 QWEN_API_KEY
        logger.info("所有环境变量:")
        for key, value in os.environ.items():
            if "API_KEY" in key:
                logger.info(f"{key}: {'已设置' if value else '未设置'}")
                if value:
                    logger.info(f"  前5位: {value[:5]}...")
        
        # 优先从配置文件读取模型配置
        if models is None:
            try:
                ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
                self.models = ai_config.get("ai_models", [
                    {"type": "mock", "api_key": None, "base_url": None},
                ])
                # 处理环境变量占位符
                for model in self.models:
                    if model.get("api_key") and model["api_key"].startswith("${") and model["api_key"].endswith("}"):
                        env_var = model["api_key"][2:-1]
                        # 直接从环境变量读取
                        model["api_key"] = os.environ.get(env_var)
                        # 添加日志，检查环境变量是否正确读取
                        logger.info(f"从环境变量 {env_var} 读取 API 密钥: {'已设置' if model['api_key'] else '未设置'}")
                        # 打印环境变量值（仅显示前5个字符，保护隐私）
                        if model['api_key']:
                            logger.info(f"API 密钥前5位: {model['api_key'][:5]}...")
                        else:
                            # 尝试直接打印环境变量值，看看是否能读取到
                            logger.info(f"尝试直接读取环境变量 {env_var}: {os.environ.get(env_var)}")
                    else:
                        # 如果 API 密钥不是环境变量占位符，直接使用
                        if model.get("api_key"):
                            logger.info(f"直接使用配置文件中的 API 密钥: {model['api_key'][:5]}...")
                
                # 确保 Qwen 模型使用正确的 API 端点和模型 ID
                for model in self.models:
                    if model["type"] == "qwen":
                        # 只有在 base_url 未设置时才使用默认值
                        if not model.get("base_url"):
                            model["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                        # 只有在 model_id 未设置时才使用默认值
                        if not model.get("model_id"):
                            model["model_id"] = "qwen-turbo"  # 标准 Qwen 模型 ID，轻量级模型
                        logger.info(f"Qwen 模型配置: API 端点={model['base_url']}, 模型 ID={model['model_id']}")
            except Exception as e:
                logger.error(f"读取AI配置失败: {e}")
                self.models = [
                    {"type": "mock", "api_key": None, "base_url": None},
                ]
        else:
            self.models = models
        
        # 从配置文件读取默认模型
        if default_model is None:
            try:
                ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
                # 使用第一个模型作为默认模型
                if self.models:
                    default_model = self.models[0]["type"]
                else:
                    default_model = "mock"
            except Exception:
                default_model = "mock"
        
        self.default_model = default_model
        
        logger.info(f"初始化AI客户端，默认模型: {default_model}")
        logger.info(f"配置的模型: {[model['type'] for model in self.models]}")

    def generate(self, prompt, system_prompt=None, max_tokens=2000, temperature=0.7):
        """
        调用AI模型生成内容，支持自动fallback

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_tokens: 最大生成 token 数
            temperature: 生成温度

        Returns:
            str: AI生成的内容
        """
        # 遍历模型列表，尝试调用，失败则fallback
        for model in self.models:
            model_type = model["type"]
            # 每次调用都重新读取环境变量，确保使用最新的密钥
            if model.get("api_key") and model["api_key"].startswith("${") and model["api_key"].endswith("}"):
                env_var = model["api_key"][2:-1]
                api_key = os.environ.get(env_var)
                logger.info(f"从环境变量 {env_var} 读取 API 密钥: {'已设置' if api_key else '未设置'}")
            else:
                api_key = model["api_key"] or os.environ.get(f"{model_type.upper()}_API_KEY")
            base_url = model["base_url"]

            try:
                logger.info(f"尝试调用模型: {model_type}")
                logger.info(f"API 密钥: {'已设置' if api_key else '未设置'}")
                logger.info(f"API URL: {base_url}")
                # 打印环境变量值（仅显示前5个字符，保护隐私）
                if api_key:
                    logger.info(f"API 密钥前5位: {api_key[:5]}...")
                
                if model_type == "mock":
                    return self._mock_response(prompt, system_prompt)
                elif model_type == "doubao":
                    return self._call_doubao(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                elif model_type == "openai":
                    return self._call_openai(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                elif model_type == "claude":
                    return self._call_claude(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                elif model_type == "deepseek":
                    return self._call_deepseek(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                elif model_type == "qwen":
                    return self._call_qwen(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                elif model_type == "yuanbao":
                    return self._call_yuanbao(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                elif model_type == "zhiPu":
                    return self._call_zhiPu(prompt, system_prompt, max_tokens, temperature, api_key, base_url)
                else:
                    logger.warning(f"不支持的模型类型: {model_type}")
                    continue
            except Exception as e:
                logger.error(f"调用模型 {model_type} 失败: {e}")
                continue

        # 所有模型都失败时，返回模拟响应
        logger.warning("所有模型调用失败，返回模拟响应")
        return self._mock_response(prompt, system_prompt)

    def _mock_response(self, prompt, system_prompt):
        """模拟AI响应，用于本地演示"""
        logger.info("使用模拟AI响应")

        # 模拟分析页面并生成测试步骤
        if "分析页面" in prompt or "页面信息" in prompt:
            return json.dumps({
                "page_analysis": {
                    "title": "登录页面",
                    "url": "https://example.com/login",
                    "elements": [
                        {"type": "input", "name": "username", "label": "用户名"},
                        {"type": "input", "name": "password", "label": "密码"},
                        {"type": "button", "name": "login", "label": "登录按钮"}
                    ],
                    "business": "用户登录功能"
                },
                "test_steps": [
                    {"action": "input", "element": "username", "value": "test_user"},
                    {"action": "input", "element": "password", "value": "password123"},
                    {"action": "click", "element": "login"},
                    {"action": "assert", "condition": "页面跳转至首页"}
                ]
            }, ensure_ascii=False)

        # 模拟执行结果分析
        if "执行结果" in prompt or "测试结果" in prompt:
            return json.dumps({
                "result_analysis": {
                    "status": "success",
                    "message": "测试通过，登录成功并跳转到首页",
                    "details": {
                        "steps_executed": 4,
                        "errors": 0,
                        "assertions_passed": 1
                    }
                }
            }, ensure_ascii=False)

        return "这是一个模拟的AI响应，用于本地演示。"

    def _call_doubao(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用豆包API"""
        logger.info("调用豆包API")
        try:
            # 检查 API 密钥是否存在
            if not api_key:
                logger.error("豆包 API 密钥不存在")
                raise ValueError("API 密钥未设置")
            
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            # 从配置文件读取模型配置
            for model in ai_config.get("ai_models", []):
                if model["type"] == "doubao":
                    url = base_url or model.get("base_url", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
                    model_id = model.get("model_id", "ep-20240417172235-49v4x")
                    break
            else:
                url = base_url or "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
                model_id = "ep-20240417172235-49v4x"
        except Exception as e:
            logger.error(f"读取豆包模型配置失败: {e}")
            url = base_url or "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
            model_id = "ep-20240417172235-49v4x"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            timeout = ai_config.get("ai_test_params", {}).get("timeout", 30)
        except Exception:
            timeout = 30
        
        try:
            logger.info(f"发送请求到豆包 API: {url}")
            logger.info(f"使用模型: {model_id}")
            # 禁用 SSL 证书验证，解决证书验证失败问题
            response = requests.post(url, headers=headers, json=data, timeout=timeout, verify=False)
            response.raise_for_status()  # 检查 HTTP 状态码
            result = response.json()
            logger.info(f"豆包 API 响应成功")
            logger.info(f"响应内容: {result}")  # 打印完整响应
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            logger.error(f"豆包 API 请求失败: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
            raise
        except KeyError as e:
            logger.error(f"豆包 API 响应格式错误: {e}")
            logger.error(f"响应内容: {result}")
            raise

    def _call_openai(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用OpenAI API"""
        logger.info("调用OpenAI API")
        url = base_url or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _call_claude(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用Claude API"""
        logger.info("调用Claude API")
        url = base_url or "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": "claude-3-opus-20240229",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        return result["content"][0]["text"]

    def _call_deepseek(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用DeepSeek API"""
        logger.info("调用DeepSeek API")
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            # 从配置文件读取模型配置
            for model in ai_config.get("ai_models", []):
                if model["type"] == "deepseek":
                    url = base_url or model.get("base_url", "https://api.deepseek.com/v1/chat/completions")
                    model_id = model.get("model_id", "deepseek-chat")
                    break
            else:
                url = base_url or "https://api.deepseek.com/v1/chat/completions"
                model_id = "deepseek-chat"
        except Exception:
            url = base_url or "https://api.deepseek.com/v1/chat/completions"
            model_id = "deepseek-chat"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            timeout = ai_config.get("ai_test_params", {}).get("timeout", 30)
        except Exception:
            timeout = 30
        
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _call_qwen(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用Qwen API"""
        logger.info("调用Qwen API")
        config_api_key = None
        
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            # 从配置文件读取模型配置
            for model in ai_config.get("ai_models", []):
                if model["type"] == "qwen":
                    url = base_url or model.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
                    model_id = model.get("model_id", "qwen-turbo")
                    # 处理 API 密钥
                    if model.get("api_key"):
                        # 处理环境变量占位符
                        if model["api_key"].startswith("${") and model["api_key"].endswith("}"):
                            env_var = model["api_key"][2:-1]
                            # 直接从环境变量读取，不使用缓存
                            config_api_key = os.environ.get(env_var)
                            logger.info(f"从环境变量 {env_var} 读取 API 密钥: {'已设置' if config_api_key else '未设置'}")
                            # 打印环境变量值（仅显示前5个字符，保护隐私）
                            if config_api_key:
                                logger.info(f"API 密钥前5位: {config_api_key[:5]}...")
                        else:
                            config_api_key = model["api_key"]
                            logger.info("使用配置文件中的 API 密钥")
                    break
            else:
                url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                model_id = "qwen-turbo"
        except Exception as e:
            logger.error(f"读取 Qwen 模型配置失败: {e}")
            url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            model_id = "qwen-turbo"
        
        # 如果配置文件中没有 API 密钥，使用传入的 API 密钥
        if not config_api_key:
            config_api_key = api_key
            logger.info("使用传入的 API 密钥")
        
        # 检查 API 密钥是否存在
        if not config_api_key:
            logger.error("Qwen API 密钥不存在")
            raise ValueError("API 密钥未设置")
        
        # 移除 URL 中的反引号
        if url and ('`' in url):
            url = url.replace('`', '')
            logger.info(f"修正 URL: {url}")
        
        headers = {
            "Authorization": f"Bearer {config_api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"请求头: {headers}")
        data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            timeout = ai_config.get("ai_test_params", {}).get("timeout", 30)
        except Exception:
            timeout = 30
        
        try:
            logger.info(f"发送请求到 Qwen API: {url}")
            logger.info(f"使用模型: {model_id}")
            logger.info(f"请求头: {headers}")
            logger.info(f"请求数据: {data}")
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.text}")
            response.raise_for_status()  # 检查 HTTP 状态码
            result = response.json()
            logger.info(f"Qwen API 响应成功")
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Qwen API 请求失败: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
            raise
        except KeyError as e:
            logger.error(f"Qwen API 响应格式错误: {e}")
            if 'result' in locals():
                logger.error(f"响应内容: {result}")
            raise

    def _call_yuanbao(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用元宝API（智谱AI）"""
        logger.info("调用元宝API")
        url = base_url or "https://chatglm.cn/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "yuanbao-1.0",  # 替换为实际的元宝模型ID
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _call_zhiPu(self, prompt, system_prompt, max_tokens, temperature, api_key, base_url):
        """调用智谱AI API"""
        logger.info("调用智谱AI API")
        url = base_url or "https://open.bigmodel.cn/api/mt/text2text"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "glm-4",  # 替换为实际的智谱模型ID
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        return result["data"]["text"]