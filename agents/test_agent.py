"""
TestAgent - 企业级测试专用智能体
遵循企业级标准架构：
- 完整的工具注册表
- 感知-思考-行动-反思生命周期
- 记忆管理
- 错误处理和重试
- 测试报告生成
- Skill角色系统集成
"""
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from agents.base_agent import BaseAgent, TaskPlan, ToolCall
from agents.skill_manager import SkillManager, skill_manager as global_skill_manager
from utils.tools.logger import log as logger
from utils.tools.ai_client import AIClient
from utils.tools.config_reader import ConfigReader


class DictPageAdapter:
    """字典到页面对象的适配器 - 用于API调用时传递字典参数"""
    
    def __init__(self, data: Dict):
        self._data = data or {}
    
    def get_title(self) -> str:
        return self._data.get('title', '未知页面')
    
    def get_url(self) -> str:
        return self._data.get('url', '')
    
    def get_text(self, selector: str = '') -> str:
        return self._data.get('text', '')
    
    def click(self, selector: str):
        logger.info(f"[模拟] 点击元素: {selector}")
    
    def input(self, selector: str, value: str):
        logger.info(f"[模拟] 在 {selector} 输入: {value}")
    
    def select(self, selector: str, value: str):
        logger.info(f"[模拟] 在 {selector} 选择: {value}")
    
    def hover(self, selector: str):
        logger.info(f"[模拟] 悬停元素: {selector}")
    
    def scroll_to_element(self, selector: str):
        logger.info(f"[模拟] 滚动到元素: {selector}")
    
    def screenshot(self, name: str = None) -> str:
        path = f"/mock/screenshots/{name or 'screenshot'}.png"
        logger.info(f"[模拟] 截图保存至: {path}")
        return path


class TestAgent(BaseAgent):
    """企业级测试专用智能体 - 支持Skill角色系统"""

    def __init__(self, ai_client: Optional[AIClient] = None, system_prompt: str = "", config_path: str = "config/ai_config.yaml", initial_skill: str = "test_expert"):
        # 初始化Skill管理器
        self.skill_manager = SkillManager()

        # 尝试激活初始Skill
        if initial_skill and self.skill_manager.activate_skill(initial_skill):
            current_skill = self.skill_manager.get_current_skill_info()
            if current_skill and current_skill.get("system_prompt"):
                default_prompt = current_skill["system_prompt"]
                logger.info(f"使用Skill系统提示词: {current_skill['name']}")
            else:
                default_prompt = self._get_default_prompt()
        else:
            default_prompt = self._get_default_prompt()

        super().__init__(
            name="TestAgent",
            ai_client=ai_client,
            system_prompt=system_prompt or default_prompt,
            max_memory=50
        )
        self.config = self._load_config(config_path)
        self._register_test_tools()
        self.test_results: List[Dict] = []
        self.start_time: Optional[float] = None
        logger.info(f"初始化TestAgent完成，名称: {self.name}")

    def _get_default_prompt(self) -> str:
        """获取默认系统提示词"""
        return """你是一位专业的企业级自动化测试专家，具备以下核心能力：
1. 测试分析：深度理解需求，精准识别测试点和风险
2. 测试设计：生成覆盖全面的测试用例，包括正常/异常/边界场景
3. 测试执行：调用工具执行测试步骤，具备错误处理和重试
4. 结果断言：智能验证实际结果与预期
5. 缺陷分析：精准定位问题根因，提供专业修复建议
6. 报告生成：生成结构化测试报告

请始终保持专业、严谨、细致的工作态度。"""

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            config = ConfigReader.read_yaml(config_path)
            return config.get("test_agent", {})
        except Exception as e:
            logger.warning(f"加载配置失败: {e}，使用默认配置")
            return {
                "max_retry": 3,
                "timeout": 30,
                "take_screenshot": True,
                "generate_report": True
            }

    def _register_test_tools(self):
        """注册企业级测试专用工具"""
        self.tool_registry.register(
            name="analyze_page",
            func=self._tool_analyze_page,
            description="分析测试页面，提取可交互元素和业务逻辑",
            parameters={"page": {"type": "object", "description": "页面对象"}, "url": {"type": "string", "description": "页面URL"}},
            required=["page"]
        )

        self.tool_registry.register(
            name="generate_test_cases",
            func=self._tool_generate_test_cases,
            description="基于页面分析生成测试用例",
            parameters={
                "page_analysis": {"type": "object", "description": "页面分析结果"},
                "test_type": {"type": "string", "description": "测试类型：smoke/regression/functional"},
                "scenarios": {"type": "array", "description": "测试场景列表"}
            },
            required=["page_analysis"]
        )

        self.tool_registry.register(
            name="execute_test_step",
            func=self._tool_execute_test_step,
            description="执行单个测试步骤",
            parameters={
                "page": {"type": "object", "description": "页面对象"},
                "step": {"type": "object", "description": "测试步骤"}
            },
            required=["page", "step"]
        )

        self.tool_registry.register(
            name="execute_test_suite",
            func=self._tool_execute_test_suite,
            description="执行测试套件",
            parameters={
                "page": {"type": "object", "description": "页面对象"},
                "test_cases": {"type": "array", "description": "测试用例列表"}
            },
            required=["page", "test_cases"]
        )

        self.tool_registry.register(
            name="assert_result",
            func=self._tool_assert_result,
            description="智能断言验证",
            parameters={
                "actual": {"type": "any", "description": "实际结果"},
                "expected": {"type": "any", "description": "预期结果"},
                "assertion_type": {"type": "string", "description": "断言类型：equal/contain/not_empty/exist"},
                "tolerance": {"type": "number", "description": "容忍度（数值比较）"}
            },
            required=["actual", "expected"]
        )

        self.tool_registry.register(
            name="analyze_test_result",
            func=self._tool_analyze_test_result,
            description="智能分析测试结果",
            parameters={
                "execution_log": {"type": "object", "description": "执行日志"},
                "screenshots": {"type": "array", "description": "截图列表"},
                "expected_result": {"type": "object", "description": "预期结果"}
            },
            required=["execution_log"]
        )

        self.tool_registry.register(
            name="generate_test_report",
            func=self._tool_generate_test_report,
            description="生成结构化测试报告",
            parameters={
                "test_results": {"type": "array", "description": "测试结果列表"},
                "report_format": {"type": "string", "description": "报告格式：json/html/markdown"}
            },
            required=["test_results"]
        )

        self.tool_registry.register(
            name="take_screenshot",
            func=self._tool_take_screenshot,
            description="截图取证",
            parameters={"page": {"type": "object", "description": "页面对象"}, "name": {"type": "string", "description": "截图名称"}},
            required=["page"]
        )

        logger.info("TestAgent工具注册完成")

    def _tool_analyze_page(self, page, url: str = "") -> Dict:
        """页面分析工具 - 分析页面结构和元素"""
        # 如果 page 是字典，使用适配器包装
        if isinstance(page, dict):
            page = DictPageAdapter(page)
        
        logger.info(f"开始分析页面: {url}")
        try:
            page_info = {
                "title": page.get_title() if hasattr(page, 'get_title') else '未知页面',
                "url": url or (page.get_url() if hasattr(page, 'get_url') else ''),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            prompt = f"""请分析以下Web页面，识别可交互元素和业务逻辑：
页面标题: {page_info['title']}
页面URL: {page_info['url']}

请输出JSON格式，包含：
{{
    "elements": [
        {{
            "type": "input/button/link/select/checkbox/radio",
            "identifier": "id/name/text",
            "locator": "定位器",
            "purpose": "用途描述"
        }}
    ],
    "business_logic": "业务逻辑描述",
    "test_suggestions": ["测试建议1", "测试建议2"]
}}"""

            response = self.call_llm(prompt, json_mode=True)
            result = self.parse_json_response(response)
            result["page_info"] = page_info
            logger.info(f"页面分析完成，识别到 {len(result.get('elements', []))} 个元素")
            return result
        except Exception as e:
            logger.error(f"页面分析失败: {e}")
            return {"error": str(e), "elements": []}

    def _tool_generate_test_cases(self, page_analysis: Dict, test_type: str = "functional", scenarios: List = None) -> Dict:
        """测试用例生成工具 - 智能生成测试用例"""
        logger.info(f"生成{test_type}测试用例")
        try:
            scenarios = scenarios or ["正常流程", "异常流程", "边界条件"]
            prompt = f"""基于以下页面分析生成测试用例：
页面分析: {json.dumps(page_analysis, ensure_ascii=False)}
测试类型: {test_type}
测试场景: {scenarios}

请输出JSON格式：
{{
    "test_cases": [
        {{
            "id": "TC-001",
            "name": "测试用例名称",
            "description": "用例描述",
            "priority": "high/medium/low",
            "scenario": "测试场景",
            "preconditions": ["前置条件"],
            "steps": [
                {{
                    "step_num": 1,
                    "action": "input/click/select/assert",
                    "element": "元素标识符",
                    "value": "操作值",
                    "expected_result": "预期结果"
                }}
            ],
            "expected_result": "整体预期结果"
        }}
    ]
}}"""

            response = self.call_llm(prompt, json_mode=True)
            result = self.parse_json_response(response)
            logger.info(f"成功生成 {len(result.get('test_cases', []))} 个测试用例")
            return result
        except Exception as e:
            logger.error(f"测试用例生成失败: {e}")
            return {"error": str(e), "test_cases": []}

    def _tool_execute_test_step(self, page, step: Dict) -> Dict:
        """执行单个测试步骤 - 具备重试和错误处理"""
        # 如果 page 是字典，使用适配器包装
        if isinstance(page, dict):
            page = DictPageAdapter(page)
        
        step_num = step.get("step_num", 1)
        action = step.get("action")
        element = step.get("element")
        value = step.get("value")
        expected_result = step.get("expected_result", "")

        logger.info(f"执行步骤 {step_num}: {action} {element}")
        max_retry = self.config.get("max_retry", 3)
        retry_count = 0

        while retry_count <= max_retry:
            try:
                if action == "input":
                    page.input(element, value)
                elif action == "click":
                    page.click(element)
                elif action == "select":
                    page.select(element, value)
                elif action == "hover":
                    page.hover(element)
                elif action == "scroll":
                    page.scroll_to_element(element)
                elif action == "assert":
                    actual_result = page.get_text(element) if hasattr(page, 'get_text') else ''
                    assertion_result = self._tool_assert_result(
                        actual=actual_result,
                        expected=expected_result,
                        assertion_type="contain"
                    )
                    return {"step": step, "success": assertion_result["success"], "actual": actual_result, "assertion": assertion_result}

                result = {"step": step, "success": True, "retry": retry_count}
                logger.info(f"步骤 {step_num} 执行成功")
                return result
            except Exception as e:
                retry_count += 1
                if retry_count > max_retry:
                    logger.error(f"步骤 {step_num} 执行失败: {e}")
                    return {"step": step, "success": False, "error": str(e), "retry": max_retry}
                logger.warning(f"步骤 {step_num} 重试 {retry_count}/{max_retry}: {e}")
                time.sleep(1)

    def _tool_execute_test_suite(self, page, test_cases: List[Dict]) -> Dict:
        """执行测试套件 - 批量执行测试用例"""
        # 如果 page 是字典，使用适配器包装
        if isinstance(page, dict):
            page = DictPageAdapter(page)
        
        logger.info(f"开始执行测试套件，共 {len(test_cases)} 个用例")
        results = []
        suite_start = time.time()

        for test_case in test_cases:
            case_start = time.time()
            case_result = {
                "test_case": test_case,
                "steps": [],
                "status": "passed",
                "duration": 0,
                "screenshot": None
            }

            try:
                for step in test_case.get("steps", []):
                    step_result = self._tool_execute_test_step(page, step)
                    case_result["steps"].append(step_result)
                    if not step_result.get("success"):
                        case_result["status"] = "failed"

                if case_result["status"] == "failed" and self.config.get("take_screenshot", True):
                    case_result["screenshot"] = self._tool_take_screenshot(page, f"failed_{test_case.get('id')}")

            except Exception as e:
                logger.error(f"测试用例执行异常: {e}")
                case_result["status"] = "error"
                case_result["error"] = str(e)

            case_result["duration"] = round(time.time() - case_start, 2)
            results.append(case_result)
            self.test_results.append(case_result)

        suite_duration = round(time.time() - suite_start, 2)
        passed_count = sum(1 for r in results if r["status"] == "passed")

        logger.info(f"测试套件执行完成: {passed_count}/{len(results)} 通过，耗时 {suite_duration}秒")

        return {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "duration": suite_duration,
            "results": results
        }

    def _tool_assert_result(self, actual: Any, expected: Any, assertion_type: str = "equal", tolerance: float = 0.0) -> Dict:
        """智能断言工具 - 支持多种断言类型"""
        success = False
        message = ""

        try:
            if assertion_type == "equal":
                success = str(actual) == str(expected)
                message = f"期望: {expected}, 实际: {actual}"
            elif assertion_type == "contain":
                success = str(expected) in str(actual)
                message = f"'{expected}' 在 '{actual}' 中" if success else f"'{expected}' 不在 '{actual}' 中"
            elif assertion_type == "not_empty":
                success = bool(actual) and str(actual).strip() != ""
                message = "结果不为空" if success else "结果为空"
            elif assertion_type == "exist":
                success = actual is not None
                message = "元素存在" if success else "元素不存在"
            elif assertion_type == "numeric":
                try:
                    success = abs(float(actual) - float(expected)) <= tolerance
                    message = f"数值在允许范围内: {actual} vs {expected} (tolerance: {tolerance})"
                except:
                    success = False
                    message = "数值比较失败"

            logger.info(f"断言: {assertion_type} - {'通过' if success else '失败'} - {message}")
            return {
                "success": success,
                "assertion_type": assertion_type,
                "actual": actual,
                "expected": expected,
                "message": message
            }
        except Exception as e:
            logger.error(f"断言异常: {e}")
            return {
                "success": False,
                "assertion_type": assertion_type,
                "actual": actual,
                "expected": expected,
                "message": f"断言异常: {e}"
            }

    def _tool_analyze_test_result(self, execution_log: Dict, screenshots: List = None, expected_result: Dict = None) -> Dict:
        """智能分析测试结果 - AI驱动的结果分析"""
        logger.info("智能分析测试结果")
        try:
            prompt = f"""请分析以下测试执行结果：
执行日志: {json.dumps(execution_log, ensure_ascii=False)}
预期结果: {json.dumps(expected_result, ensure_ascii=False) if expected_result else '无'}

请输出JSON格式：
{{
    "overall_status": "passed/failed/partial",
    "root_cause": "失败根因分析",
    "failure_category": "环境问题/代码缺陷/测试问题/配置问题",
    "repair_suggestions": ["建议1", "建议2"],
    "risk_assessment": "风险评估",
    "confidence": 0.9
}}"""

            response = self.call_llm(prompt, json_mode=True)
            result = self.parse_json_response(response)
            result["screenshots"] = screenshots or []
            result["analysis_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"测试结果分析完成，状态: {result.get('overall_status')}")
            return result
        except Exception as e:
            logger.error(f"结果分析失败: {e}")
            return {"error": str(e), "overall_status": "unknown"}

    def _tool_generate_test_report(self, test_results: List[Dict], report_format: str = "json") -> Dict:
        """生成结构化测试报告"""
        logger.info(f"生成{report_format}格式测试报告")
        try:
            total = len(test_results)
            passed = sum(1 for r in test_results if r.get("status") == "passed")
            failed = sum(1 for r in test_results if r.get("status") == "failed")
            errors = sum(1 for r in test_results if r.get("status") == "error")
            duration = sum(r.get("duration", 0) for r in test_results)

            report = {
                "report_id": f"REP-{uuid.uuid4().hex[:8].upper()}",
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
                    "total_duration": round(duration, 2)
                },
                "test_results": test_results,
                "failures": [r for r in test_results if r.get("status") in ["failed", "error"]],
                "recommendations": []
            }

            if failed > 0:
                report["recommendations"].append(f"关注 {failed} 个失败用例")
            if report["summary"]["pass_rate"] < 80:
                report["recommendations"].append("通过率低于80%，建议进行完整回归测试")

            logger.info(f"测试报告生成完成: {report['report_id']}")
            return report
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {"error": str(e)}

    def _tool_take_screenshot(self, page, name: str = None) -> Dict:
        """截图工具"""
        # 如果 page 是字典，使用适配器包装
        if isinstance(page, dict):
            page = DictPageAdapter(page)
        
        screenshot_name = name or f"screenshot_{int(time.time())}"
        logger.info(f"截取屏幕: {screenshot_name}")
        try:
            screenshot_path = page.screenshot(name=screenshot_name) if hasattr(page, 'screenshot') else f"/mock/screenshots/{screenshot_name}.png"
            return {"success": True, "path": screenshot_path, "name": screenshot_name}
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return {"success": False, "error": str(e)}

    def perceive(self, **kwargs) -> Dict[str, Any]:
        """感知阶段 - 收集测试环境信息"""
        self.start_time = time.time()
        self.add_memory("system", f"开始任务感知: {kwargs.get('task_type', 'unknown')}")

        perception = {
            "task_type": kwargs.get("task_type", "ui_test"),
            "target_url": kwargs.get("target_url", ""),
            "test_objective": kwargs.get("test_objective", ""),
            "test_data": kwargs.get("test_data", {}),
            "environment": kwargs.get("environment", "staging"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "context": kwargs.get("context", {})
        }

        logger.info(f"感知完成: {perception['task_type']}")
        return perception

    def think(self, perception: Dict[str, Any]) -> TaskPlan:
        """思考阶段 - 制定测试计划"""
        self.add_memory("assistant", f"开始思考: {perception.get('test_objective', '无目标')}")
        tools = self.tool_registry.list_tools()

        prompt = f"""你是专业测试专家，请基于以下信息制定测试计划：
任务类型: {perception['task_type']}
目标URL: {perception['target_url']}
测试目标: {perception['test_objective']}
环境: {perception['environment']}
可用工具: {json.dumps(tools, ensure_ascii=False)}

请输出JSON格式：
{{
    "description": "测试计划描述",
    "steps": [
        {{
            "action": "工具名称",
            "parameters": {{}}
        }}
    ]
}}"""

        response = self.call_llm(prompt, json_mode=True, temperature=0.7)
        plan_data = self.parse_json_response(response)

        plan = TaskPlan(
            task_id=str(uuid.uuid4())[:8],
            description=plan_data.get("description", f"测试计划: {perception.get('test_objective')}"),
            steps=plan_data.get("steps", [])
        )

        self.add_memory("assistant", f"制定计划完成: {plan.description}")
        logger.info(f"思考阶段完成，计划ID: {plan.task_id}")
        return plan

    def act(self, plan: TaskPlan) -> Dict[str, Any]:
        """行动阶段 - 执行测试计划"""
        self.add_memory("assistant", f"开始执行计划: {plan.description}")
        results = []

        for i, step in enumerate(plan.steps, 1):
            action = step.get("action")
            params = step.get("parameters", {})
            logger.info(f"执行计划步骤 {i}/{len(plan.steps)}: {action}")

            tool_call = self.use_tool(action, **params)
            result = {
                "step_num": i,
                "action": action,
                "success": tool_call.success,
                "result": tool_call.result if tool_call.success else tool_call.error_msg,
                "tool_call": tool_call
            }
            results.append(result)

            if not tool_call.success:
                logger.error(f"步骤 {i} 执行失败: {tool_call.error_msg}")

        final_result = {
            "plan_id": plan.task_id,
            "total_steps": len(plan.steps),
            "step_results": results,
            "success": all(r["success"] for r in results),
            "duration": round(time.time() - self.start_time, 2) if self.start_time else 0
        }

        self.add_memory("assistant", f"执行阶段完成，结果: {'成功' if final_result['success'] else '失败'}")
        return final_result

    def reflect(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """反思阶段 - 分析并优化"""
        self.add_memory("assistant", "开始反思分析")

        total_steps = action_result.get("total_steps", 0)
        passed_steps = sum(1 for r in action_result.get("step_results", []) if r["success"])
        failed_steps = total_steps - passed_steps

        summary = {
            "test_status": "passed" if action_result.get("success") else "failed",
            "summary": {
                "total": total_steps,
                "passed": passed_steps,
                "failed": failed_steps
            },
            "details": action_result.get("step_results", []),
            "duration": action_result.get("duration", 0),
            "final_report": {}
        }

        if self.config.get("generate_report", True) and self.test_results:
            summary["final_report"] = self._tool_generate_test_report(self.test_results)

        self.add_memory("system", f"反思完成: {summary['test_status']}")
        logger.info(f"反思阶段完成: {summary['test_status']}")
        return summary

    def run_complete_test(self, page, test_objective: str, **kwargs) -> Dict[str, Any]:
        """完整测试流程 - 一键运行"""
        logger.info(f"开始完整测试流程: {test_objective}")
        return self.run(
            task_type="ui_test",
            target_url=page.get_url(),
            test_objective=test_objective,
            page=page,
            **kwargs
        )

    def quick_test(self, page, test_intent: str) -> Dict[str, Any]:
        """快速测试 - 简单测试流程"""
        logger.info(f"快速测试: {test_intent}")
        return self.run(
            task_type="quick_test",
            target_url=page.get_url(),
            test_objective=test_intent,
            page=page
        )

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            "total_tests": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r.get("status") == "passed"),
            "failed": sum(1 for r in self.test_results if r.get("status") == "failed"),
            "current_state": self.state.value,
            "current_skill": self.get_current_skill_info()
        }

    # ===== Skill系统方法 =====
    def list_available_skills(self) -> List[Dict]:
        """列出所有可用Skill"""
        return self.skill_manager.list_skills()

    def switch_skill(self, skill_id: str) -> Dict:
        """切换到指定Skill"""
        if self.skill_manager.activate_skill(skill_id):
            skill_info = self.skill_manager.get_current_skill_info()

            if skill_info and skill_info.get("system_prompt"):
                self.system_prompt = skill_info["system_prompt"]
                logger.info(f"更新系统提示词为: {skill_info['name']}")

            self.add_memory("system", f"切换到角色: {skill_info['name']}")
            return {
                "success": True,
                "skill_info": skill_info,
                "message": f"成功切换到角色: {skill_info['name']}"
            }
        return {
            "success": False,
            "message": f"Skill不存在: {skill_id}"
        }

    def get_current_skill_info(self) -> Optional[Dict]:
        """获取当前Skill信息"""
        return self.skill_manager.get_current_skill_info()

    def deactivate_skill(self):
        """停用当前Skill"""
        self.skill_manager.deactivate_skill()
        self.system_prompt = self._get_default_prompt()
        self.add_memory("system", "停用当前角色，恢复默认设置")

    def check_action_permission(self, action: str) -> Dict:
        """检查操作权限"""
        if not self.skill_manager.can_perform_action(action):
            suggested_skill = self.skill_manager.suggest_skill_for_action(action)
            return {
                "allowed": False,
                "message": self.skill_manager.get_rejection_message(),
                "suggested_skill": suggested_skill
            }
        return {"allowed": True}

    def execute_action(self, action: str, **kwargs) -> Dict:
        """执行指定动作 - 调用对应的工具"""
        try:
            tool_call = self.use_tool(action, **kwargs)
            return {
                "success": tool_call.success,
                "action": action,
                "result": tool_call.result if tool_call.success else None,
                "error": tool_call.error_msg if not tool_call.success else None
            }
        except Exception as e:
            logger.error(f"执行动作失败: {action}, 错误: {e}")
            return {
                "success": False,
                "action": action,
                "error": str(e)
            }

    def execute_with_skill_check(self, action: str, **kwargs) -> Dict:
        """执行操作前检查Skill权限"""
        permission_check = self.check_action_permission(action)
        if not permission_check["allowed"]:
            return {
                "status": "rejected",
                "message": permission_check["message"],
                "suggested_skill": permission_check.get("suggested_skill")
            }
        return self.execute_action(action, **kwargs)

    def register_custom_skill(self, skill_def: Dict) -> Dict:
        """注册自定义Skill"""
        success = self.skill_manager.register_custom_skill(skill_def)
        if success:
            return {
                "success": True,
                "message": f"成功注册自定义Skill: {skill_def.get('name')}"
            }
        return {"success": False, "message": "注册自定义Skill失败"}
