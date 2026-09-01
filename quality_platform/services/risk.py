"""
AI 发布风控（Release Risk Assessment）—— 对标大厂"发布风险评估"，超越传统测试管理工具。

输入信号（全部来自平台内部数据，可解释）：
1. 质量门禁 gate          —— 最近执行 PASS/WARN/FAIL 卡点结果
2. 稳定性 flaky           —— AI flaky 识别（波动用例 / 稳定失败数）
3. 失败聚类 clusters      —— 失败指纹聚类（同因失败聚簇，簇越大风险越高）
4. 近 7 天执行趋势        —— 失败率环比上升触发风险加权

输出：
- level:    low / medium / high / critical
- score:    0~100（100 = 风险最低）
- reasons:  中文可解释理由列表（每条含扣分依据）
- signals:  各信号原始值（供看板展示/导出）

用法：
    from quality_platform.services.risk import assess_release_risk
    assess_release_risk()
"""
from quality_platform.services.failure_clustering import cluster_failures
from quality_platform.services.gate import evaluate_gate


def assess_release_risk() -> dict:
    """综合评估当前发布风险，返回可解释的评级结果。"""
    score = 100.0
    reasons: list[str] = []
    signals: dict = {}

    # ---------- 信号 1：质量门禁 ----------
    gate = evaluate_gate()
    signals["gate"] = gate.get("status")
    if gate.get("status") == "FAIL":
        score -= 45
        reasons.append("质量门禁 FAIL：最近执行未达标（通过率/失败数超阈值），扣 45 分")
    elif gate.get("status") == "WARN":
        score -= 20
        reasons.append("质量门禁 WARN：通过率偏低或 flaky 占比偏高，扣 20 分")
    elif gate.get("status") in ("no_data", "disabled"):
        score -= 10
        reasons.append("无已完成执行可供门禁评估，风险未知，扣 10 分")

    # ---------- 信号 2：稳定性（flaky / 稳定失败） ----------
    try:
        from quality_platform.services.ai_integration import ai
        flaky = ai.detect_flaky()
        detected = flaky["summary"]["detected_flaky"]
        stable_fail = flaky["summary"]["stable_fail"]
    except Exception:  # noqa: BLE001
        detected, stable_fail = 0, 0
    signals["flaky"] = {"detected": detected, "stable_fail": stable_fail}
    if detected >= 5:
        score -= 20
        reasons.append(f"疑似 flaky 用例 {detected} 个（≥5），回归结果不可信，扣 20 分")
    elif detected > 0:
        score -= detected * 3
        reasons.append(f"疑似 flaky 用例 {detected} 个，扣 {detected * 3} 分")
    if stable_fail > 0:
        ded = min(stable_fail * 10, 30)
        score -= ded
        reasons.append(f"稳定失败用例 {stable_fail} 个（连续失败非波动），扣 {ded} 分")

    # ---------- 信号 3：失败聚类（同因失败聚簇） ----------
    try:
        clusters = cluster_failures()
        top = clusters[0] if clusters else None
        top_size = (top.get("count") or 0) if isinstance(top, dict) else 0
    except Exception:  # noqa: BLE001
        top_size = 0
    signals["failure_cluster_top"] = top_size
    if top_size >= 5:
        score -= 15
        reasons.append(f"最大失败簇含 {top_size} 条同因失败（疑似环境/公共依赖问题），扣 15 分")
    elif top_size >= 3:
        score -= 8
        reasons.append(f"最大失败簇含 {top_size} 条同因失败，扣 8 分")

    # ---------- 信号 4：近 7 天失败率趋势 ----------
    trend_delta = _failure_rate_trend()
    signals["failure_rate_trend_delta"] = trend_delta
    if trend_delta >= 10:
        score -= 15
        reasons.append(f"近 3 天失败率较前 4 天上升 {trend_delta:.1f} 个百分点，扣 15 分")
    elif trend_delta >= 5:
        score -= 8
        reasons.append(f"近 3 天失败率较前 4 天上升 {trend_delta:.1f} 个百分点，扣 8 分")

    # ---------- 汇总评级 ----------
    score = max(0.0, round(score, 1))
    if score < 40:
        level = "critical"
    elif score < 60:
        level = "high"
    elif score < 80:
        level = "medium"
    else:
        level = "low"
    if not reasons:
        reasons.append("各信号均正常：门禁通过、无 flaky/稳定失败、无聚簇、趋势平稳")

    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "signals": signals,
        "advice": _advice(level),
    }


def _failure_rate_trend() -> float:
    """近 3 天失败率 - 前 4 天失败率（百分点；无数据返回 0）。"""
    try:
        from quality_platform.services.observability import daily_stats
        days = daily_stats(7)
        recent, earlier = days[-3:], days[:4]

        def _rate(rs):
            t = sum(r["total"] for r in rs)
            f = sum(r["failed"] for r in rs)
            return (f / t * 100) if t else 0.0

        return round(_rate(recent) - _rate(earlier), 1)
    except Exception:  # noqa: BLE001
        return 0.0


def _advice(level: str) -> str:
    return {
        "low": "✅ 可发布：各项质量信号健康",
        "medium": "⚠️ 谨慎发布：存在 flaky 或通过率波动，建议修复后回归",
        "high": "⛔ 暂缓发布：门禁 WARN 或失败聚簇/趋势恶化，需先修复并全量回归",
        "critical": "⛔ 禁止发布：门禁 FAIL 或大面积稳定失败，必须修复后重跑",
    }[level]
