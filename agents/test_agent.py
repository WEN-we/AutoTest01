"""TestAgent - 测试专用智能体"""
import json
import uuid
from typing import Dict, List, Any
from agents.base_agent import BaseAgent, TaskPlan, ToolCall


class TestAgent(BaseAgent):
    """测试专用智能体"""

    def __init__(self, ai_client=None, system_prompt: str = ""):
        default_prompt = """你是一位专业的自动化测试专家，具备以下能力：
1. 测试分析：理解需求，识别测试点和风险
2. 测试设计：生成覆盖全面的测试用例
3. 测试执行：调用工具执行测试步骤
4. 结果断言：验证实际结果与预期
5. 缺陷分析：定位问题根因，提供修复建议"""

        super().__init__(
            name="TestAgent",
            ai_client=ai_client,
            system_prompt=system_prompt or default_prompt,
            max_memory=30
        )
        self._register_test_tools()

    def _register_test_tools(self):
        """注册测试专用工具"""
        self.tool_registry.register(
            name="analyze_requirement",
            func=self._tool_analyze_requirement,
            description="分析测试需求，提取测试点和验收标准",
            parameters={"requirement": {"type": "string", "description": "需求描述"}},
            required=["requirement"]
        )

        self.tool_registry.register(
            name="execute_ui_test",
            func=self._tool_execute_ui_test,
            description="执行UI测试步骤",
            parameters={
                "page": {"type": "object", "description": "页面对象"},
                "steps": {"type": "array", "description": "测试步骤列表"}
            },
            required=["page", "steps"]
        )

        self.tool_registry.register(
            name="assert_result",
            func=self._tool_assert_result,
            description="验证测试结果",
            parameters={
                "actual": {"type": "any", "description": "实际结果"},
                "expected": {"type": "any", "description": "预期结果"},
                "assertion_type": {"type": "string", "description": "断言类型"}
            },
            required=["actual", "expected"]
        )

    def _tool_analyze_requirement(self, requirement: str) -> Dict:
        """分析需求工具"""
        prompt = f"请分析以下测试需求：\n\n{requirement}\n\n输出JSON格式"
        response = self.call_llm(prompt, json_mode=True)
        return self.parse_json_response(response)

    def _tool_execute_ui_test(self, page, steps: List[Dict]) -> Dict:
        """执行UI测试工具"""
        results = []
        for step in steps:
            action = step.get("action")
            element = step.get("element")
            value = step.get("value")

            try:
                if action == "input":
                    page.input(element, value)
                elif action == "click":
                    page.click(element)
                results.append({"step": step, "success": True})
            except Exception as e:
                results.append({"step": step, "success": False, "error": str(e)})

        return {"success": all(r["success"] for r in results), "details": results}

    def _tool_assert_result(self, actual: Any, expected: Any, assertion_type: str = "equal") -> Dict:
        """断言工具"""
        if assertion_type == "equal":
            success = actual == expected
        elif assertion_type == "contain":
            success = expected in actual
        else:
            success = actual is not None

        return {"success": success, "actual": actual, "expected": expected}

    def perceive(self, **kwargs) -> Dict[str, Any]:
        """感知阶段"""
        return {
            "test_type": kwargs.get("test_type", "ui"),
            "target": kwargs.get("target"),
            "requirement": kwargs.get("requirement", ""),
            "context": kwargs.get("context", {})
        }

    def think(self, perception: Dict[str, Any]) -> TaskPlan:
        """思考阶段"""
        tools = self.tool_registry.list_tools()

        prompt = f"""基于以下信息制定测试计划：
测试类型：{perception['test_type']}
需求：{perception['requirement']}
可用工具：{json.dumps(tools, ensure_ascii=False)}

输出JSON格式：
{{
    "description": "测试计划描述",
    "steps": [{"action": "工具名", "parameters": {...}}]
}}"""

        response = self.call_llm(prompt, json_mode=True)
        plan_data = self.parse_json_response(response)

        return TaskPlan(
            task_id=str(uuid.uuid4())[:8],
            description=plan_data.get("description", "测试计划"),
            steps=plan_data.get("steps", [])
        )

    def act(self, plan: TaskPlan) -> Dict[str, Any]:
        """行动阶段"""
        results = []
        for step in plan.steps:
            action = step.get("action")
            params = step.get("parameters", {})
            tool_call = self.use_tool(action, **params)
            results.append({
                "action": action,
                "success": tool_call.success,
                "result": tool_call.result if tool_call.success else tool_call.error_msg
            })

        return {
            "plan_id": plan.task_id,
            "total_steps": len(plan.steps),
            "step_results": results,
            "success": all(r["success"] for r in results)
        }

    def reflect(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """反思阶段"""
        return {
            "test_status": "passed" if action_result.get("success") else "failed",
            "summary": {
                "total": action_result.get("total_steps", 0),
                "passed": sum(1 for r in action_result.get("step_results", []) if r["success"]),
                "failed": sum(1 for r in action_result.get("step_results", []) if not r["success"])
            },
            "details": action_result.get("step_results", [])
        }

    def quick_test(self, page, test_intent: str) -> Dict[str, Any]:
        """快速测试"""
        return self.run(
            test_type="ui",
            target=page,
            requirement=test_intent
        )