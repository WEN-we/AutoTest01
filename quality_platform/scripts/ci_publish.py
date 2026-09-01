"""CI 结果回传平台（GitHub Actions / Jenkins 等通用）。

读取 JUnit XML，POST 到平台 /api/ci/ingest，汇入与平台执行完全相同的
入库/自动归因/通知/告警管线（集中化：CI 与平台共享一个事实源）。

环境变量（未配置则静默跳过，绝不影响 CI 本身结果）：
    PLATFORM_URL      平台地址，如 http://127.0.0.1:8081
    PLATFORM_CI_TOKEN 回写令牌（= 平台侧 PLATFORM_CI_TOKEN 或 PLATFORM_SECRET）

用法（在 CI 的测试步骤之后）：
    python quality_platform/scripts/ci_publish.py --junit reports/platform/junit-unit.xml --source ci-unit
"""
import argparse
import json
import os
import sys
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(description="把 JUnit 测试结果回传质量平台")
    ap.add_argument("--junit", required=True, help="JUnit XML 文件路径")
    ap.add_argument("--source", default="github-actions", help="来源标识（显示在执行中心）")
    ap.add_argument("--test-path", default="", help="显示用测试路径（默认 ci:<source>）")
    args = ap.parse_args()

    url = os.getenv("PLATFORM_URL", "").strip()
    token = os.getenv("PLATFORM_CI_TOKEN", "").strip()
    if not url or not token:
        print("[ci_publish] 未配置 PLATFORM_URL / PLATFORM_CI_TOKEN，跳过回传（不影响 CI）")
        return 0
    if not os.path.exists(args.junit):
        print(f"[ci_publish] 未找到 {args.junit}，跳过回传")
        return 0

    with open(args.junit, encoding="utf-8", errors="replace") as f:
        xml_text = f.read()
    body = json.dumps({
        "junit_xml": xml_text,
        "source": args.source,
        "test_path": args.test_path or f"ci:{args.source}",
    }).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/ci/ingest", data=body,
        headers={"Content-Type": "application/json", "X-CI-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[ci_publish] 回传成功 HTTP {resp.status}：{resp.read().decode()[:200]}")
    except Exception as exc:  # noqa: BLE001  回传失败不影响 CI 结果
        print(f"[ci_publish] 回传失败（不影响 CI 结果）：{exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
