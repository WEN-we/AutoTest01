"""
平台可观测性（监控告警，P2）：
- 健康检查：DB 连通性 / 后端类型 / worker 节点 / 执行队列
- 执行指标：近 N 天按天统计、累计指标（执行数/通过率/失败/LLM 归因次数）
- 告警规则：最近执行失败率超阈值 -> 审计留痕 + 返回告警（供页面/webhook）
"""
from collections import defaultdict
from datetime import datetime, timedelta

from quality_platform.models import db
from utils.tools.logger import log


def db_health() -> dict:
    """DB 连通性 + 后端类型。"""
    try:
        with db._conn() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"ok": True, "backend": db.backend}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "backend": db.backend, "error": str(exc)[:200]}


def daily_stats(days: int = 7) -> list[dict]:
    """近 N 天按天执行统计（Python 侧分组，双后端无方言差异）。
    按 started_at 日期在 SQL 侧过滤，避免大执行量下 1000 条上限截断窗口。"""
    today = datetime.now().date()
    start = (today - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    runs = db.list_executions_since(since=start)

    per_day: dict[str, dict] = defaultdict(
        lambda: {"runs": 0, "total": 0, "passed": 0, "failed": 0, "skipped": 0})
    for r in runs:
        day = (r.get("started_at") or "")[:10]
        if day and day >= start:
            d = per_day[day]
            d["runs"] += 1
            d["total"] += r["total"] or 0
            d["passed"] += r["passed"] or 0
            d["failed"] += r["failed"] or 0
            d["skipped"] += r["skipped"] or 0

    out = []
    for i in range(days):
        day = (today - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        d = dict(per_day.get(day, {"runs": 0, "total": 0, "passed": 0,
                                   "failed": 0, "skipped": 0}))
        d["date"] = day
        d["pass_rate"] = round(d["passed"] / d["total"] * 100, 1) if d["total"] else 0.0
        out.append(d)
    return out


def cumulative_stats() -> dict:
    """累计指标：执行次数/用例数/通过率/失败数/LLM 归因次数。"""
    runs = db.list_executions(limit=1000)
    total_cases = sum(r["total"] or 0 for r in runs)
    passed = sum(r["passed"] or 0 for r in runs)
    failed = sum(r["failed"] or 0 for r in runs)

    llm_count = 0
    try:
        with db._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM ai_analysis WHERE source='llm'").fetchone()
            llm_count = row["c"] if row else 0
    except Exception:  # noqa: BLE001
        pass

    return {
        "runs": len(runs),
        "total_cases": total_cases,
        "pass_rate": round(passed / total_cases * 100, 1) if total_cases else 0.0,
        "failed_cases": failed,
        "llm_analysis_count": llm_count,
        "backend": db.backend,
    }


def check_alerts(fail_rate_threshold: float = 80.0) -> list[dict]:
    """检查最近执行是否触发告警规则：
    - fail_rate：单次执行失败率 >= 阈值（默认 80%）
    遍历近 20 次已完成执行，逐条评估；同一执行只告警一次（已写审计则跳过），
    触发时写审计留痕（action=alert），返回本次新触发的告警列表。
    """
    runs = [r for r in db.list_executions(limit=20)
            if r.get("status") == "finished"]
    if not runs:
        return []
    # 已告警过的 exec_id（避免重复告警刷屏）
    try:
        with db._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT target FROM audit_log "
                "WHERE action='alert' AND target != ''").fetchall()
        alerted = {str(r["target"]) for r in rows}
    except Exception:  # noqa: BLE001
        alerted = set()

    alerts: list[dict] = []
    for latest in runs:
        if not latest["total"] or str(latest["id"]) in alerted:
            continue
        fail_rate = latest["failed"] / latest["total"] * 100
        if fail_rate < fail_rate_threshold:
            continue
        alert = {
            "level": "critical", "type": "fail_rate",
            "exec_id": latest["id"], "test_path": latest["test_path"],
            "fail_rate": round(fail_rate, 1),
            "threshold": fail_rate_threshold,
            "time": datetime.now().isoformat(timespec="seconds"),
        }
        alerts.append(alert)
        try:
            db.insert_audit("system", "alert", target=str(latest["id"]),
                            detail=(f"失败率 {fail_rate:.1f}% 超阈值 "
                                    f"{fail_rate_threshold}%（{latest['test_path']}）"),
                            ok=False)
            log.warning(f"[平台] 告警：exec={latest['id']} 失败率 {fail_rate:.1f}% "
                        f"超阈值 {fail_rate_threshold}%")
        except Exception:  # noqa: BLE001
            pass
    return alerts
