# 测试平台技术架构与AI智能体

## 目录

1. [系统架构](#1-系统架构)
2. [AI智能体系统](#2-ai智能体系统)
3. [项目结构](#3-项目结构)
4. [数据库设计](#4-数据库设计)
5. [开发指南](#5-开发指南)
6. [部署说明](#6-部署说明)

---

## 1. 系统架构

### 1.1 技术栈

**后端**
- 框架：Flask (Python)
- 数据库：MySQL
- 认证：JWT
- 任务队列：Celery (可选)
- 缓存：Redis (可选)

**前端**
- 框架：Bootstrap 5
- 图标：Bootstrap Icons
- 主题：CSS变量 + JavaScript
- HTTP：Fetch API

**第三方集成**
- Jenkins：CI/CD接口
- 禅道：测试用例/缺陷管理
- AI模型：Qwen、DeepSeek、智谱AI等

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Bootstrap 前端 (Port 8082)              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │
│  │ 登录模块 │ │ 任务管理 │ │ AI配置  │ │ 报告查看/集成   │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘  │
│       └──────────┴──────────┴───────────────┘            │
│                         │                                  │
│                    HTTP/REST                               │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                   Flask 后端 (Port 8081)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │用户认证  │ │测试任务   │ │AI模型    │ │集成服务      │  │
│  │JWT       │ │CRUD      │ │管理      │ │Jenkins/Zentao│  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │
│       └────────────┴────────────┴──────────────┘          │
│                         │                                  │
│                    MySQL 数据库                            │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 模块划分

```
PythonProject3/
├── web_platform/                 # Web平台主目录
│   │
│   ├── backend/                # Flask后端
│   │   ├── api/               # API接口模块
│   │   │   ├── auth.py       # 认证接口
│   │   │   ├── tasks.py      # 任务接口
│   │   │   ├── ai_models.py  # AI模型接口
│   │   │   ├── ai_agents.py  # AI智能体接口
│   │   │   ├── jenkins.py    # Jenkins接口
│   │   │   ├── zentao.py     # 禅道接口
│   │   │   ├── reports.py    # 报告接口
│   │   │   └── integrations.py # 集成配置接口
│   │   │
│   │   ├── models/            # 数据模型
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   ├── execution.py
│   │   │   ├── ai_model.py
│   │   │   ├── ai_agent.py
│   │   │   ├── integration.py
│   │   │   └── report.py
│   │   │
│   │   ├── config/            # 配置文件
│   │   │   ├── settings.py   # 配置加载器
│   │   │   ├── database.yaml  # 数据库配置
│   │   │   ├── app.yaml      # 应用配置
│   │   │   └── security.yaml # 安全配置
│   │   │
│   │   ├── utils/             # 工具类
│   │   │   ├── database.py   # 数据库工具
│   │   │   ├── validators.py # 验证器
│   │   │   └── decorators.py # 装饰器
│   │   │
│   │   ├── agents/            # AI智能体模块
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py # 智能体基类
│   │   │   ├── test_agent.py # 测试智能体
│   │   │   └── skill_manager.py # 技能管理器
│   │   │
│   │   └── app.py            # Flask应用入口
│   │
│   ├── frontend/              # Bootstrap前端
│   │   ├── index.html         # 登录页
│   │   ├── dashboard.html     # 首页仪表盘
│   │   ├── tasks.html         # 任务管理
│   │   ├── tasks-create.html  # 创建任务
│   │   ├── tasks-detail.html  # 任务详情
│   │   ├── ai-models.html     # AI模型配置
│   │   ├── ai-agents.html     # AI智能体管理
│   │   ├── integrations.html   # 集成配置
│   │   ├── jenkins.html       # Jenkins管理
│   │   ├── zentao.html        # 禅道管理
│   │   ├── reports.html       # 测试报告
│   │   ├── execution-list.html # 执行记录
│   │   ├── execution-monitor.html # 执行监控
│   │   │
│   │   └── static/
│   │       ├── css/
│   │       │   └── styles.css # 样式文件
│   │       └── js/
│   │           ├── app.js     # API封装
│   │           ├── theme.js   # 主题切换
│   │           ├── user-menu.js # 用户菜单
│   │           └── ai-agents.js # AI智能体前端
│   │
│   ├── scripts/               # 脚本
│   │   └── init_database.py  # 数据库初始化
│   │
│   └── requirements.txt       # Python依赖
│
├── .claude/skills/           # Skill系统定义
│   ├── ai-test-agent/        # AI测试智能体
│   ├── test-expert/          # 测试专家
│   ├── code-helper/          # 代码助手
│   └── report-expert/         # 报告专家
│
└── local_web_login/          # 原有测试服务（保持不动）
```

---

## 2. AI智能体系统

### 2.1 系统概述

企业级AI测试智能体系统，专为自动化测试场景设计，支持多种技能角色切换，提供专业的测试辅助能力。

### 2.2 核心模块

1. **agents模块** - 智能体核心逻辑
   - `base_agent.py` - 智能体基类，提供感知-思考-行动-反思框架
   - `test_agent.py` - 测试专用智能体，集成Skill系统
   - `skill_manager.py` - Skill系统管理器，支持角色切换

2. **web_platform** - Web管理平台
   - `backend/api/ai_agents.py` - AI智能体API接口
   - `frontend/ai-agents.html` - 智能体管理界面
   - `frontend/static/js/ai-agents.js` - 前端交互逻辑

### 2.3 内置技能

#### 测试专家技能 (test_expert)

专门用于自动化测试场景的智能体：
- 页面分析：自动分析网页结构和元素
- 测试用例生成：基于AI自动生成测试步骤
- 测试执行：自动化执行测试用例
- 智能断言：支持多种断言类型
- 报告生成：生成结构化测试报告
- 缺陷分析：智能分析失败原因

#### 代码助手技能 (code_helper)

专注于代码编写和调试：
- 代码生成：编写测试脚本
- 代码调试：帮助修复测试代码问题
- 代码审查：检查测试代码质量
- 架构设计：设计测试框架

#### 报告专家技能 (report_expert)

专注于测试报告生成和分析：
- 报告生成：生成美观的测试报告
- 数据分析：分析测试结果数据
- 趋势分析：分析测试通过率趋势
- 报告优化：提升报告可读性

### 2.4 Skill系统架构

```
Skill系统
├── 角色定义 (role)
│   ├── name: 角色名称
│   ├── description: 角色描述
│   └── capabilities: 能力列表
│
├── 能力验证 (capability)
│   ├── name: 能力名称
│   ├── description: 能力描述
│   ├── validate: 验证函数
│   └── execute: 执行函数
│
└── 权限控制 (permission)
    ├── action: 操作类型
    ├── resource: 资源类型
    └── conditions: 条件限制
```

### 2.5 使用示例

```python
from agents.test_agent import TestAgent

# 创建智能体
agent = TestAgent(initial_skill='test_expert')

# 切换技能
agent.switch_skill('code_helper')

# 检查操作权限
permission = agent.check_action_permission('code_writing')

# 执行操作
result = agent.execute_with_skill_check('page_analysis', url='https://example.com')

# 技能切换示例
agent = TestAgent(initial_skill='test_expert')

# 初始使用测试专家技能
page_result = agent.execute_action('page_analysis', url='https://example.com')

# 切换到代码助手
agent.switch_skill('code_helper')
code_result = agent.execute_action('code_writing', requirement='登录功能测试')

# 切换到报告专家
agent.switch_skill('report_expert')
report_result = agent.execute_action('report_generation', test_data=page_result)
```

### 2.6 API接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/ai-agents | 获取智能体列表 |
| POST | /api/ai-agents | 创建智能体 |
| GET | /api/ai-agents/{id} | 获取智能体详情 |
| DELETE | /api/ai-agents/{id} | 删除智能体 |
| GET | /api/ai-agents/skills | 获取所有可用技能 |
| POST | /api/ai-agents/{id}/skills | 切换智能体技能 |
| GET | /api/ai-agents/{id}/skills/current | 获取当前技能 |
| POST | /api/ai-agents/{id}/execute | 执行操作 |
| GET | /api/ai-agents/{id}/status | 获取状态 |

---

## 3. 项目结构

### 3.1 现有框架复用

```
PythonProject3/
│
├── ✅ 现有自动化测试项目（不动）
│   ├── tests/                      # 测试用例
│   ├── page_objects/              # 页面对象
│   ├── utils/                     # 工具类
│   ├── config/                    # 测试配置
│   └── local_web_login/           # 本地测试服务
│
├── 🆕 web_platform/               # Web平台
│   ├── backend/                   # Flask后端
│   ├── frontend/                  # Bootstrap前端
│   ├── scripts/                   # 脚本
│   └── requirements.txt          # Python依赖
│
└── .claude/skills/              # AI技能定义
```

### 3.2 配置文件

```yaml
# backend/config/database.yaml
development:
  host: "localhost"
  port: 3306
  database: "test_platform"
  username: "root"
  password: "${DB_PASSWORD}"
  charset: "utf8mb4"

# backend/config/app.yaml
development:
  name: "测试平台Web"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8081
  debug: true

# backend/config/security.yaml
development:
  jwt_secret: "your-secret-key"
  jwt_expiration_hours: 24
  max_login_attempts: 5
  lockout_minutes: 30
```

---

## 4. 数据库设计

### 4.1 数据表概览

| 表名 | 说明 |
|------|------|
| user | 用户表 |
| test_task | 测试任务表 |
| test_execution | 执行记录表 |
| ai_model_config | AI模型配置表 |
| ai_agent | AI智能体表 |
| integration_config | 集成配置表 |
| test_report | 测试报告表 |

### 4.2 表结构详情

#### user - 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 用户ID，主键 |
| username | VARCHAR(50) | 用户名，唯一 |
| password | VARCHAR(255) | 密码（bcrypt加密） |
| email | VARCHAR(100) | 邮箱 |
| role | ENUM | 角色（admin/tester/viewer） |
| created_at | DATETIME | 创建时间 |
| last_login | DATETIME | 最后登录时间 |

#### test_task - 测试任务表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 任务ID，主键 |
| name | VARCHAR(200) | 任务名称 |
| description | TEXT | 任务描述 |
| scene | ENUM | 测试场景 |
| test_type | ENUM | 测试类型 |
| target_url | VARCHAR(500) | 目标URL |
| test_data | JSON | 测试数据 |
| ai_model | VARCHAR(50) | AI模型 |
| status | ENUM | 状态 |
| created_by | INT | 创建人 |
| created_at | DATETIME | 创建时间 |
| last_run_at | DATETIME | 最后执行时间 |
| run_count | INT | 执行次数 |

#### test_execution - 执行记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 执行ID，主键 |
| execution_id | VARCHAR(50) | 执行唯一标识 |
| task_id | INT | 关联任务ID |
| executor_id | INT | 执行人 |
| status | ENUM | 状态 |
| start_time | DATETIME | 开始时间 |
| end_time | DATETIME | 结束时间 |
| duration | INT | 执行时长（秒） |
| logs | TEXT | 执行日志 |
| result | JSON | 执行结果 |

#### ai_model_config - AI模型配置表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 配置ID，主键 |
| model_type | VARCHAR(50) | 模型类型 |
| model_name | VARCHAR(100) | 模型名称 |
| api_key | VARCHAR(255) | API密钥 |
| base_url | VARCHAR(500) | API地址 |
| model_id | VARCHAR(100) | 模型ID |
| priority | INT | 优先级 |
| is_active | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |

#### ai_agent - AI智能体表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 智能体ID，主键 |
| name | VARCHAR(100) | 智能体名称 |
| current_skill | VARCHAR(50) | 当前技能 |
| status | ENUM | 状态 |
| created_by | INT | 创建人 |
| created_at | DATETIME | 创建时间 |
| last_active_at | DATETIME | 最后活跃时间 |
| config | JSON | 配置信息 |

#### integration_config - 集成配置表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 配置ID，主键 |
| integration_type | ENUM | 集成类型 |
| name | VARCHAR(100) | 名称 |
| base_url | VARCHAR(500) | 服务地址 |
| credentials | JSON | 认证信息 |
| is_active | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |

---

## 5. 开发指南

### 5.1 添加新的API接口

1. 在 `backend/api/` 目录创建新的API文件
2. 定义Blueprint
3. 实现接口逻辑
4. 在 `app.py` 中注册Blueprint

```python
# backend/api/new_api.py
from flask import Blueprint, request, jsonify
from functools import wraps

new_api_bp = Blueprint('new_api', __name__, url_prefix='/api/new')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': '未授权'}), 401
        return f(*args, **kwargs)
    return decorated_function

@new_api_bp.route('/example', methods=['GET'])
@login_required
def example():
    return jsonify({'code': 200, 'data': {'message': 'Hello'}})
```

### 5.2 添加新的前端页面

1. 在 `frontend/` 创建HTML文件
2. 参考现有页面的导航栏结构
3. 添加到导航菜单

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新页面 - 测试平台</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg">
        <!-- 导航内容 -->
    </nav>
    
    <div class="container-fluid py-4">
        <!-- 页面内容 -->
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/app.js"></script>
</body>
</html>
```

### 5.3 添加新的Skill

1. 在 `.claude/skills/` 创建Skill目录
2. 创建 `SKILL.md` 定义Skill
3. 在 `skill_manager.py` 中注册

---

## 6. 部署说明

### 6.1 开发环境

```bash
# 后端
cd web_platform/backend
pip install -r requirements.txt
python app.py

# 前端
cd web_platform/frontend
python -m http.server 8082
```

### 6.2 生产环境部署

**后端部署**

```bash
# 安装生产依赖
pip install gunicorn

# 使用Gunicorn运行
gunicorn -w 4 -b 0.0.0.0:8081 "app:create_app()" -D
```

**前端部署**

```bash
# 直接部署static目录到Nginx
# 或使用简单的HTTP服务器
python -m http.server 80
```

### 6.3 Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /path/to/frontend;
        index index.html;
    }
    
    # API代理
    location /api {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 未来扩展

- [ ] 新增更多专业技能（性能测试、安全测试）
- [ ] 支持自定义Skill定义
- [ ] 技能学习和进化
- [ ] 多人协作模式
- [ ] 更丰富的Web管理功能
- [ ] 数据库持久化存储

---

*本文档最后更新于2026年5月16日*
