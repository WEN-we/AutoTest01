"""
自愈定位器（Self-Healing Locator）—— 大厂智能测试招牌能力

原理（对标 Healenium 的轻量落地）：
- 主定位器找不到元素时，自动派生候选定位器（语义等价变换）依次尝试：
    #login-btn        -> [data-testid="login-btn"] / [name="login-btn"]
    .submit-btn       -> [class*="submit-btn"]
    text=登录          -> (Playwright 原生文本定位，保持)
    input[placeholder="用户名"] -> 保持（已含语义属性）
- 唯一命中的候选 → 自愈成功，用例继续执行（不打断）
- 自愈事件落盘 reports/self_heal_events.json（供质量平台展示 + 人工审核固化新定位器）
- 全部候选失败 → 抛出原始异常（不吞错误，保证用例真实性）

用法（VelmartWebBasePage 已内建，业务 PO 无感知）：
    page.click("#login-btn")   # 若 #login-btn 失效，自动尝试 [data-testid="login-btn"] 等
"""
import json
import os
import re
from datetime import datetime

from utils.tools.logger import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HEAL_EVENT_FILE = os.path.join(PROJECT_ROOT, "reports", "self_heal_events.json")

# 当前用例 nodeid（conftest 注入；自愈事件溯源到用例）
_current_nodeid = ""


def set_current_nodeid(nodeid: str):
    global _current_nodeid
    _current_nodeid = nodeid or ""


def get_current_nodeid() -> str:
    return _current_nodeid


def derive_candidates(locator: str) -> list[str]:
    """
    从主定位器派生候选定位器（语义等价变换，按优先级排序）。
    只做确定性变换，不做模糊猜测——避免误点击导致用例"假通过"。
    """
    candidates: list[str] = []
    locator = (locator or "").strip()

    # #id -> [data-testid="id"] / [name="id"]（大厂推荐的契约属性优先）
    m = re.fullmatch(r"#([\w-]+)", locator)
    if m:
        sid = m.group(1)
        candidates.append(f'[data-testid="{sid}"]')
        candidates.append(f'[name="{sid}"]')
        candidates.append(f'[id="{sid}"]')  # 显式属性写法（容忍 # 被转义的场景）
        return candidates

    # .class -> [class*="class"]（部分匹配，容忍 class 追加导致的失效）
    m = re.fullmatch(r"\.([\w-]+)", locator)
    if m:
        cls = m.group(1)
        candidates.append(f'[class*="{cls}"]')
        candidates.append(f'[data-testid="{cls}"]')
        return candidates

    # 提取定位器中的可见文本（三种形态依次尝试）
    text = None
    m = re.search(r'has-text\("([^"]+)"\)', locator)      # button:has-text("登录")
    if not m:
        m = re.match(r'text=(.+)$', locator)               # text=登录
    if not m and "[placeholder=" not in locator:
        m = re.search(r'"([^"]{1,30})"', locator)          # 任意双引号文本（兜底）
    if m and m.group(1).strip():
        text = m.group(1).strip()

    if text:
        candidates.append(f'text={text}')
        candidates.append(f'[aria-label="{text}"]')
        return candidates

    # input[placeholder="用户名"] -> 附加语义属性保持（已精确）；补充等价属性
    m = re.search(r'\[placeholder="([^"]+)"\]', locator)
    if m:
        ph = m.group(1)
        candidates.append(f'[aria-label="{ph}"]')
        candidates.append(f'[name="{ph}"]')
        return candidates

    return candidates


def record_heal_event(nodeid: str, original_locator: str, healed_locator: str,
                      description: str = ""):
    """自愈事件落盘（供平台展示与人工审核：自愈 → 人审 → 固化新定位器）。"""
    event = {
        "nodeid": nodeid or _current_nodeid,
        "original_locator": original_locator,
        "healed_locator": healed_locator,
        "description": description,
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        os.makedirs(os.path.dirname(HEAL_EVENT_FILE), exist_ok=True)
        records = []
        if os.path.exists(HEAL_EVENT_FILE):
            with open(HEAL_EVENT_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        records.append(event)
        with open(HEAL_EVENT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning(f"自愈事件落盘失败：{exc}")
    logger.warning(f"⚠️ [自愈定位器] {original_locator} 失效，已自愈为 {healed_locator}"
                   f"（{description or nodeid or '未知用例'}）——请审核后固化新定位器")
    return event
