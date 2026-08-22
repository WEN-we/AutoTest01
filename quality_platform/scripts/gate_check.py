#!/usr/bin/env python
"""
质量门禁检查脚本（CI 独立门禁，不依赖平台数据库）

对标大厂：CI 流水线中测试完成后，按阈值判定是否放行（FAIL 则 workflow 失败）。

用法（CI）：
    python quality_platform/scripts/gate_check.py \
        --junit-xml reports/platform/junit.xml \
        --min-pass-rate 80 --max-fail 5

退出码：
    0 = PASS / WARN（放行）
    1 = FAIL（门禁不过，CI 应失败）
"""
import argparse
import sys
import xml.etree.ElementTree as ET


def parse_junit(xml_path: str) -> dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    total = passed = failed = skipped = 0
    for case in root.iter("testcase"):
        total += 1
        if case.find("failure") is not None or case.find("error") is not None:
            failed += 1
        elif case.find("skipped") is not None:
            skipped += 1
        else:
            passed += 1
    return {"total": total, "passed": passed, "failed": failed, "skipped": skipped}


def evaluate(stats: dict, min_pass_rate: float, max_fail: int) -> tuple[str, list[dict]]:
    total = stats["total"]
    pass_rate = round(stats["passed"] / total * 100, 1) if total else 0.0
    rules = [
        {"name": "通过率", "actual": f"{pass_rate}%", "threshold": f"{min_pass_rate}%",
         "violated": pass_rate < min_pass_rate},
        {"name": "失败用例数", "actual": f"{stats['failed']} 个", "threshold": f"{max_fail} 个",
         "violated": stats["failed"] > max_fail},
    ]
    status = "FAIL" if any(r["violated"] for r in rules) else "PASS"
    return status, rules


def main() -> int:
    parser = argparse.ArgumentParser(description="质量门禁检查（CI）")
    parser.add_argument("--junit-xml", required=True, help="pytest --junitxml 输出文件")
    parser.add_argument("--min-pass-rate", type=float, default=80.0, help="最低通过率 %")
    parser.add_argument("--max-fail", type=int, default=5, help="最大允许失败数")
    args = parser.parse_args()

    try:
        stats = parse_junit(args.junit_xml)
    except Exception as exc:
        print(f"❌ 门禁失败：无法解析 junit 文件 {args.junit_xml}：{exc}")
        return 1

    status, rules = evaluate(stats, args.min_pass_rate, args.max_fail)
    print(f"=== 质量门禁检查 ===")
    print(f"用例总数 {stats['total']} | 通过 {stats['passed']} | "
          f"失败 {stats['failed']} | 跳过 {stats['skipped']}")
    for r in rules:
        mark = "✗" if r["violated"] else "✓"
        print(f"  [{mark}] {r['name']}：{r['actual']}（阈值 {r['threshold']}）")
    print(f"门禁结果：{'❌ FAIL（阻止发布）' if status == 'FAIL' else '✅ PASS'}")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
