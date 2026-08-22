"""
失败指纹聚类（Failure Fingerprinting）—— 对标 Google 测试工程 / 字节 flaky 治理

原理：失败用例按「错误类型 + 错误信息指纹」聚簇，识别同一根因的 N 个失败。
- 指纹 = (error_type, error_message 前 N 字符规范化)
- 聚类后：每个簇 = 一个"根因"，展示影响用例数与代表用例，避免逐个重复排查

用法：
    from quality_platform.services.failure_clustering import cluster_failures
    clusters = cluster_failures()
"""
import hashlib
import re
from collections import defaultdict

from quality_platform.models import db

FINGERPRINT_CHARS = 60          # 取错误信息前多少字符作为指纹
_SKIP_TOKENS = re.compile(r"\b(\d+|[0-9a-f]{8,}|0x[0-9a-f]+)\b", re.I)  # 去数字/长hex


def _normalize(text: str) -> str:
    """规范化错误信息：去数字/hex/时间戳，避免同根因不同细节被拆散。"""
    t = _SKIP_TOKENS.sub("#", text or "")
    return t.strip()[:FINGERPRINT_CHARS]


def cluster_failures(limit: int = 200) -> dict:
    """对最近失败聚簇。返回簇列表（按影响面降序）。"""
    failures = db.recent_failures(limit=limit)
    groups: dict[str, list] = defaultdict(list)
    for f in failures:
        key = f"{f.get('error_type') or 'Unknown'}::{_normalize(f.get('error_message') or '')}"
        groups[key].append(f)

    clusters = []
    for key, items in groups.items():
        error_type, fingerprint = key.split("::", 1)
        clusters.append({
            "id": hashlib.md5(key.encode()).hexdigest()[:8],
            "error_type": error_type,
            "fingerprint": fingerprint or "(无错误信息)",
            "count": len(items),
            "case_ids": [i["id"] for i in items],
            "sample_nodeid": items[0]["nodeid"],
            "latest": max(i.get("exec_time") or "" for i in items),
        })
    clusters.sort(key=lambda c: c["count"], reverse=True)
    return {"clusters": clusters, "total_failures": len(failures),
            "root_causes": len(clusters)}
