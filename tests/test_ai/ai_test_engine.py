"""
AI 自主测试核心引擎
功能：分析页面 → 生成步骤 → 执行 → 断言
"""
import json
from utils.tools.logger import log as logger
from utils.tools.ai_client import AIClient
from utils.tools.config_reader import ConfigReader
from utils.tools.path_manager import get_test_data_path


class AITestEngine:
    """AI 自主测试核心引擎"""
    
    def __init__(self, models=None, default_model=None):
        """
        初始化 AI 测试引擎
        
        Args:
            models: 模型配置列表，每个元素包含 type, api_key, base_url
            default_model: 默认模型类型
        """
        self.ai_client = AIClient(models=models, default_model=default_model)
        self.system_prompt = self._load_system_prompt()
        self.test_params = self._load_test_params()
        
        logger.info("初始化AI测试引擎")
    
    def _load_system_prompt(self):
        """
        加载系统提示词

        Returns:
            str: 系统提示词
        """
        try:
            # 使用路径管理工具获取提示词文件路径
            prompt_path = get_test_data_path("ai", "prompt.yaml")
            prompt_config = ConfigReader.read_yaml(prompt_path)
            return prompt_config.get("system_prompt", "")
        except Exception as e:
            logger.error(f"加载系统提示词失败: {e}")
            return ""
    
    def _load_test_params(self):
        """
        加载测试参数
        
        Returns:
            dict: 测试参数
        """
        try:
            ai_config = ConfigReader.read_yaml("config/ai_config.yaml")
            return ai_config.get("ai_test_params", {
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 30,
                "retry_count": 3
            })
        except Exception as e:
            logger.error(f"加载测试参数失败: {e}")
            return {
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 30,
                "retry_count": 3
            }
    
    def analyze_page(self, page):
        """
        分析页面信息
        
        Args:
            page: 页面对象
            
        Returns:
            dict: 页面分析结果
        """
        logger.info("开始分析页面")
        
        # 获取页面信息
        page_info = {
            "title": page.get_title(),
            "url": page.get_url(),
            "text": page.get_page_source()[:1000]  # 只取前1000个字符，避免token超限
        }
        
        # 构建提示词
        prompt = "请分析以下页面信息，并生成完整的登录测试步骤：\n"
        prompt += f"页面标题: {page_info['title']}\n"
        prompt += f"页面URL: {page_info['url']}\n"
        prompt += f"页面内容: {page_info['text']}\n\n"
        prompt += "请输出JSON格式的分析结果，包含：\n"
        prompt += "1. page_analysis: 页面分析（标题、URL、元素、业务逻辑）\n"
        prompt += "2. test_steps: 测试步骤（操作类型、元素、值），必须包含：\n"
        prompt += "   - 输入用户名（元素标识符：username）\n"
        prompt += "   - 输入密码（元素标识符：password）\n"
        prompt += "   - 点击登录按钮（元素标识符：登录）\n"
        prompt += "   - 验证登录结果（元素标识符：msg）\n\n"
        prompt += "每个测试步骤应包含：\n"
        prompt += "- action: 操作类型（input/click/assert）\n"
        prompt += "- element: 元素标识符（ID、name或文本内容）\n"
        prompt += "- value: 操作值（仅input操作需要）\n\n"
        prompt += "示例输出：\n"
        prompt += "{\n"
        prompt += "  \"page_analysis\": {\n"
        prompt += "    \"title\": \"本地测试\",\n"
        prompt += "    \"url\": \"http://127.0.0.1:8090\",\n"
        prompt += "    \"elements\": [\n"
        prompt += "      {\"type\": \"input\", \"id\": \"username\", \"name\": null},\n"
        prompt += "      {\"type\": \"input\", \"id\": \"password\", \"name\": null},\n"
        prompt += "      {\"type\": \"button\", \"text\": \"登录\"},\n"
        prompt += "      {\"type\": \"p\", \"id\": \"msg\", \"name\": null}\n"
        prompt += "    ],\n"
        prompt += "    \"business\": \"登录功能\"\n"
        prompt += "  },\n"
        prompt += "  \"test_steps\": [\n"
        prompt += "    {\"action\": \"input\", \"element\": \"username\", \"value\": \"test\"},\n"
        prompt += "    {\"action\": \"input\", \"element\": \"password\", \"value\": \"test\"},\n"
        prompt += "    {\"action\": \"click\", \"element\": \"登录\", \"value\": null},\n"
        prompt += "    {\"action\": \"assert\", \"element\": \"msg\", \"value\": \"登录成功\"}\n"
        prompt += "  ]\n"
        prompt += "}\n"
        
        # 调用AI分析
        response = self.ai_client.generate(
            prompt, 
            self.system_prompt,
            max_tokens=self.test_params.get("max_tokens", 2000),
            temperature=self.test_params.get("temperature", 0.7)
        )
        
        # 清理响应内容，去除markdown代码块标记
        cleaned_response = self._clean_response(response)
        
        try:
            result = json.loads(cleaned_response)
            logger.info(f"页面分析完成: {result.get('page_analysis', {}).get('business', '未知业务')}")
            return result
        except json.JSONDecodeError:
            logger.error(f"AI响应格式错误: {response}")
            return {"page_analysis": {}, "test_steps": []}
    
    def _clean_response(self, response):
        """
        清理AI响应内容，去除markdown代码块标记
        
        Args:
            response: AI返回的原始响应
            
        Returns:
            str: 清理后的响应内容
        """
        if not response:
            return response
        
        # 去除markdown代码块标记
        cleaned = response.strip()
        
        # 去除 ```json 和 ```
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        # 去除其他可能的markdown标记
        cleaned = cleaned.strip()
        
        return cleaned
    
    def execute_test(self, page, test_steps):
        """
        执行测试步骤
        
        Args:
            page: 页面对象
            test_steps: 测试步骤列表
            
        Returns:
            dict: 执行结果
        """
        logger.info(f"开始执行测试步骤，共 {len(test_steps)} 步")
        
        executed_steps = []
        errors = []
        
        for i, step in enumerate(test_steps, 1):
            logger.info(f"执行步骤 {i}: {step}")
            
            try:
                action = step.get("action")
                element = step.get("element")
                value = step.get("value")
                
                if action == "input":
                    page.input(element, value)
                elif action == "click":
                    page.click(element)
                elif action == "assert":
                    # 这里简化处理，实际应根据断言条件执行相应操作
                    pass
                
                executed_steps.append(step)
            except Exception as e:
                error_msg = f"执行步骤 {i} 失败: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # 构建执行结果
        result = {
            "steps_executed": len(executed_steps),
            "errors": len(errors),
            "error_details": errors,
            "final_url": page.get_url(),
            "final_title": page.get_title()
        }
        
        logger.info(f"测试执行完成，执行 {len(executed_steps)} 步，错误 {len(errors)} 个")
        return result
    
    def analyze_result(self, execution_result):
        """
        分析执行结果

        Args:
            execution_result: 执行结果

        Returns:
            dict: 结果分析
        """
        logger.info("分析测试执行结果")

        # 构建提示词
        prompt = f"""请分析以下测试执行结果，并判断测试是否通过：
{json.dumps(execution_result, ensure_ascii=False, indent=2)}

请输出JSON格式的分析结果，包含：
1. status: 测试状态（success/failure）
2. message: 测试结果描述
3. details: 详细信息
"""

        # 调用AI分析
        response = self.ai_client.generate(
            prompt, 
            self.system_prompt,
            max_tokens=self.test_params.get("max_tokens", 2000),
            temperature=self.test_params.get("temperature", 0.7)
        )

        try:
            result = json.loads(response)
            # 确保结果包含 status 字段
            if 'status' not in result:
                logger.error(f"AI响应缺少 status 字段: {result}")
                return {"status": "failure", "message": "结果分析失败: 缺少状态字段", "details": {}}
            logger.info(f"测试结果分析: {result.get('status', 'unknown')}")
            return result
        except json.JSONDecodeError:
            logger.error(f"AI响应格式错误: {response}")
            return {"status": "failure", "message": "结果分析失败", "details": {}}
        except Exception as e:
            logger.error(f"分析结果失败: {e}")
            return {"status": "failure", "message": f"结果分析失败: {str(e)}", "details": {}}
    
    def run_autonomous_test(self, page):
        """
        运行自主测试
        
        Args:
            page: 页面对象
            
        Returns:
            dict: 完整测试结果
        """
        logger.info("开始运行AI自主测试")
        
        # 1. 分析页面
        analysis_result = self.analyze_page(page)
        
        # 2. 执行测试
        test_steps = analysis_result.get("test_steps", [])
        execution_result = self.execute_test(page, test_steps)
        
        # 3. 分析结果
        final_result = self.analyze_result(execution_result)
        
        # 4. 构建完整结果
        full_result = {
            "page_analysis": analysis_result.get("page_analysis", {}),
            "test_steps": test_steps,
            "execution_result": execution_result,
            "final_result": final_result
        }
        
        logger.info(f"AI自主测试完成，结果: {final_result.get('status', 'unknown')}")
        return full_result