<div align="center">
  
  # 企业级电商全平台自动化测试框架
  
  ✨ 基于 Python + Pytest 的全平台自动化测试解决方案 ✨
  
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
  [![TestFramework](https://img.shields.io/badge/TestFramework-Pytest-green.svg)](https://docs.pytest.org/)
  [![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Android%20%7C%20iOS%20%7C%20HarmonyOS%20%7C%20Windows%20%7C%20Linux-orange.svg)](README.md)
  [![CI](https://img.shields.io/badge/CI-GitHub%20Actions%20%7C%20Jenkins-red.svg)](README.md)
  [![Report](https://img.shields.io/badge/Report-Allure-green.svg)](https://docs.qameta.io/allure/)
  
  [English](README_en.md) | 简体中文
</div>

---

## 项目介绍

本项目是一套**企业级电商全平台自动化测试通用框架**，基于 Python + Pytest 构建，覆盖 Web 端、接口、Android APP、iOS APP、Windows 桌面、Linux 桌面及 Linux 服务端测试场景，集成 Allure 可视化报告与 GitHub Actions CI/CD 持续集成，实现多环境隔离、数据与用例分离、工具类高度复用，适配各类电商业务场景，可直接复用并快速适配自身业务需求，落地全流程自动化测试。

---

## 核心特性

| 特性 | 描述 |
| :--- | :--- |
| ✅ 全平台覆盖 | Web UI + 接口 + Android APP + iOS APP + Windows 桌面 + Linux 桌面 + Linux 服务端 + HarmonyOS（鸿蒙） |
| ✅ 多环境隔离 | 支持开发、测试、生产环境一键切换，避免环境干扰 |
| ✅ 数据驱动测试 | 测试数据与用例分离，支持 YAML 格式，便于维护与扩展 |
| ✅ 统一驱动管理 | 全平台驱动自动初始化、自动销毁，降低维护成本 |
| ✅ 可视化报告 | 集成 Allure Report，清晰展示测试结果、用例覆盖率及失败原因 |
| ✅ 持续集成 | 支持 GitHub Actions 自动触发测试、生成报告，适配 Jenkins 流水线 |
| ✅ 高可复用性 | 工具类与业务逻辑解耦，页面对象层（PO模式）统一管理，适配业务快速迭代 |
| ✅ 灵活执行 | 支持按模块、按类型执行用例，支持冒烟测试、回归测试，支持失败重跑 |

---

## 技术栈

| 测试类型 | 核心技术 |
| :--- | :--- |
| 测试框架 | pytest/unittest |
| 接口自动化 | requests + pytest |
| Web UI 自动化(传统) | unittest + selenium |
| Web UI 自动化(现代) | Playwright（支持Chrome/Firefox/WebKit） |
| Android APP 自动化 | Appium + ADB（支持真机/模拟器） |
| iOS APP 自动化 | Appium + XCUITest |
| Windows 桌面自动化 | PyAutoGUI |
| Linux 桌面自动化 | PyAutoGUI |
| Linux 服务端自动化 | Paramiko（SSH远程操作） |
| HarmonyOS 鸿蒙自动化 | Appium + UiAutomator2 + HDC（鸿蒙调试工具） |
| 报告工具 | Allure Report |
| 配置管理 | PyYAML + python-dotenv |
| 日志工具 | loguru |
| CI/CD | GitHub Actions/Jenkins |

---

## 目录结构说明

核心采用分层架构设计，目录清晰、职责明确，便于团队协作与维护：

```
AutoTest01/                     # repo 根（默认分支: master）
├─ .github/
│  └─ workflows/                # GitHub Actions 工作流（CI/CD 配置）
├─ .gitignore
├─ .env.example                 # 环境变量配置示例（复制为 .env 后填写实际值）
├─ README.md
├─ README_en.md
├─ Run_CI.bat                   # 一键运行 CI（Windows batch）
├─ pytest.ini                   # pytest 配置
├─ requirements.txt
├─ requirements-ci.txt
├─ run_all_smoke.py             # 全平台冒烟测试一键运行脚本
├─ bat/
│  └─ run_allure.bat            # Allure 报告相关 batch 脚本
├─ docs/                        # 项目文档
├─ agents/                      # AI Agent 智能体模块
├─ ai_agents/                   # AI Agent 核心模块
├─ ai_page_objects/
│  ├─ __init__.py
│  ├─ base/                     # AI 相关 page object 基础
│  └─ web/                      # AI web page objects
├─ page_objects/
│  ├─ __init__.py
│  ├─ android/
│  ├─ base/
│  ├─ harmony/
│  ├─ ios/
│  ├─ linux_gui/
│  ├─ web/
│  └─ windows/                  # 各平台的 page object 目录（按平台分）
├─ service_objects/
│  ├─ __init__.py
│  ├─ base_service.py
│  └─ linux_service.py          # 服务层封装（例如启动/管理服务）
├─ config/
│  ├─ ai_config.yaml
│  ├─ app_config.yaml
│  ├─ env_config.yaml
│  ├─ harmony_config.yaml
│  ├─ linux_config.yaml
│  ├─ perf_config.yaml
│  ├─ ui_config.yaml
│  └─ windows_config.yaml       # 各类运行/环境/平台配置文件（yaml）
├─ local_web_login/             # 本地登录后端服务（示例/测试用）
├─ test_data/
│  ├─ ai/
│  ├─ api/
│  └─ ui/                       # 测试用的数据（按类别）
├─ tests/
│  ├─ __init__.py
│  ├─ conftest.py               # pytest 固件/夹具
│  ├─ test_ai/
│  ├─ test_android/
│  ├─ test_api/
│  ├─ test_ecommerce/            # 电商平台测试用例（UI + API）
│  ├─ test_harmony/
│  ├─ test_ios/
│  ├─ test_linux/
│  ├─ test_performance/
│  ├─ test_selenium/
│  ├─ test_service/
│  ├─ test_smoke/
│  ├─ test_ui/
│  ├─ test_whitebox/
│  └─ test_windows/             # 各类测试集（按平台/类型分）
├─ tools/
│  └─ get_mouse_pos.py          # 小工具脚本
├─ utils/
│  ├─ __init__.py
│  ├─ drivers/                  # 驱动相关工具/封装
│  └─ tools/                    # 工具集合
└─ web_platform/                # 图形化测试管理平台（Flask 后端 + 前端）
   ├─ backend/
   ├─ frontend/
   └─ scripts/                  # 平台运维脚本（重置密码等）
```

---

## 环境准备

### 1. 克隆项目
```bash
git clone https://github.com/WEN-we/AutoTest01.git
cd AutoTest01
```

### 2. 创建并激活虚拟环境（推荐）

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux/Mac
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装项目依赖（Python3.11 稳定兼容）
```bash
pip install -r requirements.txt
```

### 4. 安装 Playwright 浏览器（Web UI 自动化必备）
```bash
playwright install
```

---

### 补充说明

- **Android APP 测试**：需提前配置 ADB 环境、安装 Appium 服务
- **iOS APP 测试**：需配置 Xcode 环境、模拟器 / 真机调试权限
- **Linux 服务端测试**：需提前获取服务器 SSH 连接信息（IP、端口、账号密码）

---

## 本地执行测试

### 1. 一键运行全平台冒烟测试（推荐，快速验证核心流程）
```bash
python run_all_smoke.py
```

### 2. 执行所有测试用例
```bash
pytest --run-all
```

### 3. 传统框架 Web 测试（Selenium + Unittest）
```bash
# 运行 Selenium 用例
python -m unittest discover tests/test_selenium/
```

### 4. 按测试类型执行指定用例
```bash
# 只执行接口用例
pytest -m api

# 只执行Web UI用例
pytest -m ui

# 只执行冒烟用例（核心流程，快速验证）
pytest -m smoke

# 只执行Android APP用例
pytest tests/test_android/

# 只执行Linux服务端用例
pytest tests/test_service/

# 只执行Windows桌面用例
pytest tests/test_windows/
```

---

## 端能力启用开关（重要）

为避免在未安装对应环境时“收集测试阶段就报错”，项目默认只收集 **API + UI** 两类基础用例；其余端请按需开启：

### 临时全开（可能需要额外环境/驱动）
```bash
pytest --run-all
```

### 按端启用（推荐）：通过环境变量控制收集

| 环境变量 | 作用 |
| :--- | :--- |
| `ENABLE_ANDROID=1` | 收集 `tests/test_android/` |
| `ENABLE_IOS=1` | 收集 `tests/test_ios/` |
| `ENABLE_HARMONY=1` | 收集 `tests/test_harmony/` |
| `ENABLE_WINDOWS=1` | 收集 `tests/test_windows/`（非 Windows 平台时） |
| `ENABLE_LINUX=1` | 收集 `tests/test_linux/`（非 Linux 平台时） |
| `ENABLE_SERVICE=1` | 收集 `tests/test_service/` |

### 示例
```bash
set ENABLE_ANDROID=1
pytest -m android
```

### 5. 执行指定模块用例（如订单模块接口用例）
```bash
pytest tests/test_api/test_user_api.py -v
```

### 6. 查看 Allure 可视化报告
```bash
allure serve reports/allure-results
```

---
## CI/CD 配置（自动化集成）

### GitHub Actions 配置

- **将项目推送到 GitHub 仓库**
- **工作流文件**：`.github/workflows/pre-release-test.yml`（发布前验证）和 `.github/workflows/post-release-validation.yml`（发布后验证）
- **开启 GitHub Pages**：设置 → Pages → 源选择 gh-pages 分支
- **触发条件**：每次 push 到 master 分支或提交 PR 时，自动执行测试、生成 Allure 报告并上传
- **测试内容**：Web UI 测试、API 测试、AI 自主测试、性能监控

#### 必需的 GitHub Secrets

工作流运行前需在仓库「设置 → Secrets and variables → Actions」中配置以下 Secret：

| Secret 名称 | 用途 | 说明 |
| --- | --- | --- |
| `MYSQL_CI_PASSWORD` | MySQL 服务容器 root 密码 | CI 中 MySQL service container 与数据库初始化脚本（init_database.py、测试用户插入脚本）均通过此 Secret 获取密码，必须配置否则 CI 数据库相关步骤将失败 |

### Jenkins 配置（可选）

执行脚本：`Run_CI.bat`（Windows），可配置定时任务、自动拉取代码、触发测试流程

---

## GitHub Actions（Allure 统一报告）

项目提供两个工作流：

- **`pre-release-test.yml`**（发布前验证）：
  - Web 端 UI 测试（Playwright + 本地登录服务）
  - Web 端 API 测试
  - AI 自主测试（需配置 API 密钥，无密钥自动跳过）
  - 合并生成 Allure 报告并发布到 GitHub Pages

- **`post-release-validation.yml`**（发布后验证）：
  - Web 端生产环境验证
  - API 生产环境验证
  - 服务可用性检查
  - 性能监控（Locust 压测）
  - 生成发布后验证报告

### 关于 iOS/Android/真实设备说明

- GitHub Hosted Runner **无法直接访问你的真机**。如果你要跑真机/内网环境，请改用 **self-hosted runner**。
- iOS/Android/Windows/Linux 端测试需要对应环境（Appium/Xcode/ADB 等），默认不收集，通过 `ENABLE_XXX=1` 环境变量启用

---

## 业务适配说明（快速适配自身电商业务）

| 适配类型 | 操作说明 |
| :--- | :--- |
| 配置适配 | 修改 `config/` 目录下对应配置文件，更新环境地址、账号密码、设备信息等 |
| Web 端 | 修改 `ui_config.yaml`（浏览器、超时时间等） |
| APP 端 | 修改 `app_config.yaml`（包名、启动页、设备名称等） |
| Linux 端 | 修改 `linux_config.yaml`（SSH 连接信息、服务检查命令等） |
| 数据适配 | 修改 `test_data/` 下的接口 / UI 测试数据，替换为自身业务数据 |
| UI 适配 | 修改 `page_objects/` 下的元素定位器（XPath/CSS），适配自身前端页面 |
| 用例适配 | 基于 `tests/` 下的用例模板，新增 / 修改用例，覆盖自身电商业务场景（如商品下单、支付、退款等） |
| 多端适配 | Android/iOS/Windows/Linux 端无需修改核心代码，仅需调整对应配置文件即可运行 |

---

## 注意事项

- **测试环境需保持稳定**，避免环境差异（如前端页面更新、接口地址变更）导致用例失败
- **敏感信息**（如数据库密码、接口 token、服务器账号密码）需放在 `.env` 文件中，禁止提交到代码仓库
- **用例编写遵循 “单一职责” 原则**，每个用例只验证一个业务场景，便于问题定位
- **工具类禁止写入业务逻辑**，保持通用性，便于跨项目复用
- **每次提交代码前**，需本地执行冒烟用例，确保核心业务流程正常，避免影响整体测试体系
- **执行 APP / 桌面端测试时**，需确保设备（真机 / 模拟器 / 桌面）处于可用状态，避免驱动启动失败

---

## 适用场景

- **电商 Web 平台自动化测试**（商城前端、后台管理系统）
- **电商 APP 自动化测试**（Android/iOS 真机 / 模拟器）
- **Windows 桌面电商相关软件测试**
- **Linux 服务端监控、接口测试、部署验证**
- **电商核心流程冒烟测试、回归测试、系统测试**
- **企业级 CI/CD 自动化集成，实现测试流程自动化**

---

## 核心优化&亮点

1. **全平台覆盖**：明确覆盖所有测试端，突出项目竞争力
2. **核心特性模块**：清晰展示全平台优势，适配面试/毕设场景
3. **技术栈表格化**：各端测试对应技术一目了然，更规范
4. **目录结构完整**：补充全平台相关文件，与项目实际基本匹配
5. **执行命令详细**：补充各端单独执行命令，方便本地调试
6. **适配说明全面**：环境准备、业务适配、注意事项均补充全平台相关说明
7. **排版统一规范**：使用 `---` 分隔模块，代码块高亮，关键路径用反引号标注
8. **信息完整保留**：保留原文核心信息，不新增冗余内容

---

## 结束语

感谢您对本项目的关注与支持！如果您有任何问题或建议，欢迎在 GitHub 上提交 Issue 或 Pull Request。

开源不易，希望这个项目能够为您的自动化测试工作带来帮助。让我们一起构建更高效、更可靠的测试框架！

---

<div align="center">
  <h3>🌟 企业级电商全平台自动化测试框架 🌟</h3>
  <p>让自动化测试更简单、更高效</p>
</div>