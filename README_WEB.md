# 测试平台Web - 使用指南

## 📋 项目概述

本项目为您的自动化测试框架添加了图形化Web界面，支持：

- ✅ 用户认证与权限管理
- ✅ 测试任务配置与执行
- ✅ AI模型配置与管理
- ✅ 测试报告查看
- ✅ Jenkins集成（触发构建、查看状态）
- ✅ 禅道集成（用例同步、Bug管理）
- ✅ 响应式Bootstrap界面

---

## 🎯 项目结构

```
d:\Pthon.Object\PythonProject3\
│
├── ✅ 现有自动化测试项目（不动）
│   ├── tests/                      # 测试用例
│   ├── page_objects/              # 页面对象
│   ├── utils/                     # 工具类
│   ├── config/                    # 测试配置
│   └── local_web_login/           # 本地测试服务
│
├── 🆕 web_platform/               # Web平台
│   │
│   ├── backend/                   # Flask后端
│   │   ├── api/                   # API接口
│   │   │   ├── auth.py           # 认证接口
│   │   │   ├── tasks.py          # 任务接口
│   │   │   ├── ai_models.py      # AI模型接口
│   │   │   ├── jenkins.py        # Jenkins接口
│   │   │   ├── zentao.py         # 禅道接口
│   │   │   ├── reports.py        # 报告接口
│   │   │   └── integrations.py  # 集成配置接口
│   │   │
│   │   ├── models/               # 数据模型
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   ├── execution.py
│   │   │   ├── ai_model.py
│   │   │   ├── integration.py
│   │   │   └── report.py
│   │   │
│   │   ├── config/               # 🎯 配置文件（与代码分离）
│   │   │   ├── settings.py       # 配置加载器
│   │   │   ├── database.yaml     # 数据库配置
│   │   │   ├── app.yaml         # 应用配置
│   │   │   ├── security.yaml    # 安全配置
│   │   │   └── integrations.yaml # 集成配置模板
│   │   │
│   │   ├── utils/                # 工具类
│   │   │   ├── database.py       # 数据库工具
│   │   │   ├── validators.py     # 验证器
│   │   │   └── decorators.py     # 装饰器
│   │   │
│   │   └── app.py               # Flask应用入口
│   │
│   ├── frontend/                  # Bootstrap前端
│   │   ├── index.html           # 登录页
│   │   ├── dashboard.html        # 首页
│   │   ├── tasks.html           # 任务管理
│   │   ├── ai-models.html       # AI模型配置
│   │   ├── integrations.html    # 集成配置
│   │   ├── jenkins.html         # Jenkins
│   │   ├── zentao.html          # 禅道
│   │   ├── reports.html         # 测试报告
│   │   │
│   │   └── static/
│   │       ├── css/styles.css   # 样式
│   │       └── js/app.js       # API调用封装
│   │
│   ├── scripts/                  # 脚本
│   │   └── init_database.py    # 数据库初始化
│   │
│   └── requirements.txt         # Python依赖
│
└── README_WEB.md               # 本文档
```

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
cd d:\Pthon.Object\PythonProject3\web_platform
pip install -r requirements.txt
```

### 2️⃣ 配置数据库

编辑配置文件 `backend/config/database.yaml`：

```yaml
development:
  host: "localhost"
  port: 3306
  database: "test_platform"      # 新数据库名
  username: "root"
  password: "${DB_PASSWORD}"              # 修改为您的密码
  charset: "utf8mb4"
```

### 3️⃣ 初始化数据库

```bash
cd backend
python scripts/init_database.py
```

这将创建：
- ✅ 新数据库 `test_platform`
- ✅ 所有数据表（6个表）
- ✅ 默认管理员账户

### 4️⃣ 启动后端服务

```bash
cd backend
python app.py
```

后端运行在：**http://127.0.0.1:8081**

### 5️⃣ 启动前端

有两种方式：

#### 方式A：直接打开HTML文件（推荐）

```bash
# 直接在浏览器中打开
frontend/index.html
```

#### 方式B：使用Python简单服务器

```bash
cd frontend
python -m http.server 8082
```

前端访问：**http://localhost:8082**

---

## 📝 默认账户

- **用户名**: `admin`
- **密码**: `change_me_in_production`

---

## 🎨 界面功能

### 1️⃣ 首页仪表盘
- 测试任务统计
- 最近任务列表
- 快速操作入口

### 2️⃣ 测试任务管理
- 创建/编辑/删除任务
- 支持多种测试类型：
  - Web测试
  - API测试
  - 移动端测试
  - 性能测试
  - AI测试
- 任务执行和状态监控

### 3️⃣ AI模型配置
- 添加AI模型（通义千问、DeepSeek、智谱AI等）
- 测试模型连接
- 管理多个模型配置

### 4️⃣ Jenkins集成
- 查看Jenkins任务列表
- 触发构建
- 查看构建状态和日志

**配置Jenkins：**
1. 进入"集成配置"
2. 添加Jenkins配置：
   - 名称：Jenkins
   - URL：http://jenkins-server:8080
   - 用户名：jenkins用户
   - API Token：jenkins的API Token

### 5️⃣ 禅道集成
- 查看产品和测试用例
- 执行测试用例
- 创建Bug
- 同步测试用例

**配置禅道：**
1. 进入"集成配置"
2. 添加禅道配置：
   - 名称：禅道
   - URL：http://zentao-server/zentao
   - 账户：禅道账户
   - 密码：禅道密码

### 6️⃣ 测试报告
- 查看历史测试报告
- 报告详情查看

---

## 🔧 API接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| GET | `/api/auth/profile` | 获取用户信息 |

### 任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 获取任务列表 |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks/:id` | 获取任务详情 |
| PUT | `/api/tasks/:id` | 更新任务 |
| DELETE | `/api/tasks/:id` | 删除任务 |
| POST | `/api/tasks/:id/execute` | 执行任务 |
| POST | `/api/tasks/:id/stop` | 停止任务 |
| GET | `/api/tasks/statistics` | 获取统计 |

### AI模型接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ai-models` | 获取模型列表 |
| POST | `/api/ai-models` | 添加模型 |
| PUT | `/api/ai-models/:id` | 更新模型 |
| DELETE | `/api/ai-models/:id` | 删除模型 |
| POST | `/api/ai-models/:id/test` | 测试连接 |

### Jenkins接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/integrations/jenkins/status` | 检查连接 |
| GET | `/api/integrations/jenkins/jobs` | 获取任务列表 |
| POST | `/api/integrations/jenkins/build` | 触发构建 |
| GET | `/api/integrations/jenkins/build/:job/:id` | 构建状态 |

### 禅道接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/integrations/zentao/status` | 检查连接 |
| GET | `/api/integrations/zentao/products` | 获取产品 |
| GET | `/api/integrations/zentao/cases` | 获取用例 |
| POST | `/api/integrations/zentao/bugs` | 创建Bug |
| POST | `/api/integrations/zentao/sync/cases` | 同步用例 |

---

## ⚙️ 配置说明

### 数据库配置

文件：`backend/config/database.yaml`

```yaml
development:
  host: "localhost"
  port: 3306
  database: "test_platform"
  username: "root"
  password: "${DB_PASSWORD}"
```

### 应用配置

文件：`backend/config/app.yaml`

```yaml
development:
  name: "测试平台Web"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8081              # 避免与local_web_login冲突
  debug: true
```

### 安全配置

文件：`backend/config/security.yaml`

```yaml
development:
  jwt_secret: "your-secret-key"
  jwt_expiration_hours: 24
  max_login_attempts: 5
  lockout_minutes: 30
```

---

## 🔄 与现有框架集成

### 复用AI配置

您的现有AI配置在 `config/ai_config.yaml`，可以在Web平台中：
1. 在"AI模型配置"页面添加模型
2. 或直接在数据库的 `ai_model_config` 表中插入

### 复用测试用例

您的现有测试用例在 `tests/` 目录，Web平台的任务执行可以：
1. 调用现有的测试脚本
2. 复用 `page_objects/` 中的页面对象

---

## 📁 数据表结构

### user - 用户表
```sql
- id: 用户ID
- username: 用户名
- password: 密码（bcrypt加密）
- email: 邮箱
- role: 角色（admin/tester/viewer）
- created_at: 创建时间
- last_login: 最后登录时间
```

### test_task - 测试任务表
```sql
- id: 任务ID
- name: 任务名称
- task_type: 任务类型
- target_url: 目标URL
- test_data: 测试数据（JSON）
- ai_model: AI模型
- status: 状态
- created_by: 创建人
- created_at: 创建时间
```

### test_execution - 执行记录表
```sql
- id: 执行ID
- task_id: 关联任务ID
- executor_id: 执行人
- status: 状态
- start_time: 开始时间
- end_time: 结束时间
- duration: 执行时长
- logs: 执行日志
```

### ai_model_config - AI模型配置表
```sql
- id: 配置ID
- model_type: 模型类型
- model_name: 模型名称
- api_key: API密钥
- base_url: API地址
- model_id: 模型ID
- priority: 优先级
```

### integration_config - 集成配置表
```sql
- id: 配置ID
- integration_type: 集成类型
- name: 名称
- base_url: 服务地址
- credentials: 认证信息（JSON）
- is_active: 是否启用
```

---

## ❓ 常见问题

### 1. 数据库连接失败

**检查MySQL服务是否启动**
```bash
net start mysql
```

**检查配置是否正确**
- 编辑 `backend/config/database.yaml`
- 确认用户名密码正确

### 2. 前端无法访问后端

**跨域问题**
后端已配置CORS，允许所有来源访问。

**检查端口**
- 后端运行在：8081
- 前端默认访问：8082
- 确保端口不冲突

### 3. Jenkins连接失败

**检查配置**
1. 确认Jenkins地址可访问
2. 确认用户名和API Token正确
3. API Token获取：在Jenkins中 → 用户 → 配置 → API Token

### 4. 禅道连接失败

**检查配置**
1. 确认禅道地址可访问
2. 确认账户密码正确
3. 确认API权限开启

---

## 🚀 生产部署

### 后端部署

```bash
# 安装生产依赖
pip install gunicorn

# 使用Gunicorn运行
gunicorn -w 4 -b 0.0.0.0:8081 "app:create_app()" -D
```

### 前端部署

```bash
# 直接部署static目录到Nginx
# 或使用简单的HTTP服务器
python -m http.server 80
```

---

## 📞 联系方式

如有问题，请检查：
- 系统日志输出
- 浏览器控制台错误
- 后端控制台错误

---

## 📄 许可证

本项目仅供学习交流使用。
