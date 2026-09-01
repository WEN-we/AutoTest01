"""
质量工程平台 - 测试执行服务

职责（大厂平台"一键执行 + 结果入库"链路）：
1. 排队：线程池（默认 2 个 worker）+ 无界队列，提交即返回，超出并发自动排队
2. 执行：后台运行 pytest（--junitxml 结构化结果 + --alluredir 报告 + 可选并发/重试）
3. 解析：JUnit XML -> 用例结果（nodeid/状态/错误信息）
4. 入库：executions + case_results
5. 证据：失败用例自动关联 reports/screenshots/ 下最新截图
6. 治理：支持取消（排队中直接取消 / 运行中 kill 子进程）与整体超时强杀

用法：
    from quality_platform.services.test_executor import executor
    executor.run_async("tests/test_api/", reruns=1, parallel=2)
    executor.cancel(exec_id)
    executor.queue_status()
"""
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

from utils.tools.logger import log
from quality_platform.models import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "screenshots"
JUNIT_TMP = PROJECT_ROOT / "reports" / "platform"  # 目录，junit 文件按 exec_id 隔离（防并发覆盖）
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


def _load_auto_analysis_cfg() -> dict:
    """读取失败自动归因配置（auto_analysis 段）。"""
    defaults = {"enabled": True, "max_cases": 10}
    try:
        cfg = yaml.safe_load(PLATFORM_CONFIG.read_text(encoding="utf-8")) \
            .get("auto_analysis", {})
        return {**defaults, **cfg}
    except Exception:
        return defaults


def _load_distributed_workers() -> list[str]:
    """读取分布式 worker 节点配置（distributed.workers，可空=仅本地执行）。"""
    try:
        cfg = yaml.safe_load(PLATFORM_CONFIG.read_text(encoding="utf-8")) \
            .get("distributed", {}) or {}
        return [w for w in (cfg.get("workers") or []) if w]
    except Exception:
        return []


def parse_junit_text(xml_text: str) -> list[dict]:
    """从 JUnit XML 文本解析用例结果（主控本地执行与分布式 worker 回传共用）。"""
    if not xml_text.strip():
        return []
    root = ET.fromstring(xml_text)
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


class TestExecutor:
    """pytest 执行器（线程池队列 + JUnit 解析 + 取消/超时治理）"""

    def __init__(self, default_timeout: int = 1800, max_workers: int = 2):
        self.default_timeout = default_timeout
        self.max_workers = max_workers
        self._pool = ThreadPoolExecutor(max_workers=max_workers,
                                        thread_name_prefix="qa-exec")
        self._futures: dict[int, Future] = {}
        self._cancels: set[int] = set()      # 请求取消的 exec_id（含排队中与运行中）
        self._lock = threading.Lock()

    # ---------- 对外接口 ----------
    def run_async(self, test_path: str, reruns: int = 0, parallel: int = 0,
                  timeout: int = 0, marker: str = "", workers: list[str] | None = None) -> int:
        """
        提交执行任务（排队），立即返回 execution_id。
        reruns:   失败重试次数（大厂标准 1~2 次）
        parallel: 并发 worker 数（0 = 串行；>1 走 pytest-xdist）
        timeout:  单用例超时秒数（0 = 不限制，走 pytest-timeout）
        marker:   pytest 标记过滤（如 smoke / api）
        workers:  远程执行节点列表（如 ["http://127.0.0.1:9101", ...]）；
                  非空时按文件粒度分发并行执行（分布式），无可用节点自动降级本地
        """
        exec_id = db.insert_execution(test_path)
        future = self._pool.submit(
            self._run, exec_id, test_path,
            reruns=reruns, parallel=parallel, timeout=timeout, marker=marker,
            workers=workers,
        )
        with self._lock:
            self._futures[exec_id] = future
        queued = self.queue_status()["queued"]
        log.info(f"[平台] 任务已提交：exec={exec_id} path={test_path} "
                 f"workers={workers or '本地'} 排队中={queued}")
        return exec_id

    def cancel(self, exec_id: int) -> dict:
        """取消执行：排队中直接移出队列；运行中 kill 子进程（结果标记 cancelled）。"""
        with self._lock:
            future = self._futures.get(exec_id)
            if future is None:
                return {"ok": False, "reason": "任务不存在或已结束"}
            if future.cancel():  # 尚未开始，直接从队列移除
                self._futures.pop(exec_id, None)
                db.finish_execution(exec_id, 0, 0, 0, 0, 0.0)
                self._mark_status(exec_id, "cancelled")
                log.info(f"[平台] 任务已取消（未开始）：exec={exec_id}")
                return {"ok": True, "state": "cancelled_before_start"}
            # 已在运行：置取消标记，_run 的等待循环会 kill 子进程
            self._cancels.add(exec_id)
        log.info(f"[平台] 已请求取消（运行中，将终止子进程）：exec={exec_id}")
        return {"ok": True, "state": "cancelling"}

    def recover_orphans(self) -> int:
        """
        启动恢复：把上次进程退出时遗留的 running 记录标记为 interrupted。
        （执行线程随进程消亡，但 DB 状态未回收 → 僵尸"运行中"记录，看板/门禁统计被污染）
        """
        try:
            with db._conn() as conn:
                cur = conn.execute(
                    "UPDATE executions SET status='interrupted', "
                    "finished_at=datetime('now','localtime') WHERE status='running'")
                if cur.rowcount:
                    log.info(f"[平台] 启动恢复：{cur.rowcount} 条僵尸 running 记录已标记为 interrupted")
                return cur.rowcount
        except Exception as exc:
            log.warning(f"[平台] 启动恢复失败：{exc}")
            return 0

    def queue_status(self) -> dict:
        """队列状态：运行中 / 排队中 / 待取消数。"""
        with self._lock:
            futures = list(self._futures.values())
            cancelling = len(self._cancels)
        running = sum(1 for f in futures if f.running())
        done = sum(1 for f in futures if f.done())
        queued = max(len(futures) - running - done, 0)
        return {"max_workers": self.max_workers, "running": running,
                "queued": queued, "cancelling": cancelling}

    # ---------- 内部实现 ----------
    def _run(self, exec_id: int, test_path: str, reruns: int = 0,
             parallel: int = 0, timeout: int = 0, marker: str = "",
             workers: list[str] | None = None):
        started = time.time()
        if workers:
            try:
                self._run_distributed(exec_id, test_path, workers,
                                      reruns, parallel, timeout, marker, started)
                return
            except Exception as exc:
                log.warning(f"[平台] 分布式执行异常，降级本地：{exc}")
        self._run_local(exec_id, test_path, reruns, parallel, timeout, marker, started)

    def _run_local(self, exec_id: int, test_path: str, reruns: int, parallel: int,
                   timeout: int, marker: str, started: float):
        """本地执行（原 _run 逻辑）。"""
        cancelled = False
        timed_out = False
        try:
            # junit 文件按 exec_id 隔离，避免并发执行互相覆盖（大厂执行隔离）
            junit_file = JUNIT_TMP / f"junit_{exec_id}.xml"
            junit_file.parent.mkdir(parents=True, exist_ok=True)
            cmd = self._build_command(test_path, reruns, parallel, timeout, marker,
                                      junit_file)
            log.info(f"[平台] 执行测试：{' '.join(cmd)}")
            # 注入执行环境变量（覆盖被测服务地址）
            # TEST_PLATFORM_EXECUTION=1：通知 conftest 跳过 Allure HTML 生成后处理。
            # 否则每次平台执行都会触发 allure generate（89s~120s 超时），
            # 与手动/并发执行互相阻塞，单用例执行被拖慢 100 倍（exec=68 实测 268s）。
            env = {**os.environ, **_load_exec_env(), "TEST_PLATFORM_EXECUTION": "1"}
            cancelled, timed_out, _ = self._run_subprocess(cmd, env, exec_id)
            results = parse_junit_text(junit_file.read_text(encoding="utf-8", errors="replace")) \
                if junit_file.exists() else []
            self._store_results(exec_id, results, started, cancelled, timed_out)
        except Exception as exc:
            log.error(f"[平台] 执行异常：{exc}")
            db.finish_execution(exec_id, 0, 0, 0, 0, round(time.time() - started, 2))
        finally:
            with self._lock:
                self._futures.pop(exec_id, None)
                self._cancels.discard(exec_id)

    def _run_distributed(self, exec_id: int, test_path: str, workers: list[str],
                         reruns: int, parallel: int, timeout: int, marker: str,
                         started: float):
        """分布式执行：按文件分发到远程 worker 并行跑，汇总 JUnit 入库。"""
        from quality_platform.remote.dispatcher import run_distributed
        out = run_distributed(test_path, workers, reruns, parallel, timeout, marker)
        if out.get("fallback_local") or not out.get("workers_used"):
            log.warning(f"[平台] 分布式无可用节点，降级本地执行：exec={exec_id}")
            self._run_local(exec_id, test_path, reruns, parallel, timeout, marker, started)
            return
        results = out["results"]
        self._store_results(exec_id, results, started,
                            cancelled=False, timed_out=False)
        for err in out["errors"]:
            log.warning(f"[平台] worker 异常（已记录）：{err}")

    def _store_results(self, exec_id: int, results: list[dict], started: float,
                       cancelled: bool, timed_out: bool):
        """统一入库：结果写 case_results + 汇总 executions（本地/分布式共用）。"""
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

        duration = round(time.time() - started, 2)
        db.finish_execution(exec_id, total, passed, failed, skipped, duration)
        if cancelled:
            self._mark_status(exec_id, "cancelled")
        elif timed_out:
            self._mark_status(exec_id, "timeout")
        elif total == 0:
            # 未收集到任何用例：路径有效但被测端被 pytest 忽略/依赖缺失/目录为空。
            # 标记 empty（前端展示"未收集到用例"），避免被误读为"执行成功 0 条"。
            self._mark_status(exec_id, "empty")
            log.warning(f"[平台] 执行完成但未收集到用例（total=0，路径有效但被测端可能被忽略）：exec={exec_id}")
        log.info(f"[平台] 执行完成：exec={exec_id} total={total} "
                 f"passed={passed} failed={failed} skipped={skipped} "
                 f"cancelled={cancelled} timeout={timed_out}")
        # 智能闭环：失败用例自动 AI 归因（LLM 不可用自动降级规则；失败不影响主流程）
        if not cancelled and failed > 0:
            self._auto_analyze(exec_id)
        # 完成通知（webhook，失败不阻塞主流程；消息中带归因结论）
        if not cancelled:
            try:
                from quality_platform.services.notifier import send_execution_summary
                send_execution_summary(exec_id)
            except Exception as exc:
                log.warning(f"[平台] 通知异常：{exc}")
        # 告警规则检查（最近执行失败率超阈值 -> 审计留痕；不阻塞主流程）
        try:
            from quality_platform.services.observability import check_alerts
            check_alerts()
        except Exception as exc:
            log.warning(f"[平台] 告警检查异常：{exc}")

    def _run_subprocess(self, cmd: list[str], env: dict, exec_id: int,
                        poll_seconds: float = 2.0) -> tuple[bool, bool, tuple]:
        """运行子进程，支持运行中取消（kill）与整体超时强杀。"""
        proc = subprocess.Popen(
            cmd, cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", env=env,
        )
        cancelled = timed_out = False
        deadline = time.time() + self.default_timeout
        out = err = ""
        while True:
            try:
                out, err = proc.communicate(timeout=poll_seconds)
                break
            except subprocess.TimeoutExpired:
                with self._lock:
                    want_cancel = exec_id in self._cancels
                if want_cancel:
                    proc.kill()
                    out, err = proc.communicate()
                    cancelled = True
                    break
                if time.time() > deadline:
                    log.warning(f"[平台] 执行超时（>{self.default_timeout}s），强制终止：exec={exec_id}")
                    proc.kill()
                    out, err = proc.communicate()
                    timed_out = True
                    break
        return cancelled, timed_out, (out, err)

    def _mark_status(self, exec_id: int, status: str):
        """补充标记终态（cancelled/timeout），保留统计字段。"""
        try:
            with db._conn() as conn:
                conn.execute("UPDATE executions SET status=? WHERE id=?", (status, exec_id))
        except Exception as exc:
            log.warning(f"[平台] 标记状态失败：exec={exec_id} {status} {exc}")

    def _auto_analyze(self, exec_id: int):
        """
        执行完成后对失败用例批量自动归因（大厂智能闭环：执行 → 自动归因 → 推送）。
        - 条数上限 auto_analysis.max_cases（控制 LLM 调用成本，超出部分人工点按钮分析）
        - LLM 未配置/失败自动降级规则引擎（FailureAnalyzer 内建）
        - 任何异常只记日志，不影响执行结果入库与通知
        """
        cfg = _load_auto_analysis_cfg()
        if not cfg.get("enabled", True):
            return
        try:
            from quality_platform.services.ai_integration import ai
            failed_rows = [r for r in db.list_case_results(exec_id)
                           if r["status"] in ("failed", "error")]
            limit = int(cfg.get("max_cases", 10))
            for row in failed_rows[:limit]:
                ai.analyze_failure(row["id"])  # 带缓存：已分析的直接跳过
            analyzed = min(len(failed_rows), limit)
            if failed_rows:
                log.info(f"[平台] 自动归因完成：exec={exec_id} "
                         f"{analyzed}/{len(failed_rows)} 条失败已分析（LLM/规则自动降级）")
        except Exception as exc:
            log.warning(f"[平台] 自动归因失败（不影响执行结果）：{exc}")

    # ---------- 命令构建（大厂执行参数化） ----------
    def _build_command(self, test_path: str, reruns: int, parallel: int,
                       timeout: int, marker: str, junit_file: Path = None) -> list[str]:
        # 使用当前解释器（sys.executable），确保与平台同 Python 环境、依赖一致
        cmd = [sys.executable, "-m", "pytest", str(test_path),
               f"--junitxml={junit_file or JUNIT_TMP}",
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
        """（兼容保留）从文件解析 JUnit XML。"""
        if not xml_path.exists():
            return []
        return parse_junit_text(xml_path.read_text(encoding="utf-8", errors="replace"))

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
