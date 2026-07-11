"""
AI智能体数据模型
持久化存储AI智能体信息到数据库
"""
import json
from datetime import datetime
from backend.utils.database import Database


class AIAgent:
    """AI智能体模型"""

    @staticmethod
    def create(agent_id: str, name: str, description: str = None,
               current_skill: str = 'test_expert', config: dict = None,
               created_by: int = None) -> int:
        """创建AI智能体
        
        Args:
            agent_id: 智能体UUID
            name: 智能体名称
            description: 描述
            current_skill: 当前Skill
            config: 配置信息
            created_by: 创建者ID
            
        Returns:
            记录ID
        """
        sql = """
            INSERT INTO ai_agent (agent_id, name, description, current_skill, 
                                  config, statistics, skill_history, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        config_json = json.dumps(config) if config else None
        statistics_json = json.dumps({'total_actions': 0, 'success_count': 0, 'failed_count': 0})
        skill_history_json = json.dumps([])
        
        return Database.execute_insert(sql, (
            agent_id, name, description, current_skill,
            config_json, statistics_json, skill_history_json, created_by
        ))

    @staticmethod
    def find_by_agent_id(agent_id: str):
        """根据agent_id查找智能体"""
        sql = "SELECT * FROM ai_agent WHERE agent_id = %s"
        record = Database.execute_query(sql, (agent_id,), fetch_one=True)
        return AIAgent._parse_json_fields(record)

    @staticmethod
    def find_all(page: int = 1, page_size: int = 20, status: str = None):
        """获取所有智能体（分页）"""
        offset = (page - 1) * page_size
        
        if status:
            where_clause = "WHERE status = %s"
            params = [status, page_size, offset]
            count_params = [status]
        else:
            where_clause = ""
            params = [page_size, offset]
            count_params = []
        
        sql = f"""
            SELECT * FROM ai_agent
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        count_sql = f"SELECT COUNT(*) as total FROM ai_agent {where_clause}"
        
        results = Database.execute_query(sql, tuple(params))
        total = Database.execute_query(count_sql, tuple(count_params), fetch_one=True)['total']
        
        if results:
            results = [AIAgent._parse_json_fields(r) for r in results]
        
        return {
            'items': results,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def update(agent_id: str, **kwargs):
        """更新智能体信息"""
        allowed_fields = ['name', 'description', 'status', 'current_skill', 
                          'skill_history', 'statistics', 'config', 'last_active']
        
        updates = []
        params = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ['skill_history', 'statistics', 'config']:
                    value = json.dumps(value) if value else None
                updates.append(f"{key} = %s")
                params.append(value)
        
        if not updates:
            return 0
        
        params.append(agent_id)
        sql = f"UPDATE ai_agent SET {', '.join(updates)} WHERE agent_id = %s"
        return Database.execute_update(sql, tuple(params))

    @staticmethod
    def update_status(agent_id: str, status: str):
        """更新状态"""
        sql = "UPDATE ai_agent SET status = %s, last_active = NOW() WHERE agent_id = %s"
        return Database.execute_update(sql, (status, agent_id))

    @staticmethod
    def update_skill(agent_id: str, skill: str):
        """更新当前Skill并记录历史"""
        agent = AIAgent.find_by_agent_id(agent_id)
        if not agent:
            return 0
        
        skill_history = agent.get('skill_history', []) or []
        skill_history.append({
            'skill': skill,
            'timestamp': datetime.now().isoformat()
        })
        
        sql = """
            UPDATE ai_agent 
            SET current_skill = %s, skill_history = %s, last_active = NOW()
            WHERE agent_id = %s
        """
        return Database.execute_update(sql, (skill, json.dumps(skill_history), agent_id))

    @staticmethod
    def update_statistics(agent_id: str, statistics: dict):
        """更新统计信息"""
        sql = "UPDATE ai_agent SET statistics = %s WHERE agent_id = %s"
        return Database.execute_update(sql, (json.dumps(statistics), agent_id))

    @staticmethod
    def delete(agent_id: str):
        """删除智能体"""
        sql = "DELETE FROM ai_agent WHERE agent_id = %s"
        return Database.execute_update(sql, (agent_id,))

    @staticmethod
    def _parse_json_fields(record):
        """解析JSON字段"""
        if not record:
            return record
        
        json_fields = ['skill_history', 'statistics', 'config']
        for field in json_fields:
            if record.get(field) and isinstance(record[field], str):
                try:
                    record[field] = json.loads(record[field])
                except:
                    record[field] = None
        
        return record


class AIAgentExecutionLog:
    """AI智能体执行日志模型"""

    @staticmethod
    def create(agent_id: str, action: str, skill: str = None,
               input_params: dict = None) -> int:
        """创建执行日志"""
        sql = """
            INSERT INTO ai_agent_execution_log (agent_id, action, skill, input, status)
            VALUES (%s, %s, %s, %s, 'running')
        """
        input_json = json.dumps(input_params) if input_params else None
        return Database.execute_insert(sql, (agent_id, action, skill, input_json))

    @staticmethod
    def complete(log_id: int, output: dict = None, status: str = 'success',
                 error_message: str = None, duration: float = None):
        """完成执行日志"""
        sql = """
            UPDATE ai_agent_execution_log
            SET output = %s, status = %s, error_message = %s, duration = %s
            WHERE id = %s
        """
        output_json = json.dumps(output) if output else None
        return Database.execute_update(sql, (output_json, status, error_message, duration, log_id))

    @staticmethod
    def find_by_agent(agent_id: str, limit: int = 100):
        """获取智能体的执行日志"""
        sql = """
            SELECT * FROM ai_agent_execution_log
            WHERE agent_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        results = Database.execute_query(sql, (agent_id, limit))
        return AIAgentExecutionLog._parse_json_fields(results)

    @staticmethod
    def _parse_json_fields(records):
        """解析JSON字段"""
        if not records:
            return records
        
        if isinstance(records, dict):
            records = [records]
        
        for r in records:
            if r.get('input') and isinstance(r['input'], str):
                try:
                    r['input'] = json.loads(r['input'])
                except:
                    r['input'] = None
            if r.get('output') and isinstance(r['output'], str):
                try:
                    r['output'] = json.loads(r['output'])
                except:
                    r['output'] = None
        
        return records
