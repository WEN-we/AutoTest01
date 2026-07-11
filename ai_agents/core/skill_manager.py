"""
Skill管理器 - 管理AI智能体的角色切换
"""
import os
import yaml
import markdown
from typing import Dict, List, Optional


class Skill:
    """Skill定义类"""
    
    def __init__(self, config: Dict):
        self.name: str = config.get('name', '')
        self.role: str = config.get('role', '')
        self.description: str = config.get('description', '')
        self.capabilities: List[str] = config.get('capabilities', [])
        self.forbidden_actions: List[str] = config.get('forbidden_actions', [])
        self.personality: Dict = config.get('personality', {})
        self.response_style: Dict = config.get('response_style', {})
        self.response_format: Dict = config.get('response_format', {})
        self.switch_suggestions: Dict = config.get('switch_suggestions', {})
        self.rejection_message: str = config.get('rejection_message', '')
        
    def can_do(self, action: str) -> bool:
        """检查是否可以执行该操作"""
        return action in self.capabilities
    
    def cannot_do(self, action: str) -> bool:
        """检查是否禁止该操作"""
        return action in self.forbidden_actions
    
    def get_rejection_response(self) -> str:
        """获取拒绝响应"""
        return self.rejection_message


class SkillManager:
    """Skill管理器"""
    
    def __init__(self, skills_dir: str = None):
        self.skills: Dict[str, Skill] = {}
        self.current_skill: Optional[Skill] = None
        self.skills_dir = skills_dir or '.claude/skills'
        
    def load_skills(self) -> None:
        """加载所有Skill文件"""
        if not os.path.exists(self.skills_dir):
            return
            
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                self._load_skill(skill_name, skill_path)
    
    def _load_skill(self, skill_name: str, skill_path: str) -> None:
        """加载单个Skill"""
        skill_file = os.path.join(skill_path, 'SKILL.md')
        if not os.path.exists(skill_file):
            return
            
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            skill_config = self._parse_skill_markdown(content)
            self.skills[skill_name] = Skill(skill_config)
        except Exception as e:
            print(f"加载Skill失败 {skill_name}: {e}")
    
    def _parse_skill_markdown(self, content: str) -> Dict:
        """解析Skill的Markdown文件"""
        config = {}
        
        # 解析角色定义
        role_section = self._extract_section(content, '角色定义')
        if role_section:
            config['name'] = self._extract_value(role_section, '名称')
            config['role'] = self._extract_value(role_section, '角色')
            config['description'] = self._extract_value(role_section, '描述')
            
            # 解析性格特点
            personality = {}
            personality_section = self._extract_subsection(role_section, '性格特点')
            if personality_section:
                for line in personality_section.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or '：' in line):
                        parts = line.replace('-', '').strip().split('：', 1)
                        if len(parts) == 2:
                            personality[parts[0].strip()] = parts[1].strip()
            config['personality'] = personality
        
        # 解析核心能力
        capabilities_section = self._extract_section(content, '核心能力')
        if capabilities_section:
            capabilities = []
            # 查找capabilities的yaml块
            import re
            yaml_match = re.search(r'capabilities:\s*\n((?:\s*- \w+.*\n?)+)', capabilities_section)
            if yaml_match:
                yaml_content = 'capabilities:\n' + yaml_match.group(1)
                try:
                    parsed = yaml.safe_load(yaml_content)
                    if isinstance(parsed, dict) and 'capabilities' in parsed:
                        capabilities = parsed['capabilities']
                except:
                    pass
            config['capabilities'] = capabilities
        
        # 解析禁止行为
        forbidden_section = self._extract_section(content, '禁止行为')
        if forbidden_section:
            forbidden_actions = []
            yaml_match = re.search(r'forbidden_actions:\s*\n((?:\s*- \w+.*\n?)+)', forbidden_section)
            if yaml_match:
                yaml_content = 'forbidden_actions:\n' + yaml_match.group(1)
                try:
                    parsed = yaml.safe_load(yaml_content)
                    if isinstance(parsed, dict) and 'forbidden_actions' in parsed:
                        forbidden_actions = parsed['forbidden_actions']
                except:
                    pass
            config['forbidden_actions'] = forbidden_actions
            
            # 解析拒绝话术
            rejection_match = re.search(r'```\n([\s\S]*?)```', forbidden_section)
            if rejection_match:
                config['rejection_message'] = rejection_match.group(1).strip()
        
        # 解析响应风格
        style_section = self._extract_section(content, '响应风格')
        if style_section:
            response_style = {}
            style_def = self._extract_subsection(style_section, '风格定义')
            if style_def:
                for line in style_def.split('\n'):
                    line = line.strip()
                    if line and '：' in line:
                        parts = line.split('：', 1)
                        if len(parts) == 2:
                            response_style[parts[0].strip()] = parts[1].strip()
            config['response_style'] = response_style
            
            # 解析输出格式
            yaml_match = re.search(r'response_format:\s*\n((?:\s*[\w\s:-]+\n?)+)', style_section)
            if yaml_match:
                try:
                    config['response_format'] = yaml.safe_load(yaml_match.group(0))
                except:
                    config['response_format'] = {}
        
        # 解析角色切换建议
        switch_section = self._extract_section(content, '角色切换建议')
        if switch_section:
            switch_suggestions = {}
            # 解析表格
            lines = switch_section.split('\n')
            for line in lines:
                if '|' in line and '角色' not in line and '---' not in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3:
                        switch_suggestions[parts[0]] = {
                            'purpose': parts[1],
                            'command': parts[2]
                        }
            config['switch_suggestions'] = switch_suggestions
        
        return config
    
    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """提取指定章节"""
        pattern = rf'##\s+{section_name}\s*\n([\s\S]*?)(?=\n##\s|\Z)'
        import re
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None
    
    def _extract_subsection(self, content: str, subsection_name: str) -> Optional[str]:
        """提取子章节"""
        pattern = rf'###\s+{subsection_name}\s*\n([\s\S]*?)(?=\n###\s|\n##\s|\Z)'
        import re
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None
    
    def _extract_value(self, content: str, key: str) -> str:
        """提取键值对的值"""
        import re
        pattern = rf'{key}[:：]\s*([^\n]+)'
        match = re.search(pattern, content)
        return match.group(1).strip() if match else ''
    
    def list_skills(self) -> List[Dict]:
        """列出所有可用Skill"""
        result = []
        for name, skill in self.skills.items():
            result.append({
                'name': name,
                'role': skill.role,
                'description': skill.description,
                'capabilities': skill.capabilities[:3] + ['...'] if len(skill.capabilities) > 3 else skill.capabilities
            })
        return result
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """获取指定Skill"""
        return self.skills.get(skill_name)
    
    def activate_skill(self, skill_name: str) -> bool:
        """激活指定Skill"""
        skill = self.skills.get(skill_name)
        if skill:
            self.current_skill = skill
            return True
        return False
    
    def get_current_skill(self) -> Optional[Skill]:
        """获取当前激活的Skill"""
        return self.current_skill
    
    def check_action(self, action: str) -> bool:
        """检查当前Skill是否允许执行该操作"""
        if not self.current_skill:
            return True  # 没有激活Skill时允许所有操作
        return self.current_skill.can_do(action)
    
    def process_request(self, action: str, **kwargs) -> Dict:
        """处理请求，根据当前Skill决定响应"""
        if not self.current_skill:
            return {
                'status': 'error',
                'message': '请先选择一个角色Skill'
            }
        
        if self.current_skill.cannot_do(action):
            return {
                'status': 'rejected',
                'message': self.current_skill.get_rejection_response(),
                'suggestions': self.current_skill.switch_suggestions
            }
        
        return {
            'status': 'allowed',
            'skill': self.current_skill.name,
            'action': action,
            'data': kwargs
        }
    
    def suggest_switch(self, action: str) -> Optional[str]:
        """建议切换到适合执行该操作的Skill"""
        for name, skill in self.skills.items():
            if skill.can_do(action) and name != self.current_skill.name:
                return skill.switch_suggestions.get(name, {}).get('command', f'/skill {name}')
        return None


# 全局Skill管理器实例
skill_manager = SkillManager()
