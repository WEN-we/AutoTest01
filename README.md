# 企业级电商全平台自动化测试框架
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![TestFramework](https://img.shields.io/badge/TestFramework-Pytest-green.svg)](https://docs.pytest.org/)
[![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Android%20%7C%20iOS%20%7C%20HarmonyOS%20%7C%20Windows%20%7C%20Linux-orange.svg)](README.md)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions%20%7C%20Jenkins-red.svg)](README.md)
[![Report](https://img.shields.io/badge/Report-Allure-green.svg)](https://docs.qameta.io/allure/)

---

## 项目介绍
本项目是一套**企业级电商全平台自动化测试通用框架**，基于 Python + Pytest 构建，覆盖 Web 端、接口、Android APP、iOS APP、Windows 桌面、Linux 桌面及 Linux 服务端测试场景，集成 Allure 可视化报告与 GitHub Actions CI/CD 持续集成，实现多环境隔离、数据与用例分离、工具类高度复用，适配各类电商业务场景，可直接复用并快速适配自身业务需求，落地全流程自动化测试。

---

## 核心特性
✅ 全平台覆盖：Web UI + 接口 + Android APP + iOS APP + Windows 桌面 + Linux 桌面 + Linux 服务端  + HarmonyOS（鸿蒙）

✅ 多环境隔离：支持开发、测试、生产环境一键切换，避免环境干扰  
✅ 数据驱动测试：测试数据与用例分离，支持 YAML 格式，便于维护与扩展  
✅ 统一驱动管理：全平台驱动自动初始化、自动销毁，降低维护成本  
✅ 可视化报告：集成 Allure Report，清晰展示测试结果、用例覆盖率及失败原因  
✅ 持续集成：支持 GitHub Actions 自动触发测试、生成报告，适配 Jenkins 流水线  
✅ 高可复用性：工具类与业务逻辑解耦，页面对象层（PO模式）统一管理，适配业务快速迭代  
✅ 灵活执行：支持按模块、按类型执行用例，支持冒烟测试、回归测试，支持失败重跑

---

## 技术栈
| 测试类型              | 核心技术                                       |
|:------------------|:-------------------------------------------|
| 测试框架              | pytest/unittest                            |
| 接口自动化             | requests + pytest                          |
| Web UI 自动化(传统)    | unittest + selenium                        |
| Web UI 自动化(现代)    | Playwright（支持Chrome/Firefox/WebKit）        |
| Android APP 自动化   | Appium + ADB（支持真机/模拟器）                     |
| iOS APP 自动化       | Appium + XCUITest                          |
| Windows 桌面自动化     | PyAutoGUI                                  |
| Linux 桌面自动化       | PyAutoGUI                                  |
| Linux 服务端自动化      | Paramiko（SSH远程操作）                          |
| HarmonyOS 鸿蒙自动化   | Appium + UiAutomator2 + HDC（鸿蒙调试工具）        |
| 报告工具              | Allure Report                              |
| 配置管理              | PyYAML + python-dotenv                     |
| 日志工具              | loguru                                     |
| CI/CD             | GitHub Actions/Jenkins                     |

---

## 目录结构说明
核心采用分层架构设计，目录清晰、职责明确，便于团队协作与维护：
```
PythonProject3/
├── .github/
│   └── workflows/
│       ├── ci_allure.yml            # GitHub Actions：分平台跑 + 汇总 Allure
│       └── test_workflow.yml        # 旧版示例工作流（pytest-html）
├── .gitignore                       # Git 忽略规则
├── bat/                             # 历史/本地生成的报告与脚本
│   ├── run_allure.bat               # 本地一键生成 Allure 报告（Windows）
│   └── 测试报告_*/                  # 历史 Allure 报告（独立目录）
├── config/                          # 配置（多环境/多端）
│   ├── env_config.yaml
│   ├── ui_config.yaml
│   ├── app_config.yaml
│   ├── windows_config.yaml
│   └── linux_config.yaml
├── page_objects/                    # 页面对象（多端）
│   ├── __init__.py
│   ├── web/
│   │   ├── __init__.py
│   │   ├── base_page.py
│   │   ├── home_page.py
│   │   └── login_page.py
│   │   ├── order_page.py
│   │   └── user_page.py
│   ├── android/
│   │   ├── __init__.py
│   │   ├── base_android.py
│   │   └── login_page.py
│   ├── ios/
│   │   └── __init__.py
│   ├── windows/
│   │   ├── __init__.py
│   │   ├── base_window.py
│   │   └── login_window.py
│   ├── linux_gui/
│   │   ├── __init__.py
│   │   ├── base_linux_gui.py
│   │   └── terminal_page.py
│   ├── base/
│   │   ├── __init__.py
│   │   └── base_page.py
│   └── harmony/                      # 新增这个文件夹
│   │    ├── __init__.py
│   │    ├── base_harmony.py         # 鸿蒙基类
│   │    └── login_page.py           # 鸿蒙登录页
├── service_objects/
│   ├── __init__.py
│   ├── base_service.py
│   └── linux_service.py
├── test_data/                       # 测试数据
│   ├── api_test_data.yaml
│   └── ui_test_data.yaml
├── tests/
│   ├── conftest.py                  # 全局 fixture + 按端启用开关 + 自动打 marker
│   ├── test_api/
│   │   └── test_user_api.py
│   ├── test_ui/
│   │   └── test_user_ui.py
│   ├── test_android/
│   │   ├── test_android_appium/
│   │   │   ├── test_demo.py
│   │   │   └── test_login_android.py
│   │   └── test_android_airtest/
│   │       ├── test_airtest_redmi4.py
│   │       └── test_login.py
│   ├── test_ios/
│   │   └── test_ios_demo.py
│   ├── test_windows/
│   │   ├── test_login.py
│   │   ├── test_notepad.py
│   │   └── test_windows_gui.py
│   ├── test_linux/
│   │   ├── test_linux_gui.py
│   │   └── test_terminal.py
│   ├── test_service/
│   │   └── test_linux_service.py
│   └── test_harmony/
│       ├── __init__.py
│       ├── test_login_harmony.py   # 新增
│       └── test_user_harmony.py    # 新增
├── utils/
│   ├── api_client.py
│   ├── android_driver.py
│   ├── airtest_driver.py
│   ├── ios_driver.py
│   ├── linux_client.py
│   ├── linux_driver.py
│   ├── ui_driver.py
│   ├── windows_driver.py
│   ├── common_utils.py
│   ├── config_reader.py
│   ├── logger.py
│   ├── harmony_driver.py # 新增鸿蒙驱动
│   └── send_email.py
├── tools/
│   └── get_mouse_pos.py
├── logs/                            # 运行日志（自动生成）
├── allure-results/                  # Allure 原始结果（执行后生成）
└── allure-report/                   # Allure 静态报告（生成后可直接打开）
├── pytest.ini
├── requirements.txt
├── run_all_smoke.py
├── Run_CI.bat
├── README.md
└── 笔记.txt
```
---

## 环境准备
### 1. 克隆项目
```bash
git clone https://github.com/WEN-we/AutoTest01.git
cd ecommerce_auto_test
```
### 2. 创建并激活虚拟环境（推荐）
#### Windows
```bash
运行
python -m venv venv
venv\Scripts\activate
```
#### Linux/Mac
```bash
运行
python3 -m venv venv
source venv/bin/activate
```
### 3. 安装项目依赖（Python3.11 稳定兼容）
```bash
运行
pip install -r requirements.txt
```
### 4. 安装 Playwright 浏览器（Web UI 自动化必备）
```bash
运行
playwright install
```
---
### 补充说明
#### Android APP 测试：需提前配置 ADB 环境、安装 Appium 服务
#### iOS APP 测试：需配置 Xcode 环境、模拟器 / 真机调试权限
#### Linux 服务端测试：需提前获取服务器 SSH 连接信息（IP、端口、账号密码）

---

## 本地执行测试
#### 1. 一键运行全平台冒烟测试（推荐，快速验证核心流程）
```bash
运行
python run_all_smoke.py
```
#### 2. 执行所有测试用例
```bash
运行
pytest --run-all
```
##### 传统框架 Web 测试（Selenium + Unittest）
```
#运行 Selenium 用例
python -m unittest discover tests/test_selenium/
```
#### 3. 按测试类型执行指定用例
```bash
运行
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

- **临时全开（可能需要额外环境/驱动）**：

```bash
pytest --run-all
```

- **按端启用（推荐）**：通过环境变量控制收集
  - `ENABLE_ANDROID=1`：收集 `tests/test_android/`
  - `ENABLE_IOS=1`：收集 `tests/test_ios/`
  - `ENABLE_HARMONY=1`：收集 `tests/test_harmony/`
  - `ENABLE_WINDOWS=1`：收集 `tests/test_windows/`（非 Windows 平台时）
  - `ENABLE_LINUX=1`：收集 `tests/test_linux/`（非 Linux 平台时）
  - `ENABLE_SERVICE=1`：收集 `tests/test_service/`

示例：

```bash
set ENABLE_ANDROID=1
pytest -m android
```
#### 4. 执行指定模块用例（如订单模块接口用例）
```bash
运行
pytest tests/test_api/test_order_api.py -v
```
#### 5. 查看 Allure 可视化报告
```bash
运行
allure serve allure-results
```
---
## CI/CD 配置（自动化集成）
### GitHub Actions 配置
#### 将项目推送到 GitHub 仓库
#### 配置文件路径：.github/workflows/test_workflow.yml（已预设，可直接复用）
#### 开启 GitHub Pages：设置 → Pages → 源选择 gh-pages 分支
#### 触发条件：每次 push 到 master 分支或提交 PR 时，自动执行全平台测试、生成 Allure 报告并上传
#### 报告地址：https://github.com/WEN-we/AutoTest01/actions/runs/23890788190/artifacts/6237423778
### Jenkins 配置（可选）
执行脚本：Run_CI.bat（Windows），可配置定时任务、自动拉取代码、触发测试流程

---
## GitHub Actions（全平台 Allure 统一报告）
项目已提供工作流：`.github/workflows/ci_allure.yml`，会拆分为 4 个 job：

- Linux：API + UI + Service(SSH)
- Windows：桌面自动化
- macOS：iOS（需要你在 Runner 上具备 Appium/Xcode/应用包等条件）
- 汇总：下载各 job 的 `allure-results`，合并并生成 `allure-report` 作为 artifact

### 关于 iOS/Android/真实设备说明
- GitHub Hosted Runner **无法直接访问你的真机**。如果你要跑真机/内网环境，请改用 **self-hosted runner**。
- 当前 iOS job 作为“可跑框架骨架”，你需要补齐：
  - Appium Server 启动方式（以及 `APPIUM_URL`、udid、app 路径等配置）
  - 证书/签名/应用包路径（或使用模拟器 app）


## 业务适配说明（快速适配自身电商业务）
#### 配置适配：修改 config/ 目录下对应配置文件，更新环境地址、账号密码、设备信息等
#### Web 端：修改 ui_config.yaml（浏览器、超时时间等）
#### APP 端：修改 app_config.yaml（包名、启动页、设备名称等）
#### Linux 端：修改 linux_config.yaml（SSH 连接信息、服务检查命令等）
#### 数据适配：修改 test_data/ 下的接口 / UI 测试数据，替换为自身业务数据
#### UI 适配：修改 page_objects/ 下的元素定位器（XPath/CSS），适配自身前端页面
#### 用例适配：基于 tests/ 下的用例模板，新增 / 修改用例，覆盖自身电商业务场景（如商品下单、支付、退款等）
#### 多端适配：Android/iOS/Windows/Linux 端无需修改核心代码，仅需调整对应配置文件即可运行

---
## 注意事项
#### 测试环境需保持稳定，避免环境差异（如前端页面更新、接口地址变更）导致用例失败
#### 敏感信息（如数据库密码、接口 token、服务器账号密码）需放在 .env 文件中，禁止提交到代码仓库
#### 用例编写遵循 “单一职责” 原则，每个用例只验证一个业务场景，便于问题定位
#### 工具类禁止写入业务逻辑，保持通用性，便于跨项目复用
#### 每次提交代码前，需本地执行冒烟用例，确保核心业务流程正常，避免影响整体测试体系
#### 执行 APP / 桌面端测试时，需确保设备（真机 / 模拟器 / 桌面）处于可用状态，避免驱动启动失败

---
## 适用场景
#### 电商 Web 平台自动化测试（商城前端、后台管理系统）
#### 电商 APP 自动化测试（Android/iOS 真机 / 模拟器）
#### Windows 桌面电商相关软件测试
#### Linux 服务端监控、接口测试、部署验证
#### 电商核心流程冒烟测试、回归测试、系统测试
#### 企业级 CI/CD 自动化集成，实现测试流程自动化

---
### 核心优化&亮点（贴合全平台测试，适配该项目）
1.  标题升级为“全平台”，明确覆盖所有测试端，突出项目竞争力
2.  新增「核心特性」模块，清晰展示全平台优势，适配面试/毕设场景
3.  技术栈用表格呈现，各端测试对应技术一目了然，更规范
4.  目录结构补充全平台相关文件（如各端驱动、用例目录），与该项目实际完全匹配
5.  执行测试部分，补充各端单独执行命令，方便本地调试
6.  环境准备、业务适配、注意事项，均补充全平台相关说明，避免遗漏
7.  排版统一：用 `---` 分隔模块，代码块高亮，关键路径用反引号标注，列表对齐，适配GitHub渲染
8.  保留原文的核心信息（仓库地址、报告地址、原有模块），不新增冗余内容