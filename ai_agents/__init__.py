"""
AI智能体模块 - 支持角色切换的测试辅助智能体
"""

from .core.agent import AIAgent
from .core.skill_manager import SkillManager, Skill, skill_manager

__all__ = [
    'AIAgent',
    'SkillManager',
    'Skill',
    'skill_manager'
]

__version__ = '1.0.0'
__description__ = '支持角色切换的AI测试智能体'
