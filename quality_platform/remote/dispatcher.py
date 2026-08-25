"""分布式执行分发器（worker 集群雏形）。

职责：
1. 文件拆分：把执行目标（目录）按 test_*.py 文件粒度拆分（大厂"用例集分片"）
2. 健康检查：剔除不可用 worker（GET /health）
3. Round-Robin 分发：文件轮流分配给可用 worker，并行执行
4. 汇总：解析各 worker 回传的 JUnit XML，合并为统一结果列表
5. 降级：无可用 worker 时标记 fallback_local，由主控走本地执行（不中断业务）
"""
import glob
import json
import threading
import urllib.request
from pathlib import Path

from quality_platform.services.test_executor import parse_junit_text
from utils.tools.logger import log

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def list_test_files(test_path: str) -> list[str]:
    """把执行目标拆成单个测试文件（相对项目根）：
    - 目录：递归 glob test_*.py
    - 文件：自身
    """
    p = PROJECT_ROOT / test_path
    if p.is_file():
        return [str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")]
    files = sorted(glob.glob(str(PROJECT_ROOT / test_path / "**" / "test_*.py"),
                             recursive=True))
    return [str(Path(f).relative_to(PROJECT_ROOT)).replace("\\", "/") for f in files]


def check_worker(url: str, timeout: float = 3.0) -> bool:
    """健康检查：worker 存活且空闲优先（busy 也算存活）。"""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=timeout) as r:
            return json.loads(r.read()).get("ok") is True
    except Exception:
        return False


def _post_worker(url: str, payload: dict, timeout: int = 1800) -> dict:
    req = urllib.request.Request(
        url.rstrip("/") + "/run",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def run_distributed(test_path: str, workers: list[str], reruns: int = 0,
                    parallel: int = 0, timeout: int = 0, marker: str = "",
                    timeout_total: int = 1800) -> dict:
    """分发执行。返回：
    {"results": 合并后的用例结果, "workers_used": 实际参与节点,
     "errors": 节点错误列表, "fallback_local": 是否需本地兜底}
    """
    files = list_test_files(test_path)
    if not files:
        return {"results": [], "workers_used": [], "errors": [f"无测试文件：{test_path}"],
                "fallback_local": True}

    alive = [w for w in workers if check_worker(w)]
    if not alive:
        log.warning(f"[分布式] 无可用 worker（{workers}），降级本地执行")
        return {"results": [], "workers_used": [], "errors": ["所有 worker 不可用"],
                "fallback_local": True}

    # Round-Robin 文件分片
    assignments: dict[str, list[str]] = {w: [] for w in alive}
    for i, f in enumerate(files):
        assignments[alive[i % len(alive)]].append(f)

    log.info(f"[分布式] 分发 {len(files)} 个文件 -> {len(alive)} 个 worker："
             + ", ".join(f"{w}:{len(fl)}个" for w, fl in assignments.items()))

    out = {"results": [], "workers_used": [], "errors": []}
    lock = threading.Lock()

    def _run_one(worker: str, file_list: list[str]):
        try:
            resp = _post_worker(worker, {
                "test_paths": file_list, "reruns": reruns, "parallel": parallel,
                "timeout": timeout, "marker": marker, "timeout_total": timeout_total,
            })
            with lock:
                if resp.get("ok"):
                    out["workers_used"].append(worker)
                    if resp.get("junit_xml"):
                        out["results"].extend(parse_junit_text(resp["junit_xml"]))
                    if resp.get("error"):
                        out["errors"].append(f"{worker}: {resp['error'][:200]}")
                else:
                    out["errors"].append(f"{worker}: {resp.get('error', '未知错误')}")
        except Exception as exc:  # noqa: BLE001
            with lock:
                out["errors"].append(f"{worker}: {type(exc).__name__}: {str(exc)[:200]}")

    threads = [threading.Thread(target=_run_one, args=(w, fl))
               for w, fl in assignments.items() if fl]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return out


def workers_status(worker_urls: list[str]) -> list[dict]:
    """实时查询配置的 worker 健康状态（平台 /api/workers 用）。"""
    result = []
    for url in worker_urls:
        try:
            with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=3) as r:
                info = json.loads(r.read())
            result.append({"url": url, "ok": True, **info})
        except Exception as exc:
            result.append({"url": url, "ok": False, "error": str(exc)[:100]})
    return result
