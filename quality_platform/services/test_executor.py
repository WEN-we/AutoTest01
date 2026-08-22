"""
质量工程平台 - 测试执行服务

职责（大厂平台"一键执行 + 结果入库"链路）：
1. 触发：后台线程运行 pytest（--junitxml 结构化结果 + --alluredir 报告 + 可选并发/重试）
2. 解析：JUnit XML -> 用例结果（nodeid/状态/错误信息）
3. 入库：executions + case_results
4. 证据：失败用例自动关联 reports/screenshots/ 下最新截图

用法：
    from quality_platform.services.test_executor import TestExecutor
    executor = TestExecutor()
    executor.run_async("tests/test_api/", reruns=1, parallel=2)
"""
import os
import re
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from utils.tools.logger import log
from quality_platform.models import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "screenshots"
JUNIT_TMP = PROJECT_ROOT / "reports" / "platform" / "junit.xml"
PLATFORM_CONFIG = PROJECT_ROOT / "quality_platform" / "config" / "platform_config.yaml"
_ENV_VAR = re.compile(r"^\$\{(\w+)\}$")


def _load_exec_env() -> dict:
    """读取执行环境变量配置，${VAR} 透传宿主环境变量（如 ${DEEPSEEK_API_KEY}）。"""
    try:
        cfg = yaml.safe_load(PLATFORM_CONFIG.read_text(encoding="utf-8")).get("exec_env", {})
        resolved = {}
        for k, v in cfg.items():
            m = _ENV_VAR.match(str(v))
            resolved[k] = os.environ.get(m.group(1), "") if m else str(v)
        return resolved
    except Exception as exc:
        log.warning(f"[平台] exec_env 读取失败：{exc}")
        return {}


class TestExecutor:
    """pytest 执行器（异步线程 + JUnit 解析 + 参数化执行）"""

    def __init__(self, default_timeout: int = 1800):
        self.default_timeout = default_timeout

    def run_async(self, test_path: str, reruns: int = 0, parallel: int = 0,
                  timeout: int = 0, marker: str = "") -> int:
        """
        异步执行测试，立即返回 execution_id。
        reruns:   失败重试次数（大厂标准 1~2 次）
        parallel: 并发 worker 数（0 = 串行；>1 走 pytest-xdist）
        timeout:  单用例超时秒数（0 = 不限制，走 pytest-timeout）
        marker:   pytest 标记过滤（如 smoke / api）
        """
        exec_id = db.insert_execution(test_path)
        thread = threading.Thread(
            target=self._run,
            args=(exec_id, test_path),
            kwargs={"reruns": reruns, "parallel": parallel,
                    "timeout": timeout, "marker": marker},
            daemon=True,
        )
        thread.start()
        return exec_id

    # ---------- 内部实现 ----------
    def _run(self, exec_id: int, test_path: str, reruns: int = 0,
             parallel: int = 0, timeout: int = 0, marker: str = ""):
        started = time.time()
        try:
            JUNIT_TMP.parent.mkdir(parents=True, exist_ok=True)
            cmd = self._build_command(test_path, reruns, parallel, timeout, marker)
            log.info(f"[平台] 执行测试：{' '.join(cmd)}")
            env = {**os.environ, **_load_exec_env()}  # 注入执行环境变量（覆盖被测服务地址）
            proc = subprocess.run(
                cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=self.default_timeout, env=env,
            )
            results = self._parse_junit(JUNIT_TMP) if JUNIT_TMP.exists() else []
            total = len(results)
            passed = sum(1 for r in results if r["status"] == "passed")
            failed = sum(1 for r in results if r["status"] in ("failed", "error"))
            skipped = total - passed - failed

            for r in results:
                if r["status"] in ("failed", "error"):
                    r["screenshot"] = self._find_screenshot(r["nodeid"])
                db.insert_case_result(exec_id, r["nodeid"], r["status"],
                                      r["duration"], r["error_type"],
                                      r["error_message"], r.get("screenshot", ""))

            db.finish_execution(exec_id, total, passed, failed, skipped,
                                round(time.time() - started, 2))
            log.info(f"[平台] 执行完成：exec={exec_id} total={total} "
                     f"passed={passed} failed={failed} skipped={skipped}")
            # 完成通知（webhook，失败不阻塞主流程）
            try:
                from quality_platform.services.notifier import send_execution_summary
                send_execution_summary(exec_id)
            except Exception as exc:
                log.warning(f"[平台] 通知异常：{exc}")
        except Exception as exc:
            log.error(f"[平台] 执行异常：{exc}")
            db.finish_execution(exec_id, 0, 0, 0, 0, round(time.time() - started, 2))

    # ---------- 命令构建（大厂执行参数化） ----------
    def _build_command(self, test_path: str, reruns: int, parallel: int,
                       timeout: int, marker: str) -> list[str]:
        # 使用当前解释器（sys.executable），确保与平台同 Python 环境、依赖一致
        cmd = [sys.executable, "-m", "pytest", str(test_path),
               f"--junitxml={JUNIT_TMP}",
               "--alluredir", str(PROJECT_ROOT / "reports" / "allure-results"),
               "-q"]
        if reruns > 0:
            cmd += [f"--reruns={reruns}", "--reruns-delay=1"]
        if parallel > 1:
            cmd += [f"-n{parallel}", "--dist=loadscope"]
        if timeout > 0:
            cmd += [f"--timeout={timeout}"]
        if marker:
            cmd += ["-m", marker]
        return cmd

    # ---------- JUnit 解析 ----------
    def _parse_junit(self, xml_path: Path) -> list[dict]:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        results = []
        for case in root.iter("testcase"):
            nodeid = case.get("classname", "") + "::" + case.get("name", "")
            duration = float(case.get("time", 0) or 0)
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")
            if failure is not None:
                results.append({
                    "nodeid": nodeid, "status": "failed", "duration": duration,
                    "error_type": (failure.get("type") or "AssertionError"),
                    "error_message": (failure.text or "").strip()[:4000],
                })
            elif error is not None:
                results.append({
                    "nodeid": nodeid, "status": "error", "duration": duration,
                    "error_type": (error.get("type") or "Error"),
                    "error_message": (error.text or "").strip()[:4000],
                })
            elif skipped is not None:
                results.append({"nodeid": nodeid, "status": "skipped",
                                "duration": duration, "error_type": "", "error_message": ""})
            else:
                results.append({"nodeid": nodeid, "status": "passed",
                                "duration": duration, "error_type": "", "error_message": ""})
        return results

    # ---------- 证据关联 ----------
    def _find_screenshot(self, nodeid: str) -> str:
        """按用例名在 reports/screenshots/ 中找最新截图（匹配 nodeid 尾部用例名）。"""
        if not SCREENSHOT_DIR.exists():
            return ""
        test_name = nodeid.split("::")[-1]
        candidates = [
            p for p in SCREENSHOT_DIR.iterdir()
            if p.suffix == ".png" and test_name in p.name
        ]
        if not candidates:
            return ""
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        return str(latest.relative_to(PROJECT_ROOT)).replace("\\", "/")


# 全局单例
executor = TestExecutor()
