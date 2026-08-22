"""
AI 工具链（大厂 AI 时代测开：AI 辅助测试全链路）

模块：
- llm_client      ：轻量 LLM 客户端（OpenAI 兼容：通义/DeepSeek/OpenAI）
- failure_analyzer：失败智能分析（LLM 归因 + 规则降级）
- flaky_detector  ：flaky 用例识别（失败率 30%~70% 区间）
- test_generator  ：AI 用例生成建议（描述 → pytest 骨架）

设计原则：
- 所有 AI 能力在未配置 API Key 时自动降级为规则/模板模式，不影响主流程
- API Key 只从环境变量 / config/ai_tools.yaml 读取，禁止硬编码
"""
from utils.ai.failure_analyzer import FailureAnalyzer
from utils.ai.flaky_detector import FlakyDetector
from utils.ai.llm_client import LLMClient
from utils.ai.test_generator import TestGenerator

__all__ = ["LLMClient", "FailureAnalyzer", "FlakyDetector", "TestGenerator"]
