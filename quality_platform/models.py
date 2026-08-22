"""
质量工程平台 - SQLite 数据访问层

设计（大厂质量平台简化落地）：
- 零运维：SQLite 单文件（quality_platform/data/quality.db），首次运行自动建表
- 三张核心表：
    executions   执行批次（一次 pytest 运行）
    case_results 单用例结果（nodeid/状态/错误/截图），归属某次执行
    ai_analysis  AI 归因结果缓存（失败用例 -> 分析结论）
- 线程安全：每次操作独立连接（连接后即用即关）

用法：
    from quality_platform.models import db
    db.init_db()
    exec_id = db.insert_execution("tests/test_api/")
"""
import os
import sqlite3
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "quality.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS executions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    test_path     TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'running',   -- running/finished
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    duration      REAL,
    total         INTEGER DEFAULT 0,
    passed        INTEGER DEFAULT 0,
    failed        INTEGER DEFAULT 0,
    skipped       INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS case_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id  INTEGER NOT NULL,
    nodeid        TEXT NOT NULL,
    status        TEXT NOT NULL,                      -- passed/failed/skipped/error
    duration      REAL DEFAULT 0,
    error_type    TEXT,
    error_message TEXT,
    screenshot    TEXT
);
CREATE INDEX IF NOT EXISTS idx_case_exec ON case_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_case_nodeid ON case_results(nodeid);
CREATE TABLE IF NOT EXISTS ai_analysis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_result_id INTEGER NOT NULL,
    category      TEXT,
    confidence    REAL,
    suggestion    TEXT,
    key_evidence  TEXT,
    source        TEXT,                               -- llm / rule
    analyzed_at   TEXT
);
"""


class _Database:
    def __init__(self):
        self.path = DB_PATH

    # ---------- 基础 ----------
    def init_db(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self):
        os.makedirs(DATA_DIR, exist_ok=True)  # 首次连接自动建目录，避免未 init_db 时报错
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ---------- executions ----------
    def insert_execution(self, test_path: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO executions (test_path, status, started_at) VALUES (?, 'running', ?)",
                (test_path, datetime.now().isoformat(timespec="seconds")),
            )
            return cur.lastrowid

    def finish_execution(self, exec_id: int, total: int, passed: int,
                         failed: int, skipped: int, duration: float):
        with self._conn() as conn:
            conn.execute(
                "UPDATE executions SET status='finished', total=?, passed=?, failed=?, "
                "skipped=?, duration=?, finished_at=? WHERE id=?",
                (total, passed, failed, skipped, duration,
                 datetime.now().isoformat(timespec="seconds"), exec_id),
            )

    def list_executions(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM executions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_execution(self, exec_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM executions WHERE id=?", (exec_id,)).fetchone()
            return dict(row) if row else None

    # ---------- case_results ----------
    def insert_case_result(self, exec_id: int, nodeid: str, status: str,
                           duration: float = 0.0, error_type: str = "",
                           error_message: str = "", screenshot: str = ""):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO case_results (execution_id, nodeid, status, duration, "
                "error_type, error_message, screenshot) VALUES (?,?,?,?,?,?,?)",
                (exec_id, nodeid, status, duration, error_type or None,
                 error_message or None, screenshot or None),
            )

    def list_case_results(self, exec_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM case_results WHERE execution_id=?", (exec_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def recent_failures(self, limit: int = 100) -> list[dict]:
        """最近失败用例（按执行批次倒序），带所属执行信息。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT c.*, e.started_at AS exec_time, e.id AS exec_id "
                "FROM case_results c JOIN executions e ON c.execution_id = e.id "
                "WHERE c.status IN ('failed','error') ORDER BY c.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def recent_records(self, limit: int = 500) -> list[dict]:
        """最近用例结果（供 flaky 识别）"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT nodeid, status FROM case_results "
                "WHERE status != 'skipped' ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- ai_analysis ----------
    def upsert_analysis(self, case_result_id: int, result: dict):
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM ai_analysis WHERE case_result_id=?", (case_result_id,)
            )
            conn.execute(
                "INSERT INTO ai_analysis (case_result_id, category, confidence, "
                "suggestion, key_evidence, source, analyzed_at) VALUES (?,?,?,?,?,?,?)",
                (case_result_id, result.get("category"), result.get("confidence"),
                 result.get("suggestion"), result.get("key_evidence"),
                 result.get("source"), datetime.now().isoformat(timespec="seconds")),
            )

    def get_analysis(self, case_result_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ai_analysis WHERE case_result_id=?", (case_result_id,)
            ).fetchone()
            return dict(row) if row else None


db = _Database()
db.init_db()  # 模块加载即建表（幂等），平台/脚本无需手动初始化
