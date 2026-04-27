<div align="center">
  <img src="img/fufu.png" alt="Logo" width="200" height="200">
  
  # Enterprise E-commerce Full-Platform Automated Testing Framework
  
  ✨ Full-platform automated testing solution based on Python + Pytest ✨
  
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
  [![TestFramework](https://img.shields.io/badge/TestFramework-Pytest-green.svg)](https://docs.pytest.org/)
  [![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Android%20%7C%20iOS%20%7C%20HarmonyOS%20%7C%20Windows%20%7C%20Linux-orange.svg)](README_en.md)
  [![CI](https://img.shields.io/badge/CI-GitHub%20Actions%20%7C%20Jenkins-red.svg)](README_en.md)
  [![Report](https://img.shields.io/badge/Report-Allure-green.svg)](https://docs.qameta.io/allure/)
  
  English | [简体中文](README.md)
</div>

---

## Project Introduction

This project is an **enterprise-level e-commerce full-platform automated testing general framework** built based on Python + Pytest. It covers testing scenarios for Web, API, Android APP, iOS APP, Windows desktop, Linux desktop, and Linux server. It integrates Allure visual reports and GitHub Actions CI/CD continuous integration, realizing multi-environment isolation, separation of data and use cases, high reusability of tool classes, adapting to various e-commerce business scenarios, directly reusable and quickly adaptable to own business needs, and implementing full-process automated testing.

---

## Core Features

| Feature | Description |
| :--- | :--- |
| ✅ Full Platform Coverage | Web UI + API + Android APP + iOS APP + Windows Desktop + Linux Desktop + Linux Server + HarmonyOS |
| ✅ Multi-Environment Isolation | Support one-click switching between development, testing, and production environments to avoid environment interference |
| ✅ Data-Driven Testing | Separation of test data and test cases, support for YAML format, easy to maintain and extend |
| ✅ Unified Driver Management | Automatic initialization and destruction of full-platform drivers, reducing maintenance costs |
| ✅ Visual Reports | Integration of Allure Report, clearly displaying test results, case coverage, and failure reasons |
| ✅ Continuous Integration | Support for GitHub Actions to automatically trigger tests, generate reports, and adapt to Jenkins pipelines |
| ✅ High Reusability | Decoupling of tool classes and business logic, unified management of page object layer (PO pattern), adapting to rapid business iteration |
| ✅ Flexible Execution | Support for executing cases by module and type, support for smoke testing, regression testing, and failure rerun |

---

## Technology Stack

| Testing Type | Core Technology |
| :--- | :--- |
| Testing Framework | pytest/unittest |
| API Automation | requests + pytest |
| Web UI Automation (Traditional) | unittest + selenium |
| Web UI Automation (Modern) | Playwright (supports Chrome/Firefox/WebKit) |
| Android APP Automation | Appium + ADB (supports real devices/emulators) |
| iOS APP Automation | Appium + XCUITest |
| Windows Desktop Automation | PyAutoGUI |
| Linux Desktop Automation | PyAutoGUI |
| Linux Server Automation | Paramiko (SSH remote operation) |
| HarmonyOS Automation | Appium + UiAutomator2 + HDC (HarmonyOS debugging tool) |
| Reporting Tool | Allure Report |
| Configuration Management | PyYAML + python-dotenv |
| Logging Tool | loguru |
| CI/CD | GitHub Actions/Jenkins |

---

## Directory Structure

The core adopts a layered architecture design with clear directories and clear responsibilities, facilitating team collaboration and maintenance:

```
AutoTest01/                     # repo 根（默认分支: master）
├─ .github/
│  └─ workflows/                # GitHub Actions 工作流（CI/CD 配置）
├─ .gitignore
├─ README.md
├─ README_en.md
├─ Run_CI.bat                   # 一键运行 CI（Windows batch）
├─ 笔记.txt                      # 个人笔记 / 文档
├─ pytest.ini                   # pytest 配置
├─ requirements.txt
├─ requirements-ci.txt
├─ Run_CI.bat
├─ bat/
│  └─ run_allure.bat            # Allure 报告相关 batch 脚本
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
├─ erp/
│  └─ driver/                   # ERP 相关驱动（目录存在，可能为空）
├─ img/
│  ├─ fufu.png
│  └─ img.png                   # 演示/文档用图片资源
├─ local_web_login/
│  ├─ __init__.py
│  └─ backend_server.py         # 本地登录后端服务（示例/测试用）
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
└─ utils/
   ├─ __init__.py
   ├─ drivers/                  # 驱动相关工具/封装
   └─ tools/                    # 工具集合
```

---

## Environment Setup

### 1. Clone the Project
```bash
git clone https://github.com/WEN-we/AutoTest01.git
cd ecommerce_auto_test
```

### 2. Create and Activate Virtual Environment (Recommended)

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

### 3. Install Project Dependencies (Python 3.11 stable compatible)
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browser (Required for Web UI Automation)
```bash
playwright install
```

---

### Additional Notes

- **Android APP Testing**: Need to configure ADB environment and install Appium service in advance
- **iOS APP Testing**: Need to configure Xcode environment, simulator / real device debugging permissions
- **Linux Server Testing**: Need to obtain server SSH connection information (IP, port, account password) in advance

---

## Local Test Execution

### 1. One-click Run Full-Platform Smoke Test (Recommended, Quick Verification of Core Processes)
```bash
python run_all_smoke.py
```

### 2. Execute All Test Cases
```bash
pytest --run-all
```

### 3. Traditional Framework Web Testing (Selenium + Unittest)
```bash
# Run Selenium cases
python -m unittest discover tests/test_selenium/
```

### 4. Execute Specified Cases by Test Type
```bash
# Only execute API cases
pytest -m api

# Only execute Web UI cases
pytest -m ui

# Only execute smoke cases (core processes, quick verification)
pytest -m smoke

# Only execute Android APP cases
pytest tests/test_android/

# Only execute Linux server cases
pytest tests/test_service/

# Only execute Windows desktop cases
pytest tests/test_windows/
```

---

## End Capability Enablement Switch (Important)

To avoid "errors during test collection phase" when the corresponding environment is not installed, the project only collects **API + UI** two types of basic cases by default; please enable other ends as needed:

### Temporary Full Enablement (May require additional environment/drivers)
```bash
pytest --run-all
```

### Enable by End (Recommended): Controlled collection through environment variables

| Environment Variable | Function |
| :--- | :--- |
| `ENABLE_ANDROID=1` | Collect `tests/test_android/` |
| `ENABLE_IOS=1` | Collect `tests/test_ios/` |
| `ENABLE_HARMONY=1` | Collect `tests/test_harmony/` |
| `ENABLE_WINDOWS=1` | Collect `tests/test_windows/` (when not on Windows platform) |
| `ENABLE_LINUX=1` | Collect `tests/test_linux/` (when not on Linux platform) |
| `ENABLE_SERVICE=1` | Collect `tests/test_service/` |

### Example
```bash
set ENABLE_ANDROID=1
pytest -m android
```

### 5. Execute Specified Module Cases (e.g., Order Module API Cases)
```bash
pytest tests/test_api/test_order_api.py -v
```

### 6. View Allure Visual Report
```bash
allure serve allure-results
```

---
## CI/CD Configuration (Automated Integration)

### GitHub Actions Configuration

- **Push the project to GitHub repository**
- **Configuration file path**: `.github/workflows/test_workflow.yml` (preset, can be used directly)
- **Enable GitHub Pages**: Settings → Pages → Source select gh-pages branch
- **Trigger condition**: Every time you push to the master branch or submit a PR, it will automatically execute full-platform tests, generate Allure reports and upload
- **Report address**: https://github.com/WEN-we/AutoTest01/actions/runs/23890788190/artifacts/6237423778

### Jenkins Configuration (Optional)

Execution script: `Run_CI.bat` (Windows), can configure scheduled tasks, automatically pull code, trigger test processes

---

## GitHub Actions (Full-Platform Allure Unified Report)

The project has provided workflow: `.github/workflows/ci_allure.yml`, which will be split into 4 jobs:

- **Linux**: API + UI + Service(SSH)
- **Windows**: Desktop automation
- **macOS**: iOS (requires you to have Appium/Xcode/app package etc. on the Runner)
- **Summary**: Download `allure-results` from each job, merge and generate `allure-report` as artifact

### About iOS/Android/Real Device Instructions

- GitHub Hosted Runner **cannot directly access your real devices**. If you want to run real devices/intranet environments, please use **self-hosted runner** instead.
- The current iOS job serves as a "runnable framework skeleton", you need to complete:
  - Appium Server startup method (and `APPIUM_URL`, udid, app path and other configurations)
  - Certificate/signature/app package path (or use simulator app)

---

## Business Adaptation Instructions (Quickly Adapt to Your Own E-commerce Business)

| Adaptation Type | Operation Instructions |
| :--- | :--- |
| Configuration Adaptation | Modify the corresponding configuration files in the `config/` directory, update environment addresses, account passwords, device information, etc. |
| Web End | Modify `ui_config.yaml` (browser, timeout, etc.) |
| APP End | Modify `app_config.yaml` (package name, splash screen, device name, etc.) |
| Linux End | Modify `linux_config.yaml` (SSH connection information, service check commands, etc.) |
| Data Adaptation | Modify the API / UI test data under `test_data/` and replace it with your own business data |
| UI Adaptation | Modify the element locators (XPath/CSS) under `page_objects/` to adapt to your own front-end pages |
| Case Adaptation | Based on the case templates under `tests/`, add / modify cases to cover your own e-commerce business scenarios (such as product ordering, payment, refund, etc.) |
| Multi-End Adaptation | Android/iOS/Windows/Linux ends do not need to modify core code, only need to adjust the corresponding configuration files to run |

---

## Notes

- **Test environment needs to be stable** to avoid case failures caused by environment differences (such as front-end page updates, interface address changes)
- **Sensitive information** (such as database passwords, interface tokens, server account passwords) should be placed in `.env` files and prohibited from being submitted to the code repository
- **Case writing follows the "single responsibility" principle**, each case only verifies one business scenario, facilitating problem location
- **Tool classes are prohibited from writing business logic**, maintain versatility, and facilitate cross-project reuse
- **Before each code submission**, local smoke cases need to be executed to ensure normal core business processes and avoid affecting the overall test system
- **When executing APP / desktop testing**, ensure that the device (real device / simulator / desktop) is in an available state to avoid driver startup failure

---

## Application Scenarios

- **E-commerce Web platform automated testing** (mall front-end, backend management system)
- **E-commerce APP automated testing** (Android/iOS real devices / simulators)
- **Windows desktop e-commerce related software testing**
- **Linux server monitoring, interface testing, deployment verification**
- **E-commerce core process smoke testing, regression testing, system testing**
- **Enterprise-level CI/CD automated integration, realizing test process automation**

---

## Core Optimization & Highlights

1. **Full platform coverage**: Clearly cover all test ends, highlighting project competitiveness
2. **Core features module**: Clearly display full platform advantages, suitable for interview/graduation project scenarios
3. **Technology stack tabulation**: Each end test corresponding technology is clear at a glance, more standardized
4. **Complete directory structure**: Supplement full platform related files, completely match the actual project
5. **Detailed execution commands**: Supplement separate execution commands for each end, convenient for local debugging
6. **Comprehensive adaptation instructions**: Environment preparation, business adaptation, and notes all supplement full platform related instructions
7. **Unified typesetting specifications**: Use `---` to separate modules, code block highlighting, key paths marked with backticks
8. **Complete information retention**: Retain the core information of the original text, no redundant content added

---

<div align="center">
  <h3>🌟 Enterprise E-commerce Full-Platform Automated Testing Framework 🌟</h3>
  <p>Make automated testing simpler and more efficient</p>
</div>