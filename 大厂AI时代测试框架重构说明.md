# 大厂 AI 时代测试框架重构说明

> 项目：AutoTest01 企业级电商全平台自动化测试框架
> 日期：2026-08-22
> 背景：按大厂 AI 时代测开形态，删除旧「AI 自主测试」与「测试平台」，重新设计与搭建

---

## 一、本次重构决策

| 动作 | 对象 | 原因 |
| :--- | :--- | :--- |
| 🗑️ 删除 | `web_platform/`（旧 Flask 测试平台，83 文件） | 臃肿、前端 15 个页面堆砌、与 SUT API 重复，非大厂测开形态 |
| 🗑️ 删除 | `agents/`、`ai_page_objects/`、`tests/test_ai/`、`utils/tools/ai_client.py`、`config/ai_config.yaml` | 旧"AI 自主测试"是堆叠的玩具框架，未形成 AI 时代真正的工具链价值 |
| 🆕 新建 | `utils/ai/` AI 工具链 | 失败智能分析 / flaky 识别 / AI 用例生成 —— 大厂 AI 测开的真实提效点 |
| 🆕 新建 | `quality_platform/` 质量工程平台 | 质量看板 + 失败分析 + 一键执行 —— 大厂测开"搭平台"形态，轻量可落地 |
| 🔧 保留 | `local_web_login/`（被测系统 SUT）、PO/服务层/用例层 | 测试对象与分层地基，不属平台 |

## 二、新架构总览

```
┌──────────────────────────────────────────────────────────────┐
│ 质量工程平台 quality_platform/（Flask + SQLite，端口 8081）    │
│  看板(通过率/flaky率/趋势) · 失败分析(AI归因) · 执行中心 · 用例清单 │
├──────────────────────────────────────────────────────────────┤
│ AI 工具链 utils/ai/                                            │
│  llm_client(OpenAI兼容) · failure_analyzer(LLM+规则)          │
│  flaky_detector(30%~70%) · test_generator(描述→用例)          │
├──────────────────────────────────────────────────────────────┤
│ 用例层 tests/（接口优先，UI 少而精）→ 服务层 → PO 层（不写断言） │
├──────────────────────────────────────────────────────────────┤
│ 通用层 utils/drivers(生命周期) + utils/tools(日志/配置/路径)     │
└──────────────────────────────────────────────────────────────┘
       测试对象：local_web_login（被测服务 SUT，端口 8090）
```

## 三、AI 工具链（大厂 AI 时代差异化）

| 模块 | 能力 | 无 API Key 时 |
| :--- | :--- | :--- |
| `llm_client.py` | OpenAI 兼容对话（通义/DeepSeek/OpenAI/本地 vLLM），Key 走环境变量 `LLM_API_KEY/LLM_BASE_URL/LLM_MODEL` | 标记不可用，上层自动降级 |
| `failure_analyzer.py` | 失败归因：产品缺陷/测试缺陷/环境波动/定位器失效 + 置信度 + 建议 | 规则引擎按异常类型分类 |
| `flaky_detector.py` | 最近 N 次失败率 30%~70% → 疑似 flaky（业界标准区间） | 纯计算，无需 AI |
| `test_generator.py` | 描述 → pytest 用例骨架（API/UI 两类） | 输出可编辑模板 |

配置：`config/ai_tools.yaml`（模型/超参）；**API Key 只从环境变量读取，禁止入库**。

## 四、质量工程平台（替代旧 web_platform）

```
quality_platform/
├─ app.py                Flask 入口：4 页面 + 8 REST API
├─ models.py             SQLite 数据层（executions / case_results / ai_analysis）
├─ services/
│  ├─ test_executor.py   pytest 异步执行（线程）+ JUnit 解析入库 + 截图证据关联
│  └─ ai_integration.py  AI 能力接入（失败归因缓存 / flaky 聚合）
├─ templates/            dashboard / failures / runs / cases
├─ static/               前端（Chart.js 趋势图）
└─ data/                 quality.db（gitignore，自动建库建表）
```

核心链路：**一键执行**（选测试路径 → 后台跑 pytest → JUnit 解析入库 → 失败用例自动关联 `reports/screenshots/` 截图）→ **失败分析**（对单条失败点 AI 归因，结果缓存）→ **flaky 治理**（聚合历史 → 识别 30%~70% 失败率用例）。

启动：`python quality_platform/app.py` → http://127.0.0.1:8081

## 五、验证结果（2026-08-22）

| 项 | 结果 |
| :--- | :--- |
| 全部新增/修改文件语法（compileall） | ✅ 通过 |
| 平台 4 页面 + 4 API 路由（Flask test_client） | ✅ 全部 200，看板聚合正常 |
| AI 工具链冒烟（规则降级模式） | ✅ 超时→环境波动、断言→产品缺陷、flaky 识别 50% 用例、模板生成 |
| LLM 未配 Key 降级 | ✅ available=False，不抛错 |
| pytest 收集 | ⚠️ 当前环境无 pytest（重建 venv 后验证） |

## 六、⚠️ 数据恢复说明（重要）

执行删除时发现 `tests/`、`config/`、`utils/`、`test_data/` 目录已在 IDE 中被删除
（git 索引完好，删除未提交）。已执行 `git checkout -- tests config utils test_data`
从 HEAD 恢复，并重做了 3 个升级文件（conftest 截图 hook / selenium_driver 去重 / test_ec_login 服务层）。

**唯一不可恢复**：`tests/test_ui/velmart_web_helper.py`（untracked，未进 git）——
已确认无其他文件依赖它，不影响现有用例运行。如本地有备份可放回。

## 七、后续路线

- P1：重建 venv（`python -m venv .venv && pip install -r requirements.txt`）后跑 `pytest --collect-only` 全量收集验证
- P1：配置 `LLM_API_KEY` 环境变量，体验失败归因 LLM 模式
- P2：平台执行中心接入 CI（GitHub Actions 上传 junit → 平台解析）
- P2：`docs/项目面试笔记_企业级全平台自动化测试框架.md` 中「AI 智能测试 / Web 测试管理平台」两章需按新架构重写
