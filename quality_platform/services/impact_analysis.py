"""
精准测试：变更影响面分析（大厂精准测试核心）

原理（Test Impact Analysis）：
- 读取 git 变更文件（diff base...head）
- 按「文件路径前缀 → 测试目录」映射规则（platform_config.yaml -> impact_analysis），
  计算本次变更影响的测试集，只跑受影响的用例（省时、反馈快）
- 未匹配到映射的变更文件走 fallback（默认冒烟集），保证兜底不漏测

用法：
    from quality_platform.services.impact_analysis import analyze_changes
    report = analyze_changes(base="HEAD~1")   # 上一次提交以来的变更
    # report = {"changed_files": [...], "suggested_tests": ["tests/test_api/", ...], ...}
"""
import subprocess
from pathlib import Path

import yaml

from utils.tools.logger import log

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLATFORM_CONFIG = PROJECT_ROOT / "quality_platform" / "config" / "platform_config.yaml"

# 代码内默认映射（yaml 未配置时兜底）；键为变更文件路径前缀，值为建议执行的测试目录
_DEFAULT_MAPPINGS = {
    "local_web_login/": ["tests/test_api/", "tests/test_smoke/", "tests/test_whitebox/"],
    "page_objects/web/": ["tests/test_ui/", "tests/test_ecommerce/", "tests/test_smoke/"],
    "page_objects/android/": ["tests/test_android/"],
    "page_objects/ios/": ["tests/test_ios/"],
    "page_objects/harmony/": ["tests/test_harmony/"],
    "page_objects/windows/": ["tests/test_windows/"],
    "page_objects/linux_gui/": ["tests/test_linux/"],
    "service_objects/": ["tests/test_ecommerce/", "tests/test_service/"],
    "utils/ai/": ["tests/test_platform/"],
    "utils/tools/": ["tests/test_smoke/", "tests/test_platform/"],
    "utils/drivers/": ["tests/test_smoke/"],
    "quality_platform/": ["tests/test_platform/"],
    "tests/": [],          # 特殊：按变更文件所在测试目录精确映射（见 _direct_test_dir）
    "config/": ["tests/test_smoke/"],
}
_DEFAULT_FALLBACK = ["tests/test_smoke/"]  # 无法归类的变更 → 冒烟兜底
# tests/ 根文件（如 conftest.py）影响全局收集与 fixture → 基础可跑集
# （与 conftest.py 的 pytest_ignore_collect 默认收集范围对齐：重依赖端默认不跑）
_ROOT_TESTS_TARGETS = ["tests/test_smoke/", "tests/test_api/",
                       "tests/test_platform/", "tests/test_whitebox/"]


def _load_cfg() -> dict:
    try:
        cfg = yaml.safe_load(PLATFORM_CONFIG.read_text(encoding="utf-8")) \
            .get("impact_analysis", {})
        return {
            "mappings": cfg.get("mappings") or _DEFAULT_MAPPINGS,
            "fallback": cfg.get("fallback") or _DEFAULT_FALLBACK,
        }
    except Exception:
        return {"mappings": _DEFAULT_MAPPINGS, "fallback": _DEFAULT_FALLBACK}


def _git_changed_files(base: str = "HEAD~1") -> list[str]:
    """git diff 变更文件列表（新增/修改/删除均含）。失败返回空列表。
    健壮性：仓库只有 1 个 commit 时 HEAD~1 不存在（fatal: bad revision），
    自动回退到 HEAD（对比工作区与当前提交），保证精准测试永不因 git 状态报错。"""
    for candidate in (base, "HEAD"):
        try:
            proc = subprocess.run(
                ["git", "diff", "--name-only", candidate],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30,
            )
            if proc.returncode == 0:
                return [ln.strip().replace("\\", "/") for ln in proc.stdout.splitlines()
                        if ln.strip()]
            log.warning(f"[精准测试] git diff {candidate} 失败：{proc.stderr.strip()[:120]}"
                        f"（回退下一候选）")
        except Exception as exc:  # noqa: BLE001
            log.warning(f"[精准测试] git 命令异常（{candidate}）：{exc}")
    return []


def _direct_test_dir(changed_file: str) -> str | None:
    """
    变更本身就在 tests/ 下 → 直接定位到所在测试目录（最精确）。
    注意：tests/ 根下的直接文件（如 tests/conftest.py）影响全量，返回 None 走兜底。
    """
    parts = changed_file.split("/")
    if parts[0] == "tests" and len(parts) >= 3:
        return f"tests/{parts[1]}/"
    return None


def analyze_changes(base: str = "HEAD~1") -> dict:
    """
    分析 base 以来的变更，输出建议执行的测试集。
    返回: {
        changed_files: [...],            # 变更文件清单
        suggested_tests: [...],          # 建议执行的测试目录（去重、有序）
        unmatched: [...],                # 未匹配到映射的文件（已走 fallback）
        reasons: {test_dir: [原因...]}   # 每个测试集被选中的依据（可解释性）
    }
    """
    cfg = _load_cfg()
    mappings: dict = cfg["mappings"]
    fallback: list = cfg["fallback"]

    changed = _git_changed_files(base)
    suggested: list[str] = []
    reasons: dict[str, list[str]] = {}
    unmatched: list[str] = []

    def _add(test_dir: str, reason: str):
        if test_dir not in suggested:
            suggested.append(test_dir)
        reasons.setdefault(test_dir, []).append(reason)

    for f in changed:
        direct = _direct_test_dir(f)
        if direct:
            _add(direct, f"测试文件变更：{f}")
            continue
        # tests/ 根文件（tests/conftest.py 等）：影响全局收集与 fixture → 基础可跑集
        if f.startswith("tests/") and "/" not in f[len("tests/"):]:
            for td in _ROOT_TESTS_TARGETS:
                _add(td, f"tests 根文件变更（全局影响）：{f}")
            continue
        matched = False
        for prefix, test_dirs in mappings.items():
            if prefix != "tests/" and f.startswith(prefix):
                for td in test_dirs:
                    _add(td, f"{prefix}* 变更：{f}")
                matched = True
                break
        if not matched:
            unmatched.append(f)
            for td in fallback:
                _add(td, f"未归类变更兜底：{f}")

    report = {
        "base": base,
        "changed_files": changed,
        "suggested_tests": suggested,
        "unmatched": unmatched,
        "reasons": reasons,
        "fallback_used": bool(unmatched),
    }
    log.info(f"[精准测试] 变更 {len(changed)} 个文件 → 建议执行 {len(suggested)} 个测试集"
             f"（兜底命中 {len(unmatched)} 个文件）")
    return report
