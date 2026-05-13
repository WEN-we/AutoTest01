# 全平台测试平台 - 图形化前后端实现

## 项目概述

本项目为您现有的Python自动化测试框架添加了完整的图形化前后端界面，支持：

- ✅ 用户认证与权限管理
- ✅ 测试任务配置与执行
- ✅ AI模型配置与测试
- ✅ 测试报告查看
- ✅ Jenkins集成
- ✅ 禅道集成
- ✅ 实时任务监控

## 技术栈

### 后端
- **框架**: Flask (Python)
- **数据库**: MySQL
- **认证**: JWT
- **密码加密**: bcrypt

### 前端
- **框架**: Vue.js 3
- **UI组件**: Element Plus
- **状态管理**: Pinia
- **HTTP客户端**: Axios
- **构建工具**: Vite

## 快速开始

### 1. 环境要求

- Python 3.8+
- Node.js 16+
- MySQL 5.7+

### 2. 后端设置

#### 安装Python依赖

```bash
cd d:\Pthon.Object\PythonProject3
pip install -r requirements.txt
```

#### 初始化数据库

```bash
cd local_web_login
python init_database.py
```

这将：
- 创建数据库和所有数据表
- 创建默认管理员账户（用户名: `admin`，密码: `change_me_in_production`）
- 添加示例测试任务数据

#### 启动后端服务

```bash
cd local_web_login
python backend_server_integrated.py
```

后端服务运行在: http://127.0.0.1:8080

### 3. 前端设置

#### 安装Node.js依赖

```bash
cd frontend
npm install
```

#### 启动前端开发服务器

```bash
npm run dev
```

前端服务运行在: http://localhost:5173

### 4. 访问系统

1. 打开浏览器访问: http://localhost:5173
2. 使用管理员账户登录:
   - 用户名: `admin`
   - 密码: `change_me_in_production`

## 功能模块

### 1. 首页仪表盘

访问: http://localhost:5173/

功能：
- 查看测试统计概览
- 查看最近任务列表
- 测试趋势图表
- 快速操作入口

### 2. 测试任务管理

访问: http://localhost:5173/tasks

功能：
- 查看所有测试任务
- 按类型和状态筛选任务
- 创建新的测试任务
- 执行任务
- 查看任务详情和执行日志

#### 创建任务示例

```json
{
  "name": "登录功能测试",
  "description": "测试用户登录流程",
  "task_type": "web",
  "target_url": "http://example.com/login",
  "test_data": {
    "username": "testuser",
    "password": "password123"
  },
  "ai_model": "qwen"
}
```

### 3. AI模型配置

访问: http://localhost:5173/ai-models

功能：
- 添加AI模型配置
- 测试模型连接
- 管理多个AI模型
- 支持的模型:
  - 通义千问 (Qwen)
  - DeepSeek
  - 智谱AI (GLM)
  - 豆包
  - OpenAI GPT

#### 添加模型示例

```json
{
  "model_type": "qwen",
  "model_name": "通义千问",
  "api_key": "your-api-key-here",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
  "model_id": "qwen-turbo",
  "priority": 1
}
```

### 4. Jenkins集成

访问: http://localhost:5173/jenkins

功能：
- 查看Jenkins任务列表
- 触发构建任务
- 查看构建历史
- 监控构建状态

#### 配置Jenkins

在 "集成配置" 页面添加Jenkins配置：

```json
{
  "integration_type": "jenkins",
  "name": "测试Jenkins",
  "base_url": "http://jenkins-server:8080",
  "credentials": {
    "username": "jenkins-user",
    "api_token": "jenkins-api-token"
  }
}
```

### 5. 禅道集成

访问: http://localhost:5173/zentao

功能：
- 查看产品列表
- 查看测试用例
- 执行测试用例
- 创建Bug
- 同步测试用例

#### 配置禅道

在 "集成配置" 页面添加禅道配置：

```json
{
  "integration_type": "zentao",
  "name": "测试禅道",
  "base_url": "http://zentao-server/zentao",
  "credentials": {
    "account": "zentao-user",
    "password": "zentao-password"
  }
}
```

### 6. 测试报告

访问: http://localhost:5173/reports

功能：
- 查看所有测试报告
- 按时间和类型筛选
- 查看报告详情
- 下载报告文件

## API文档

### 认证接口

#### POST /api/auth/login
用户登录

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "change_me_in_production"}'
```

响应：
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com"
    }
  }
}
```

#### POST /api/auth/register
用户注册

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "tester", "password": "password123", "email": "tester@example.com"}'
```

### 测试任务接口

#### GET /api/tasks
获取任务列表

```bash
curl -X GET "http://localhost:8080/api/tasks?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST /api/tasks
创建测试任务

```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "新任务", "task_type": "web", "target_url": "http://example.com"}'
```

#### POST /api/tasks/:id/execute
执行测试任务

```bash
curl -X POST http://localhost:8080/api/tasks/1/execute \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### AI模型接口

#### GET /api/ai-models
获取AI模型列表

```bash
curl -X GET http://localhost:8080/api/ai-models \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST /api/ai-models/:id/test
测试模型连接

```bash
curl -X POST http://localhost:8080/api/ai-models/1/test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Jenkins接口

#### GET /api/integrations/jenkins/jobs
获取Jenkins任务列表

```bash
curl -X GET http://localhost:8080/api/integrations/jenkins/jobs \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST /api/integrations/jenkins/build
触发构建

```bash
curl -X POST http://localhost:8080/api/integrations/jenkins/build \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_name": "test-job", "parameters": {"ENV": "test"}}'
```

### 禅道接口

#### GET /api/integrations/zentao/products
获取产品列表

```bash
curl -X GET http://localhost:8080/api/integrations/zentao/products \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST /api/integrations/zentao/bugs
创建Bug

```bash
curl -X POST http://localhost:8080/api/integrations/zentao/bugs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Bug标题", "severity": 3, "steps": "复现步骤"}'
```

## 项目结构

```
PythonProject3/
├── local_web_login/              # 后端代码
│   ├── backend_server.py        # Flask后端（基础版）
│   ├── backend_server_integrated.py  # Flask后端（完整版）
│   ├── tasks_api.py             # 测试任务API
│   ├── ai_models_api.py         # AI模型API
│   ├── integrations_api.py      # 集成配置API
│   ├── jenkins_api.py           # Jenkins API
│   ├── zentao_api.py            # 禅道 API
│   └── init_database.py         # 数据库初始化
│
├── frontend/                     # 前端代码
│   ├── src/
│   │   ├── api/                 # API调用模块
│   │   ├── stores/              # 状态管理
│   │   ├── views/               # 页面组件
│   │   ├── router/              # 路由配置
│   │   ├── utils/               # 工具函数
│   │   ├── App.vue              # 根组件
│   │   └── main.js              # 入口文件
│   ├── package.json             # 依赖配置
│   ├── vite.config.js           # Vite配置
│   └── index.html               # HTML模板
│
├── docs/                         # 文档
│   └── ARCHITECTURE.md          # 系统架构文档
│
└── config/                       # 配置文件
    ├── ai_config.yaml           # AI配置
    └── ...                      # 其他配置
```

## 数据库表结构

### user
用户表
- id: 用户ID
- username: 用户名
- password: 密码（bcrypt加密）
- email: 邮箱
- role: 角色（admin/tester/viewer）
- created_at: 创建时间
- last_login: 最后登录时间

### test_task
测试任务表
- id: 任务ID
- name: 任务名称
- description: 任务描述
- task_type: 任务类型（web/api/mobile/performance/ai）
- target_url: 目标URL
- test_data: 测试数据（JSON）
- ai_model: AI模型类型
- status: 状态（pending/running/success/failed）
- created_by: 创建人
- created_at: 创建时间

### test_execution
测试执行记录表
- id: 执行ID
- task_id: 关联任务ID
- executor_id: 执行人
- status: 状态
- start_time: 开始时间
- end_time: 结束时间
- duration: 执行时长
- logs: 执行日志

### ai_model_config
AI模型配置表
- id: 配置ID
- model_type: 模型类型
- model_name: 模型名称
- api_key: API密钥
- base_url: API地址
- model_id: 模型ID
- priority: 优先级

### integration_config
集成配置表
- id: 配置ID
- integration_type: 集成类型（jenkins/zentao）
- name: 名称
- base_url: 服务地址
- credentials: 认证信息（JSON）
- is_active: 是否启用

## 常见问题

### 1. 数据库连接失败

检查MySQL服务是否启动，并确认数据库配置正确：

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("DB_PASSWORD", ""),  # 修改为你的密码
    "database": "test_auto",
    "charset": "utf8mb4"
}
```

### 2. 前端无法访问后端API

检查Vite代理配置是否正确（vite.config.js）：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8080',
    changeOrigin: true
  }
}
```

### 3. AI模型连接失败

1. 确认API密钥正确配置
2. 检查网络连接
3. 确认API地址正确
4. 查看后端日志获取详细错误信息

### 4. Jenkins/禅道集成失败

1. 确认服务地址可访问
2. 检查认证凭证是否正确
3. 确认API权限是否足够

## 开发指南

### 添加新的API接口

1. 在 `local_web_login/` 目录下创建新的API文件
2. 定义Blueprint
3. 实现接口逻辑
4. 在 `backend_server_integrated.py` 中注册Blueprint

示例：

```python
# local_web_login/new_api.py
from flask import Blueprint, request, jsonify
from local_web_login.backend_server import login_required, success_response

new_api_bp = Blueprint('new_api', __name__, url_prefix='/api/new')

@new_api_bp.route('/example', methods=['GET'])
@login_required
def example():
    return jsonify(success_response(data={"message": "Hello"}))
```

### 添加新的前端页面

1. 在 `frontend/src/views/` 创建Vue组件
2. 在 `frontend/src/router/index.js` 添加路由
3. 在侧边栏菜单添加导航入口

示例：

```vue
<template>
  <div class="new-page">
    <h1>新页面</h1>
  </div>
</template>

<script setup>
// 页面逻辑
</script>
```

## 部署说明

### 生产环境部署

#### 后端部署

1. 使用Gunicorn替代开发服务器：

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 backend_server_integrated:app
```

2. 配置Nginx反向代理

#### 前端部署

1. 构建生产版本：

```bash
npm run build
```

2. 将 `dist` 目录部署到Nginx

## 联系方式

如有问题，请查看：
- 系统架构文档: `docs/ARCHITECTURE.md`
- API文档: 本README的API部分

## 许可证

本项目仅供学习交流使用。
