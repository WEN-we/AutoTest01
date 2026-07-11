"""
Skill Manager - Agent角色管理系统
企业级Skill管理：
- 角色定义
- 能力验证
- 权限控制
- 角色切换
"""
import os
import json
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from utils.tools.logger import log as logger


class SkillType(Enum):
    """Skill类型枚举"""
    TEST_EXPERT = "test_expert"
    CODE_HELPER = "code_helper"
    REPORT_EXPERT = "report_expert"
    REQUIREMENT_ANALYST = "requirement_analyst"
    DEVOPS_ENGINEER = "devops_engineer"


@dataclass
class SkillDefinition:
    """Skill定义类"""
    skill_id: str
    name: str
    role: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    personality: Dict[str, Any] = field(default_factory=dict)
    response_style: Dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    switch_suggestions: Dict[str, Any] = field(default_factory=dict)
    rejection_message: str = ""


class SkillManager:
    """Skill管理器 - 企业级角色管理系统"""

    def __init__(self, skills_dir: str = ".claude/skills"):
        self.skills: Dict[str, SkillDefinition] = {}
        self.current_skill: Optional[SkillDefinition] = None
        self.skills_dir = skills_dir
        self._load_default_skills()

    def _load_default_skills(self):
        """加载默认Skill"""
        logger.info(f"初始化SkillManager，目录: {self.skills_dir}")

        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skill目录不存在: {self.skills_dir}，创建默认Skill")
            self._create_default_skills()
            return

        self._load_skills_from_directory()

    def _create_default_skills(self):
        """创建默认Skill"""
        default_skills = [
            {
                "skill_id": "test_expert",
                "name": "测试专家",
                "role": "企业级自动化测试专家",
                "description": "专注于自动化测试的专业智能体，擅长页面分析、测试用例生成、测试执行和结果分析",
                "capabilities": [
                    "page_analysis", "test_design", "test_generation",
                    "test_execution", "result_analysis", "report_generation",
                    "bug_analysis", "test_optimization"
                ],
                "forbidden_actions": [
                    "code_writing", "code_review", "system_admin",
                    "database_operation", "security_audit"
                ],
                "personality": {
                    "style": "专业严谨",
                    "tone": "正式",
                    "detail_level": "高"
                },
                "system_prompt": """你是一位专业的企业级自动化测试专家，具备以下核心能力：
1. 测试分析：深度理解需求，精准识别测试点和风险
2. 测试设计：生成覆盖全面的测试用例
3. 测试执行：调用工具执行测试步骤
4. 结果断言：智能验证实际结果与预期
5. 缺陷分析：精准定位问题根因，提供专业修复建议

请始终保持专业、严谨、细致的工作态度。""",
                "rejection_message": "抱歉，我是测试专家角色，不擅长处理代码相关问题。您可以尝试切换到代码助手角色。"
            },
            {
                "skill_id": "code_helper",
                "name": "代码助手",
                "role": "专业的代码开发助手",
                "description": "专注于代码编写、调试、优化和架构设计的智能体",
                "capabilities": [
                    "code_writing", "code_debugging", "code_review",
                    "code_optimization", "architecture_design",
                    "tech_consulting", "documentation"
                ],
                "forbidden_actions": [
                    "test_execution", "test_generation", "system_admin",
                    "database_operation", "security_audit"
                ],
                "personality": {
                    "style": "技术导向",
                    "tone": "专业",
                    "detail_level": "高"
                },
                "system_prompt": """你是一位专业的代码开发助手，具备以下核心能力：
1. 代码编写：编写高质量、可维护的代码
2. 代码调试：调试和修复代码bug
3. 代码审查：审查代码质量
4. 代码优化：优化代码性能
5. 架构设计：设计系统架构

请提供清晰的代码示例和详细的解释。""",
                "rejection_message": "抱歉，我是代码助手角色，不擅长处理测试执行相关问题。您可以尝试切换到测试专家角色。"
            },
            {
                "skill_id": "report_expert",
                "name": "报告专家",
                "role": "专业的报告生成专家",
                "description": "专注于生成结构化、高质量的测试报告和数据分析报告",
                "capabilities": [
                    "report_generation", "data_analysis", "chart_generation",
                    "trend_analysis", "report_optimization", "summary_report"
                ],
                "forbidden_actions": [
                    "test_execution", "code_writing", "system_admin",
                    "database_operation"
                ],
                "personality": {
                    "style": "结构化",
                    "tone": "正式",
                    "detail_level": "高"
                },
                "system_prompt": """你是一位专业的报告生成专家，擅长：
1. 数据可视化：生成高质量的图表和可视化
2. 报告结构：创建清晰、结构化的报告
3. 趋势分析：分析数据趋势和模式
4. 结论提炼：总结关键发现和建议

请始终提供专业、客观、结构清晰的报告。""",
                "rejection_message": "抱歉，我是报告专家角色，不擅长处理测试执行或代码问题。您可以尝试切换到其他角色。"
            }
        ]

        for skill_data in default_skills:
            skill = SkillDefinition(**skill_data)
            self.skills[skill.skill_id] = skill
            logger.info(f"创建默认Skill: {skill.name}")

    def _load_skills_from_directory(self):
        """从目录加载Skill"""
        if not os.path.exists(self.skills_dir):
            self._create_default_skills()
            return
            
        # 先检查目录是否有有效的Skill文件
        has_skill = False
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    has_skill = True
                    break
        
        if not has_skill:
            logger.warning(f"Skill目录中未找到有效SKILL.md，创建默认Skill")
            self._create_default_skills()
            return
            
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                self._load_single_skill(skill_name, skill_path)

    def _load_single_skill(self, skill_name: str, skill_path: str):
        """加载单个Skill"""
        skill_file = os.path.join(skill_path, "SKILL.md")
        if not os.path.exists(skill_file):
            return

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()

            skill_config = self._parse_skill_markdown(content)
            skill_config["skill_id"] = skill_name
            # 如果name为空，使用skill_name作为默认名称
            if not skill_config.get("name"):
                skill_config["name"] = skill_name.replace("-", " ").title()
            skill = SkillDefinition(**skill_config)
            self.skills[skill_name] = skill
            logger.info(f"加载Skill: {skill.name}")
        except Exception as e:
            logger.error(f"加载Skill失败 {skill_name}: {e}")

    def _parse_skill_markdown(self, content: str) -> Dict:
        """解析Skill Markdown文件"""
        config = {
            "name": "",
            "role": "",
            "description": "",
            "capabilities": [],
            "forbidden_actions": [],
            "personality": {},
            "response_style": {},
            "system_prompt": "",
            "switch_suggestions": {},
            "rejection_message": ""
        }

        # 解析角色定义
        role_section = self._extract_section(content, "角色定义")
        if role_section:
            config["name"] = self._extract_value(role_section, "名称")
            config["role"] = self._extract_value(role_section, "角色")
            config["description"] = self._extract_value(role_section, "描述")

        # 解析核心能力
        capabilities_section = self._extract_section(content, "核心能力")
        if capabilities_section:
            import re
            yaml_match = re.search(r"capabilities:\s*\n((?:\s*-\s*\w+.*\n?)+)", capabilities_section)
            if yaml_match:
                yaml_content = "capabilities:\n" + yaml_match.group(1)
                try:
                    parsed = yaml.safe_load(yaml_content)
                    if isinstance(parsed, dict) and "capabilities" in parsed:
                        config["capabilities"] = parsed["capabilities"]
                except:
                    pass

        # 解析禁止行为
        forbidden_section = self._extract_section(content, "禁止行为")
        if forbidden_section:
            import re
            yaml_match = re.search(r"forbidden_actions:\s*\n((?:\s*-\s*\w+.*\n?)+)", forbidden_section)
            if yaml_match:
                yaml_content = "forbidden_actions:\n" + yaml_match.group(1)
                try:
                    parsed = yaml.safe_load(yaml_content)
                    if isinstance(parsed, dict) and "forbidden_actions" in parsed:
                        config["forbidden_actions"] = parsed["forbidden_actions"]
                except:
                    pass

            import re
            rejection_match = re.search(r"```\s*\n([\s\S]*?)\n```", forbidden_section)
            if rejection_match:
                config["rejection_message"] = rejection_match.group(1).strip()

        return config

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """提取章节内容"""
        import re
        pattern = rf"##\s*{section_name}\s*\n([\s\S]*?)(?=\n##\s|\Z)"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None

    def _extract_value(self, content: str, key: str) -> str:
        """提取键值对"""
        import re
        pattern = rf"{key}[:：]\s*([^\n]+)"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else ""

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """获取Skill定义"""
        return self.skills.get(skill_id)

    def list_skills(self) -> List[Dict]:
        """列出所有可用Skill"""
        return [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "role": skill.role,
                "description": skill.description,
                "capabilities": skill.capabilities[:5] + ["..."] if len(skill.capabilities) > 5 else skill.capabilities
            }
            for skill in self.skills.values()
        ]

    def activate_skill(self, skill_id: str) -> bool:
        """激活指定Skill"""
        skill = self.skills.get(skill_id)
        if skill:
            self.current_skill = skill
            logger.info(f"激活Skill: {skill.name}")
            return True
        logger.warning(f"Skill不存在: {skill_id}")
        return False

    def deactivate_skill(self):
        """停用当前Skill"""
        if self.current_skill:
            logger.info(f"停用Skill: {self.current_skill.name}")
            self.current_skill = None

    def can_perform_action(self, action: str) -> bool:
        """检查当前Skill是否可以执行该操作"""
        if not self.current_skill:
            return True

        if action in self.current_skill.forbidden_actions:
            return False

        if not self.current_skill.capabilities:
            return True

        return action in self.current_skill.capabilities

    def is_action_forbidden(self, action: str) -> bool:
        """检查操作是否被禁止"""
        if not self.current_skill:
            return False
        return action in self.current_skill.forbidden_actions

    def get_rejection_message(self) -> str:
        """获取拒绝消息"""
        if self.current_skill:
            return self.current_skill.rejection_message
        return ""

    def suggest_skill_for_action(self, action: str) -> Optional[str]:
        """为操作推荐合适的Skill"""
        for skill_id, skill in self.skills.items():
            if action in skill.capabilities:
                if self.current_skill and skill_id == self.current_skill.skill_id:
                    continue
                return skill_id
        return None

    def get_current_skill_info(self) -> Optional[Dict]:
        """获取当前激活Skill信息"""
        if not self.current_skill:
            return None
        return {
            "skill_id": self.current_skill.skill_id,
            "name": self.current_skill.name,
            "role": self.current_skill.role,
            "description": self.current_skill.description,
            "capabilities": self.current_skill.capabilities
        }

    def register_custom_skill(self, skill_def: Dict) -> bool:
        """注册自定义Skill"""
        try:
            required_fields = ["skill_id", "name", "role", "description"]
            for field in required_fields:
                if field not in skill_def:
                    logger.error(f"自定义Skill缺少必填字段: {field}")
                    return False

            skill = SkillDefinition(**skill_def)
            self.skills[skill.skill_id] = skill
            logger.info(f"注册自定义Skill: {skill.name}")
            return True
        except Exception as e:
            logger.error(f"注册自定义Skill失败: {e}")
            return False


# 全局Skill管理器实例
skill_manager = SkillManager()
