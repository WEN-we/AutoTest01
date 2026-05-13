# 全平台测试平台架构设计

## 一、系统架构

### 1.1 技术栈

**后端**
- 框架：Flask (Python)
- 数据库：MySQL
- 认证：JWT
- 任务队列：Celery (可选，用于异步执行测试)
- 缓存：Redis (可选)

**前端**
- 框架：Vue.js 3
- UI组件：Element Plus
- 状态管理：Pinia
- HTTP客户端：Axios
- 路由：Vue Router 4

**第三方集成**
- Jenkins：CI/CD接口
- 禅道：测试用例/缺陷管理
- AI模型：Qwen、DeepSeek、智谱AI等

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Vue.js 前端 (Port 5173)                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │
│  │ 登录模块 │ │ 任务管理 │ │ AI配置  │ │ 报告查看        │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘  │
│       └──────────┴──────────┴───────────────┘            │
│                         │                                  │
│                    HTTP/REST                               │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                   Flask 后端 (Port 8080)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │用户认证  │ │测试任务   │ │AI模型    │ │集成服务      │  │
│  │JWT       │ │CRUD      │ │管理      │ │Jenkins/Zentao│  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │
│       └────────────┴────────────┴──────────────┘          │
│                         │                                  │
│                    MySQL 数据库                            │
└─────────────────────────────────────────────────────────────┘
```

## 二、数据库设计

### 2.1 用户表 (user)
```sql
CREATE TABLE user (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'tester', 'viewer') DEFAULT 'tester',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    login_attempts INT DEFAULT 0,
    locked_until DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 2.2 测试任务表 (test_task)
```sql
CREATE TABLE test_task (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    task_type ENUM('web', 'api', 'mobile', 'performance', 'ai') NOT NULL,
    target_url VARCHAR(500),
    test_data JSON,
    ai_model VARCHAR(50),
    status ENUM('pending', 'running', 'success', 'failed', 'cancelled') DEFAULT 'pending',
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    started_at DATETIME,
    finished_at DATETIME,
    result_summary JSON,
    FOREIGN KEY (created_by) REFERENCES user(id)
);
```

### 2.3 测试执行记录表 (test_execution)
```sql
CREATE TABLE test_execution (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id INT NOT NULL,
    executor_id INT,
    status ENUM('running', 'success', 'failed', 'skipped') NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    duration INT,
    logs TEXT,
    report_path VARCHAR(255),
    jenkins_build_id VARCHAR(50),
    FOREIGN KEY (task_id) REFERENCES test_task(id),
    FOREIGN KEY (executor_id) REFERENCES user(id)
);
```

### 2.4 AI模型配置表 (ai_model_config)
```sql
CREATE TABLE ai_model_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    api_key VARCHAR(255),
    base_url VARCHAR(255),
    model_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 0,
    config JSON,
    created_by INT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES user(id)
);
```

### 2.5 集成配置表 (integration_config)
```sql
CREATE TABLE integration_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    integration_type ENUM('jenkins', 'zentao', 'gitlab', 'jira') NOT NULL,
    name VARCHAR(100) NOT NULL,
    base_url VARCHAR(255) NOT NULL,
    auth_type ENUM('api_key', 'token', 'basic') DEFAULT 'api_key',
    credentials JSON,
    is_active BOOLEAN DEFAULT TRUE,
    config JSON,
    created_by INT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES user(id)
);
```

### 2.6 测试报告表 (test_report)
```sql
CREATE TABLE test_report (
    id INT PRIMARY KEY AUTO_INCREMENT,
    execution_id INT NOT NULL,
    report_type ENUM('json', 'html', 'allure', 'junit') NOT NULL,
    report_path VARCHAR(255),
    report_data JSON,
    summary JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES test_execution(id)
);
```

## 三、API接口规范

### 3.1 认证接口

#### POST /api/auth/login
用户登录
```json
Request:
{
  "username": "admin",
  "password": "password123"
}

Response:
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    },
    "expires_in": 86400
  }
}
```

#### POST /api/auth/register
用户注册
```json
Request:
{
  "username": "tester",
  "password": "password123",
  "email": "tester@example.com"
}

Response:
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "user_id": 2
  }
}
```

### 3.2 测试任务接口

#### GET /api/tasks
获取任务列表
```json
Query:
- page: int (default: 1)
- page_size: int (default: 20)
- status: string (optional)
- task_type: string (optional)

Response:
{
  "code": 200,
  "data": {
    "tasks": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### POST /api/tasks
创建测试任务
```json
Request:
{
  "name": "登录功能测试",
  "description": "测试用户登录流程",
  "task_type": "web",
  "target_url": "http://example.com/login",
  "test_data": {
    "username": "testuser",
    "password": "testpass"
  },
  "ai_model": "qwen"
}

Response:
{
  "code": 200,
  "data": {
    "task_id": 1
  }
}
```

#### GET /api/tasks/:id
获取任务详情
```json
Response:
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "登录功能测试",
    "description": "测试用户登录流程",
    "task_type": "web",
    "target_url": "http://example.com/login",
    "test_data": {...},
    "ai_model": "qwen",
    "status": "pending",
    "created_by": {
      "id": 1,
      "username": "admin"
    },
    "created_at": "2024-01-01 10:00:00",
    "executions": [...]
  }
}
```

#### PUT /api/tasks/:id
更新任务

#### DELETE /api/tasks/:id
删除任务

#### POST /api/tasks/:id/execute
执行测试任务
```json
Response:
{
  "code": 200,
  "data": {
    "execution_id": 1,
    "status": "running"
  }
}
```

#### POST /api/tasks/:id/stop
停止测试任务

### 3.3 AI模型配置接口

#### GET /api/ai-models
获取AI模型列表

#### POST /api/ai-models
添加AI模型配置
```json
Request:
{
  "model_type": "qwen",
  "model_name": "通义千问",
  "api_key": "sk-xxxxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
  "model_id": "qwen-turbo",
  "priority": 1
}
```

#### PUT /api/ai-models/:id
更新模型配置

#### DELETE /api/ai-models/:id
删除模型配置

#### POST /api/ai-models/:id/test
测试模型连接

### 3.4 Jenkins集成接口

#### GET /api/integrations/jenkins/jobs
获取Jenkins任务列表

#### POST /api/integrations/jenkins/build
触发Jenkins构建
```json
Request:
{
  "job_name": "test-automation",
  "parameters": {
    "TEST_ENV": "staging",
    "TEST_SUITE": "smoke"
  }
}

Response:
{
  "code": 200,
  "data": {
    "build_number": 123,
    "build_url": "http://jenkins/job/test-automation/123"
  }
}
```

#### GET /api/integrations/jenkins/build/:build_id/status
获取构建状态

### 3.5 禅道集成接口

#### GET /api/integrations/zentao/cases
获取禅道测试用例

#### POST /api/integrations/zentao/cases/:id/execute
执行禅道测试用例

#### POST /api/integrations/zentao/bugs
创建禅道Bug
```json
Request:
{
  "product_id": 1,
  "title": "登录失败",
  "steps": "1. 打开登录页\n2. 输入用户名\n3. 点击登录",
  "severity": 3,
  "assigned_to": "dev_user"
}
```

#### GET /api/integrations/zentao/products
获取禅道产品列表

### 3.6 测试报告接口

#### GET /api/reports
获取测试报告列表

#### GET /api/reports/:id
获取报告详情

#### GET /api/reports/:id/download
下载报告文件

## 四、前端页面结构

```
frontend/
├── src/
│   ├── api/                 # API接口
│   │   ├── auth.js
│   │   ├── tasks.js
│   │   ├── aiModels.js
│   │   └── integrations.js
│   │
│   ├── components/          # 公共组件
│   │   ├── Header.vue
│   │   ├── Sidebar.vue
│   │   ├── TaskCard.vue
│   │   └── ReportViewer.vue
│   │
│   ├── views/               # 页面
│   │   ├── Login.vue        # 登录页
│   │   ├── Dashboard.vue    # 首页/仪表盘
│   │   ├── TaskList.vue     # 任务列表
│   │   ├── TaskDetail.vue   # 任务详情
│   │   ├── TaskCreate.vue   # 创建任务
│   │   ├── AIModel.vue      # AI模型配置
│   │   ├── Jenkins.vue      # Jenkins集成
│   │   ├── Zentao.vue       # 禅道集成
│   │   └── Report.vue       # 测试报告
│   │
│   ├── router/              # 路由配置
│   │   └── index.js
│   │
│   ├── stores/              # 状态管理
│   │   ├── auth.js
│   │   └── tasks.js
│   │
│   └── App.vue
│
├── package.json
└── vite.config.js
```

## 五、安全性考虑

### 5.1 认证授权
- JWT token有效期24小时
- Refresh token机制（可选）
- 密码加密存储（bcrypt）
- 登录失败锁定机制

### 5.2 API安全
- 所有API需要认证（除登录注册）
- 敏感信息加密存储
- SQL注入防护
- CORS配置

### 5.3 数据安全
- 敏感数据脱敏
- 日志记录审计
- 数据库备份

## 六、性能优化

### 6.1 后端优化
- 数据库索引优化
- 缓存机制（Redis）
- 异步任务处理（Celery）
- 分页查询

### 6.2 前端优化
- 组件懒加载
- 请求缓存
- 虚拟滚动（长列表）
- 代码分割

## 七、部署方案

### 7.1 开发环境
- 后端：Flask run (Port 8080)
- 前端：npm run dev (Port 5173)
- 数据库：MySQL (Port 3306)

### 7.2 生产环境
- 后端：Gunicorn + Nginx
- 前端：Nginx静态文件服务
- 数据库：MySQL主从复制
- 缓存：Redis集群

## 八、扩展功能

### 8.1 通知系统
- 邮件通知（测试完成、失败告警）
- WebSocket实时推送

### 8.2 定时任务
- 定时执行测试
- 定时同步禅道用例

### 8.3 权限管理
- 角色权限控制
- 操作审计日志

### 8.4 统计分析
- 测试趋势图
- 通过率统计
- 执行时长分析
