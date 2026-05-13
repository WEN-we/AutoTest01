"""BaseAgent - AI智能体基类"""
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    PERCEIVING = "perceiving"
    THINKING = "thinking"
    ACTING = "acting"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Memory:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    tool_name: str
    parameters: Dict[str, Any]
    result: Any = None
    success: bool = True
    error_msg: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskPlan:
    task_id: str
    description: str
    steps: List[Dict[str, Any]]
    current_step: int = 0
    status: str = "pending"


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, func: Callable, description: str,
                 parameters: Dict[str, Any], required: List[str] = None):
        self._tools[name] = {
            "func": func,
            "description": description,
            "parameters": parameters,
            "required": required or []
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "description": tool["description"],
                "parameters": tool["parameters"],
                "required": tool["required"]
            }
            for name, tool in self._tools.items()
        }

    def execute(self, name: str, **kwargs) -> ToolCall:
        tool = self._tools.get(name)
        if not tool:
            return ToolCall(tool_name=name, parameters=kwargs, success=False,
                            error_msg=f"工具不存在: {name}")

        for req in tool["required"]:
            if req not in kwargs:
                return ToolCall(tool_name=name, parameters=kwargs, success=False,
                                error_msg=f"缺少必填参数: {req}")

        try:
            result = tool["func"](**kwargs)
            return ToolCall(tool_name=name, parameters=kwargs, result=result, success=True)
        except Exception as e:
            return ToolCall(tool_name=name, parameters=kwargs, success=False, error_msg=str(e))


class BaseAgent(ABC):
    """AI智能体基类"""

    def __init__(self, name: str, ai_client=None, system_prompt: str = "", max_memory: int = 20):
        self.name = name
        self.ai_client = ai_client
        self.system_prompt = system_prompt
        self.max_memory = max_memory

        self.state = AgentState.IDLE
        self.memory: List[Memory] = []
        self.tool_registry = ToolRegistry()
        self.current_plan: Optional[TaskPlan] = None
        self.tool_calls: List[ToolCall] = []

    def add_memory(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加记忆"""
        memory = Memory(role=role, content=content, metadata=metadata or {})
        self.memory.append(memory)

        if len(self.memory) > self.max_memory:
            system_memories = [m for m in self.memory if m.role == "system"]
            other_memories = [m for m in self.memory if m.role != "system"]
            other_memories = other_memories[-(self.max_memory - len(system_memories)):]
            self.memory = system_memories + other_memories

    def get_memory_context(self, limit: int = 10) -> str:
        """获取记忆上下文"""
        recent = self.memory[-limit:] if len(self.memory) > limit else self.memory
        return "\n".join([f"[{m.role}] {m.content}" for m in recent])

    def use_tool(self, tool_name: str, **kwargs) -> ToolCall:
        """使用工具"""
        self.state = AgentState.ACTING
        tool_call = self.tool_registry.execute(tool_name, **kwargs)
        self.tool_calls.append(tool_call)
        return tool_call

    @abstractmethod
    def perceive(self, **kwargs) -> Dict[str, Any]:
        """感知环境 - 收集信息"""
        pass

    @abstractmethod
    def think(self, perception: Dict[str, Any]) -> TaskPlan:
        """思考决策 - 制定计划"""
        pass

    @abstractmethod
    def act(self, plan: TaskPlan) -> Dict[str, Any]:
        """执行行动 - 调用工具"""
        pass

    @abstractmethod
    def reflect(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """反思结果 - 分析并修正"""
        pass

    def run(self, **kwargs) -> Dict[str, Any]:
        """运行Agent完整生命周期"""
        try:
            self.state = AgentState.PERCEIVING
            perception = self.perceive(**kwargs)
            self.add_memory("user", f"任务输入: {kwargs}")

            self.state = AgentState.THINKING
            plan = self.think(perception)
            self.current_plan = plan
            self.add_memory("assistant", f"制定计划: {plan.description}")

            self.state = AgentState.ACTING
            action_result = self.act(plan)

            self.state = AgentState.REFLECTING
            final_result = self.reflect(action_result)

            self.state = AgentState.COMPLETED
            return final_result

        except Exception as e:
            self.state = AgentState.ERROR
            return {"status": "error", "error": str(e), "state": self.state.value}

    def call_llm(self, prompt: str, temperature: float = 0.7,
                 max_tokens: int = 2000, json_mode: bool = False) -> str:
        """调用LLM"""
        if json_mode:
            prompt += "\n\n请严格按照JSON格式输出。"

        return self.ai_client.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": "json_parse_failed", "raw_response": response}