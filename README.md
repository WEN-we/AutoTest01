# 企业级电商自动化测试项目
## 项目介绍
本项目是企业级电商自动化测试通用模板，支持接口自动化、UI自动化，集成Allure可视化报告和GitHub Actions CI/CD，实现多环境隔离、数据与用例分离、工具类复用，适配所有电商业务场景，可直接复用并快速适配自身业务。

## 技术栈
- 测试框架：pytest
- 接口自动化：requests + pytest
- UI自动化：Playwright（支持Chrome/Firefox/WebKit）
- 报告工具：Allure Report
- CI/CD：GitHub Actions
- 配置管理：PyYAML + python-dotenv
- 日志工具：loguru

## 目录结构说明
详见项目目录结构文档，核心分层：配置层、数据层、工具层、页面对象层、用例层。

## 环境准备
### 1. 克隆项目
git clone https://github.com/WEN-we/AutoTest01.git
cd ecommerce_auto_test

### 2. 创建并激活虚拟环境
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate

### 3. 安装依赖
pip install -r requirements.txt

### 4. 安装Playwright浏览器
playwright install

## 本地执行测试
### 1. 执行所有测试
pytest

### 2. 执行指定类型用例
# 只执行接口用例
pytest -m api

# 只执行UI用例
pytest -m ui

# 只执行冒烟用例
pytest -m smoke

# 执行指定模块用例（如订单模块）
pytest tests/test_api/test_order_api.py

### 3. 查看Allure报告
allure serve allure-results

## CI/CD配置
1. 将项目推送到GitHub仓库
2. 开启GitHub Pages（设置 → Pages → 源选择gh-pages分支）
3. 每次push到main分支或提PR时，GitHub Actions会自动执行测试并生成报告
4. 报告地址：https://<你的用户名>.github.io/<你的仓库名>/

## 业务适配说明
1. 配置适配：修改config/env_config.yaml中的环境地址、账号密码
2. 数据适配：修改test_data/下的接口/UI测试数据，适配自身业务
3. UI适配：修改page_objects/下的元素定位器（XPath/CSS），适配前端页面
4. 用例适配：基于tests/下的用例模板，新增/修改用例，适配业务场景

## 注意事项
1. 测试环境需保持稳定，避免环境问题导致用例失败
2. 敏感信息（如密码、token）可放在.env文件，不提交到代码仓库
3. 用例编写遵循“单一职责”原则，每个用例只验证一个场景
4. 工具类禁止写入业务逻辑，保持通用性
5. 每次提交代码前，先本地执行冒烟用例，确保核心功能正常