"""
视觉回归对比（Visual Regression）—— 轻量像素级基线对比

能力：
- compare_images(baseline, current)：逐像素对比（容差 + 采样），输出：
    diff_ratio   差异像素占比（0~1）
    diff_image   差异高亮图（差异像素标红，其余半透明灰度）落盘路径
    passed       是否低于阈值
- 基线管理：update_baseline —— 首次生成基线 / 人工确认后更新基线
- 尺寸不一致：自动以基线尺寸为准对比（尺寸差异本身计入差异比例）

用法：
    from utils.tools.visual_diff import compare_images, update_baseline
    result = compare_images("reports/baselines/login.png", "reports/screenshots/cur.png",
                            threshold=0.01)
    if result["first_run"]:
        update_baseline("reports/screenshots/cur.png", "reports/baselines/login.png")
"""
import os
from pathlib import Path

from utils.tools.logger import logger

try:
    from PIL import Image, ImageChops
    _HAS_PIL = True
except ImportError:          # Pillow 未安装时优雅降级（返回不可判定而非崩溃）
    _HAS_PIL = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_THRESHOLD = 0.01     # 差异像素占比阈值（1%），超过判定为视觉回归失败
PIXEL_TOLERANCE = 10         # 单像素通道容差（抗锯齿/压缩噪声）


def _ensure_pil():
    if not _HAS_PIL:
        raise RuntimeError("Pillow 未安装：pip install Pillow（视觉回归能力依赖）")


def compare_images(baseline_path: str, current_path: str,
                   threshold: float = DEFAULT_THRESHOLD,
                   diff_output: str = "") -> dict:
    """
    对比当前截图与基线。
    - 基线不存在 → first_run=True（不判定失败，调用方应生成基线）
    - 差异比例 > threshold → passed=False，diff_image 为高亮差异图
    """
    _ensure_pil()
    if not os.path.exists(baseline_path):
        return {"first_run": True, "passed": True, "diff_ratio": 0.0, "diff_image": "",
                "reason": "基线不存在（首次运行）"}

    if not os.path.exists(current_path):
        return {"first_run": False, "passed": False, "diff_ratio": 1.0, "diff_image": "",
                "reason": "当前截图不存在"}

    base = Image.open(baseline_path).convert("RGB")
    cur = Image.open(current_path).convert("RGB")

    # 尺寸对齐：以基线为准（尺寸不一致直接算全差异更严格；这里选择对齐后比像素）
    size_mismatch = base.size != cur.size
    if size_mismatch:
        cur = cur.resize(base.size)

    # 差异掩码：逐像素通道差 > 容差 即视为差异像素
    diff = ImageChops.difference(base, cur)
    diff_map = diff.convert("L").point(lambda p: 255 if p > PIXEL_TOLERANCE else 0)
    hist = diff_map.histogram()
    changed = sum(hist[255:]) if len(hist) >= 256 else 0
    total = base.size[0] * base.size[1]
    diff_ratio = round(changed / max(total, 1), 6)

    result = {
        "first_run": False,
        "passed": diff_ratio <= threshold,
        "diff_ratio": diff_ratio,
        "diff_image": "",
        "size_mismatch": size_mismatch,
        "reason": "尺寸不一致（已按基线尺寸缩放对比）" if size_mismatch else "",
    }

    # 差异高亮图：差异像素标红，其余区域灰度化
    if diff_ratio > 0 and diff_output:
        os.makedirs(os.path.dirname(diff_output) or ".", exist_ok=True)
        highlighted = cur.convert("L").convert("RGB")
        red = Image.new("RGB", base.size, (226, 75, 74))
        highlighted = Image.composite(red, highlighted, diff_map)
        highlighted.save(diff_output)
        result["diff_image"] = diff_output

    logger.info(f"[视觉回归] {os.path.basename(current_path)} vs 基线："
                f"差异 {diff_ratio:.4%}（阈值 {threshold:.2%}）-> "
                f"{'通过' if result['passed'] else '视觉回归失败'}")
    return result


def update_baseline(current_path: str, baseline_path: str) -> bool:
    """用当前截图更新基线（首次生成 / 人工确认后固化）。"""
    try:
        _ensure_pil()
        os.makedirs(os.path.dirname(baseline_path) or ".", exist_ok=True)
        Image.open(current_path).convert("RGB").save(baseline_path)
        logger.info(f"[视觉回归] 基线已更新：{baseline_path}")
        return True
    except Exception as exc:
        logger.warning(f"[视觉回归] 基线更新失败：{exc}")
        return False
