"""
质量门禁（Quality Gate）—— 对标字节/腾讯发布卡点

逻辑：对最近一次完成的执行，按配置规则判定：
- FAIL：通过率 < min_pass_rate 或失败数 > max_fail_count
- WARN：通过率 < warn_pass_rate 或 flaky 占比 > max_flaky_rate
- PASS：其余

配置：quality_platform/config/platform_config.yaml -> gate
"""
import os

import yaml

from quality_platform.models import db

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config", "platform_config.yaml")


def _load_gate_cfg() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f).get("gate", {})
    except Exception:
        return {}


def evaluate_gate() -> dict:
    """评估最近一次完成的执行，返回门禁结果。"""
    cfg = _load_gate_cfg()
    if not cfg.get("enabled", True):
        return {"status": "disabled", "rules": []}

    runs = db.list_executions(limit=5)
    finished = [r for r in runs if r["status"] == "finished"]
    if not finished:
        return {"status": "no_data", "rules": [], "latest_run": None}

    latest = finished[0]
    total = latest["total"] or 0
    passed = latest["passed"] or 0
    failed = latest["failed"] or 0
    # 空执行（未收集到任何用例，如测试路径不存在）：无数据可评估，不判 FAIL
    if total == 0:
        return {"status": "no_data", "rules": [], "latest_run": None,
                "note": "最近执行未收集到用例（total=0），无可评估数据"}
    pass_rate = round(passed / total * 100, 1) if total else 0.0

    flaky_report = _recent_flaky()
    flaky_count = flaky_report["summary"]["detected_flaky"]
    # flaky 占比分母 = 参与 flaky 判定的用例总数（平台活跃用例，而非本次执行用例数）。
    # 修复：此前误用 latest["total"]，导致"本次只跑 3 条、历史有 8 条 flaky"时占比爆炸（8/3=267%），
    # 全绿执行也被误判 WARN。
    flaky_base = flaky_report["summary"].get("total_cases") or (
        flaky_count + flaky_report["summary"]["stable_fail"] + flaky_report["summary"]["stable_pass"]
    )
    flaky_rate = round(flaky_count / max(flaky_base, 1), 3)

    rules = [
        {"name": "通过率", "actual": pass_rate, "threshold": cfg.get("min_pass_rate", 80.0),
         "unit": "%", "violated": pass_rate < cfg.get("min_pass_rate", 80.0)},
        {"name": "失败用例数", "actual": failed, "threshold": cfg.get("max_fail_count", 5),
         "unit": "个", "violated": failed > cfg.get("max_fail_count", 5)},
        {"name": "flaky 占比", "actual": flaky_rate, "threshold": cfg.get("max_flaky_rate", 0.3),
         "unit": "", "violated": flaky_rate > cfg.get("max_flaky_rate", 0.3)},
    ]

    hard_fail = any(r["violated"] for r in rules[:2])
    warn = pass_rate < cfg.get("warn_pass_rate", 90.0) or rules[2]["violated"]
    status = "FAIL" if hard_fail else ("WARN" if warn else "PASS")

    return {
        "status": status,
        "rules": rules,
        "latest_run": {"id": latest["id"], "test_path": latest["test_path"],
                       "pass_rate": pass_rate, "failed": failed},
    }


def quality_score() -> dict:
    """质量分 0~100：通过率 + 稳定性（flaky 少）+ 执行覆盖。"""
    runs = db.list_executions(limit=10)
    finished = [r for r in runs if r["status"] == "finished"]
    if not finished:
        return {"score": 0, "parts": {}}
    total = sum(r["total"] for r in finished)
    passed = sum(r["passed"] for r in finished)
    pass_rate = passed / total if total else 0

    flaky_report = _recent_flaky()
    flaky_count = flaky_report["summary"]["detected_flaky"]
    # 稳定性基于"参与判定的活跃用例集"计算 flaky 占比（与门禁口径一致），而非执行次数
    flaky_base = flaky_report["summary"].get("total_cases") or (
        flaky_count + flaky_report["summary"]["stable_fail"] + flaky_report["summary"]["stable_pass"]
    )
    stability = max(0.0, 1.0 - flaky_count / max(flaky_base, 1) * 3)  # flaky 越多扣分

    cfg = _load_score_cfg()
    # 统一为 0~100 分制：通过率 + 稳定性（flaky 少）+ 执行覆盖
    score = (
        pass_rate * 100 * cfg["pass_rate_weight"]
        + stability * 100 * cfg["stability_weight"]
        + cfg["coverage_weight"] * 100 * min(1.0, len(finished) / 10)
    )
    return {"score": round(min(score, 100), 1),
            "parts": {"pass_rate": round(pass_rate * 100, 1),
                      "stability": round(stability * 100, 1),
                      "run_coverage": round(min(1.0, len(finished) / 10) * 100, 1)}}


def test_pyramid() -> dict:
    """测试金字塔：按用例类型统计分布（api/ui/smoke/...）。"""
    records = db.recent_records(limit=2000)
    dist: dict[str, int] = {}
    for r in records:
        nodeid = r.get("nodeid", "")
        kind = "other"
        # 兼容两种 nodeid 格式：路径式（tests/test_api/x.py::...）与 junit classname 点分式（tests.test_api.x.TestX::...）
        for key in ("test_api", "test_ui", "test_smoke", "test_selenium",
                    "test_android", "test_ecommerce", "test_performance",
                    "test_whitebox", "test_service"):
            if f"/{key}/" in nodeid or f".{key}." in nodeid:
                kind = key.replace("test_", "")
                break
        dist[kind] = dist.get(kind, 0) + 1
    return {"distribution": dist, "total": sum(dist.values())}


def _recent_flaky():
    from quality_platform.services.ai_integration import ai
    return ai.detect_flaky()


def _load_score_cfg() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f).get("quality_score", {})
    except Exception:
        return {"pass_rate_weight": 0.6, "stability_weight": 0.3, "coverage_weight": 0.1}
