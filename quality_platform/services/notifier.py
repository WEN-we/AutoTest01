"""
质量工程平台 - 失败/结果通知（大厂：失败自动告警，钉钉/企微/通用 webhook）

配置：quality_platform/config/platform_config.yaml -> notify
    notify:
      enabled: true
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
      # 支持 ${ENV_VAR} 透传，如 ${DINGTALK_WEBHOOK}

发送失败不影响主流程（仅记 warning）。
"""
import os
import re

import requests

from utils.tools.logger import log
from quality_platform.models import db

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "config", "platform_config.yaml")
_ENV_VAR = re.compile(r"^\$\{(\w+)\}$")


def _load_notify_cfg() -> dict:
    try:
        import yaml
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f).get("notify", {})
        url = cfg.get("webhook_url", "")
        m = _ENV_VAR.match(str(url))
        if m:
            cfg["webhook_url"] = os.environ.get(m.group(1), "")
        return cfg
    except Exception:
        return {}


def _build_payload(execution: dict, failures: list[dict]) -> dict:
    """钉钉/企微通用 markdown 格式（失败用例带自动归因结论）。"""
    pass_rate = round(execution["passed"] / max(execution["total"], 1) * 100, 1)
    fail_lines = "\n".join(
        f"- {f['nodeid']}（{f.get('error_type') or '未知'}）"
        + (f" → **{f.get('ana_category')}**" if f.get("ana_category") else "")
        for f in failures[:5]
    ) or "- 无"
    text = (
        f"## 测试执行完成 #{execution['id']}\n"
        f"- 路径：{execution['test_path']}\n"
        f"- 结果：通过 {execution['passed']}/{execution['total']}（{pass_rate}%），"
        f"失败 {execution['failed']}，跳过 {execution['skipped']}\n"
        f"- 耗时：{execution['duration']}s\n"
        f"### 失败用例（自动归因）\n{fail_lines}"
    )
    return {
        "msgtype": "markdown",
        "markdown": {"title": f"测试执行 #{execution['id']}：{pass_rate}%",
                     "text": text},
    }


def send_execution_summary(execution_id: int) -> bool:
    """执行完成后推送摘要；无配置/失败返回 False 不阻塞。"""
    cfg = _load_notify_cfg()
    url = cfg.get("webhook_url", "")
    if not cfg.get("enabled") or not url:
        return False
    execution = db.get_execution(execution_id)
    if not execution or execution["status"] != "finished":
        return False
    failures = [c for c in db.list_case_results(execution_id)
                if c["status"] in ("failed", "error")]
    try:
        resp = requests.post(url, json=_build_payload(execution, failures), timeout=10)
        if resp.status_code == 200:
            log.info(f"[平台] 通知已发送：exec={execution_id}")
            return True
        log.warning(f"[平台] 通知失败：HTTP {resp.status_code} {resp.text[:100]}")
    except Exception as exc:
        log.warning(f"[平台] 通知异常：{exc}")
    return False
