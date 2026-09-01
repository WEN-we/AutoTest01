"""
质量工程平台 - 定时执行调度器（大厂 nightly 回归标配）

能力：
- 支持两类调度：daily（每天固定 HH:MM 跑一次）/ interval（每 N 小时跑一次）
- 后台守护线程轮询调度表，到点触发 TestExecutor
- 调度任务持久化在 SQLite（schedules 表），平台重启不丢失

用法（由 app.py 在启动时调用）：
    from quality_platform.services.scheduler import scheduler
    scheduler.start()            # 启动守护线程
    scheduler.add_daily("22:00", "tests/test_smoke/", reruns=1)
    scheduler.add_interval(6, "tests/test_api/", parallel=2)
"""
import threading
import time
from datetime import datetime, timedelta

from utils.tools.logger import log
from quality_platform.models import db
from quality_platform.services.test_executor import executor

_SCHEMA_SCHEDULES = """
CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,               -- daily / interval
    cron_value  TEXT NOT NULL,               -- daily: "HH:MM" / interval: 小时数
    test_path   TEXT NOT NULL,
    reruns      INTEGER DEFAULT 0,
    parallel    INTEGER DEFAULT 0,
    enabled     INTEGER DEFAULT 1,
    last_run    TEXT
);
"""


class Scheduler:
    """轻量定时调度器（每日 / 每 N 小时）"""

    POLL_SECONDS = 30

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    # ---------- 生命周期 ----------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        with db._conn() as conn:
            conn.executescript(_SCHEMA_SCHEDULES)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("[平台] 定时调度器已启动")

    def stop(self):
        self._stop.set()

    # ---------- 调度管理 API ----------
    def add_daily(self, hhmm: str, test_path: str, name: str = "每日回归",
                  reruns: int = 1, parallel: int = 0) -> int:
        return self.add(name, "daily", hhmm, test_path, reruns, parallel)

    def add_interval(self, hours: int, test_path: str, name: str = "周期回归",
                     reruns: int = 1, parallel: int = 0) -> int:
        return self.add(name, "interval", str(hours), test_path, reruns, parallel)

    def add(self, name: str, kind: str, cron_value: str, test_path: str,
            reruns: int = 0, parallel: int = 0) -> int:
        with db._conn() as conn:
            cur = conn.execute(
                "INSERT INTO schedules (name, kind, cron_value, test_path, reruns, parallel) "
                "VALUES (?,?,?,?,?,?)",
                (name, kind, cron_value, test_path, reruns, parallel),
            )
            return cur.lastrowid

    def list(self) -> list[dict]:
        with db._conn() as conn:
            rows = conn.execute("SELECT * FROM schedules ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def delete(self, schedule_id: int):
        with db._conn() as conn:
            conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))

    def toggle(self, schedule_id: int, enabled: bool):
        with db._conn() as conn:
            conn.execute("UPDATE schedules SET enabled=? WHERE id=?", (int(enabled), schedule_id))

    # ---------- 调度主循环 ----------
    def _loop(self):
        while not self._stop.is_set():
            try:
                for s in self.list():
                    # 单条调度异常不阻断其余调度（cron 数据损坏等仅记录告警，本轮跳过）
                    try:
                        if not s["enabled"]:
                            continue
                        if self._should_run(s):
                            log.info(f"[平台] 触发定时执行：{s['name']} -> {s['test_path']}")
                            executor.run_async(s["test_path"], reruns=s["reruns"],
                                               parallel=s["parallel"])
                            with db._conn() as conn:
                                conn.execute(
                                    "UPDATE schedules SET last_run=? WHERE id=?",
                                    (datetime.now().isoformat(timespec="seconds"), s["id"]),
                                )
                    except Exception as exc:
                        log.warning(f"[平台] 调度 #{s.get('id')} 处理异常（本轮跳过）：{exc}")
            except Exception as exc:
                log.warning(f"[平台] 调度循环异常：{exc}")
            self._stop.wait(self.POLL_SECONDS)

    def _should_run(self, s: dict) -> bool:
        now = datetime.now()
        if s["kind"] == "daily":
            hh, mm = s["cron_value"].split(":")
            target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            # 触发条件：当前时间落在目标点之后的轮询窗口内，且今天尚未跑过
            if target <= now <= target + timedelta(seconds=self.POLL_SECONDS + 5):
                return self._last_run_date(s) != now.date().isoformat()
        elif s["kind"] == "interval":
            hours = float(s["cron_value"])
            last = s["last_run"]
            if not last:
                return True
            try:
                last_dt = datetime.fromisoformat(last)
                return now - last_dt >= timedelta(hours=hours)
            except ValueError:
                return False
        return False

    def _last_run_date(self, s: dict) -> str:
        if not s["last_run"]:
            return ""
        try:
            return datetime.fromisoformat(s["last_run"]).date().isoformat()
        except ValueError:
            return ""


def validate_cron(kind: str, cron_value: str) -> str | None:
    """调度时间入参校验（API 创建入口与数据完整性共用）。
    返回错误描述；合法返回 None。
    - daily: 必须 HH:MM，小时 00-23、分钟 00-59
    - interval: 必须正数小时（0 < x <= 720）
    """
    kind = (kind or "").strip().lower()
    cron_value = str(cron_value or "").strip()
    if kind == "daily":
        parts = cron_value.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return "daily 调度时间必须为 HH:MM 格式（如 22:00）"
        hh, mm = int(parts[0]), int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return "daily 调度时间越界：小时 00-23、分钟 00-59"
        return None
    if kind == "interval":
        try:
            hours = float(cron_value)
        except ValueError:
            return "interval 调度必须为小时数（如 6）"
        if not (0 < hours <= 720):
            return "interval 调度小时数必须为正数且不超过 720（30 天）"
        return None
    return "kind 必须为 daily / interval"


scheduler = Scheduler()
