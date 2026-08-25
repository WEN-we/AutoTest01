"""
质量工程平台 - 数据访问层（SQLite / PostgreSQL 双后端）

设计（大厂质量平台简化落地）：
- 默认 SQLite：零运维（quality_platform/data/quality.db），首次运行自动建表
- 可选 PostgreSQL：设置环境变量 DB_TYPE=postgres + DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD
  （生产级：并发写、网络访问、备份恢复；SQL 方言由连接包装层自动适配）
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

# ---------- 后端选择 ----------
DB_TYPE = os.getenv("DB_TYPE", "sqlite").strip().lower()   # sqlite / postgres
PG_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432") or 5432),
    "dbname": os.getenv("DB_NAME", "quality_platform"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

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
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',       -- admin / user
    created_at    TEXT
);
CREATE TABLE IF NOT EXISTS cases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeid        TEXT NOT NULL UNIQUE,
    name          TEXT,
    module        TEXT,
    tags          TEXT DEFAULT '',
    owner         TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    status        TEXT DEFAULT 'active',              -- active / disabled
    created_at    TEXT,
    updated_at    TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL,                     -- 操作者（未登录失败尝试记为 anonymous）
    action        TEXT NOT NULL,                     -- login/logout/run_start/cancel/case_add/...
    target        TEXT DEFAULT '',                   -- 操作对象（exec_id/case_id/sched_id 等）
    detail        TEXT DEFAULT '',                   -- 补充信息（失败原因等）
    ip            TEXT DEFAULT '',
    ok            INTEGER DEFAULT 1,                 -- 1 成功 / 0 失败（如登录失败）
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
CREATE TABLE IF NOT EXISTS ai_settings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    provider      TEXT NOT NULL,                      -- deepseek/qwen/doubao/ollama/custom
    base_url      TEXT NOT NULL,
    api_key_enc   TEXT DEFAULT '',                    -- Fernet 加密存储（PLATFORM_SECRET 派生密钥）
    model         TEXT NOT NULL,
    enabled       INTEGER DEFAULT 0,                  -- 1 启用（ai 调用优先走此配置）/ 0 停用
    updated_at    TEXT
);
"""

# PostgreSQL 版 DDL（SERIAL 自增；时间/布尔用兼容类型，代码传值不变）
_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS executions (
    id            SERIAL PRIMARY KEY,
    test_path     TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'running',
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    duration      DOUBLE PRECISION,
    total         INTEGER DEFAULT 0,
    passed        INTEGER DEFAULT 0,
    failed        INTEGER DEFAULT 0,
    skipped       INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS case_results (
    id            SERIAL PRIMARY KEY,
    execution_id  INTEGER NOT NULL,
    nodeid        TEXT NOT NULL,
    status        TEXT NOT NULL,
    duration      DOUBLE PRECISION DEFAULT 0,
    error_type    TEXT,
    error_message TEXT,
    screenshot    TEXT
);
CREATE INDEX IF NOT EXISTS idx_case_exec ON case_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_case_nodeid ON case_results(nodeid);
CREATE TABLE IF NOT EXISTS ai_analysis (
    id            SERIAL PRIMARY KEY,
    case_result_id INTEGER NOT NULL,
    category      TEXT,
    confidence    DOUBLE PRECISION,
    suggestion    TEXT,
    key_evidence  TEXT,
    source        TEXT,
    analyzed_at   TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT
);
CREATE TABLE IF NOT EXISTS cases (
    id            SERIAL PRIMARY KEY,
    nodeid        TEXT NOT NULL UNIQUE,
    name          TEXT,
    module        TEXT,
    tags          TEXT DEFAULT '',
    owner         TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    status        TEXT DEFAULT 'active',
    created_at    TEXT,
    updated_at    TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL,
    action        TEXT NOT NULL,
    target        TEXT DEFAULT '',
    detail        TEXT DEFAULT '',
    ip            TEXT DEFAULT '',
    ok            INTEGER DEFAULT 1,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
CREATE TABLE IF NOT EXISTS ai_settings (
    id            SERIAL PRIMARY KEY,
    provider      TEXT NOT NULL,
    base_url      TEXT NOT NULL,
    api_key_enc   TEXT DEFAULT '',
    model         TEXT NOT NULL,
    enabled       INTEGER DEFAULT 0,
    updated_at    TEXT
);
"""


class _PGCursor:
    """psycopg2 游标包装：让现有 sqlite3 风格的 execute/fetchone/fetchall/lastrowid 直接可用。"""

    def __init__(self, cur):
        self._cur = cur

    @property
    def lastrowid(self):
        """INSERT ... RETURNING id 时取回主键（psycopg2 需显式 fetch）。"""
        row = self._cur.fetchone()
        return row[0] if row else None

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    def close(self):
        self._cur.close()


class _PGConn:
    """psycopg2 连接包装：sqlite3 风格兼容层（`?`→`%s`、INSERT 自动 RETURNING、
    INSERT OR IGNORE → ON CONFLICT DO NOTHING、executescript 拆条执行）。"""

    def __init__(self, conn):
        self._conn = conn
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *exc):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self.close()
        return False

    def close(self):
        if not self.closed:
            try:
                self._conn.close()
            finally:
                self.closed = True

    def _adapt_sql(self, sql: str) -> str:
        """SQLite 方言 → PG 方言（仅差异点，其余原样）。"""
        s = sql.strip()
        has_ignore = s.upper().startswith("INSERT OR IGNORE")
        if has_ignore:
            s = s.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1)
        s = s.replace("?", "%s")
        if has_ignore:
            s = s.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
        elif s.upper().startswith("INSERT") and "RETURNING" not in s.upper():
            s = s.rstrip().rstrip(";") + " RETURNING id"
        return s

    def execute(self, sql, args=None):
        cur = self._conn.cursor()
        try:
            cur.execute(self._adapt_sql(sql), tuple(args) if args else ())
        except Exception:
            cur.close()
            raise
        return _PGCursor(cur)

    def executescript(self, script: str):
        """PG 无 executescript：按分号拆条执行（跳过空语句与注释行）。"""
        cur = self._conn.cursor()
        try:
            for stmt in script.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    cur.execute(stmt)
        finally:
            cur.close()


class _Database:
    def __init__(self):
        self.path = DB_PATH
        self.backend = DB_TYPE   # sqlite / postgres

    # ---------- 基础 ----------
    def init_db(self):
        if self.backend == "postgres":
            with self._conn() as conn:
                conn.executescript(_SCHEMA_PG)
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self):
        if self.backend == "postgres":
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **PG_CONFIG)
            return _PGConn(conn)
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
        """某次执行的用例结果（联表带上 AI 归因字段 ana_*，无归因为 NULL）。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT c.*, a.category AS ana_category, a.confidence AS ana_confidence, "
                "a.suggestion AS ana_suggestion, a.source AS ana_source "
                "FROM case_results c "
                "LEFT JOIN ai_analysis a ON a.case_result_id = c.id "
                "WHERE c.execution_id=? ORDER BY c.id",
                (exec_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def recent_failures(self, limit: int = 100) -> list[dict]:
        """最近失败用例（按执行批次倒序），带所属执行信息与 AI 归因（ana_*）。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT c.*, e.started_at AS exec_time, e.id AS exec_id, "
                "a.category AS ana_category, a.confidence AS ana_confidence, "
                "a.suggestion AS ana_suggestion, a.source AS ana_source "
                "FROM case_results c "
                "JOIN executions e ON c.execution_id = e.id "
                "LEFT JOIN ai_analysis a ON a.case_result_id = c.id "
                "WHERE c.status IN ('failed','error') ORDER BY c.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_case_result(self, case_result_id: int) -> dict | None:
        """按主键查询单条用例结果（含所属执行信息），供失败详情/归因使用。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT c.*, e.started_at AS exec_time, e.id AS exec_id "
                "FROM case_results c JOIN executions e ON c.execution_id = e.id "
                "WHERE c.id=?",
                (case_result_id,),
            ).fetchone()
            return dict(row) if row else None

    def recent_records(self, limit: int = 500) -> list[dict]:
        """最近用例结果（供 flaky 识别）"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT nodeid, status FROM case_results "
                "WHERE status != 'skipped' ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- cases（用例库管理）----------
    def list_cases(self, module: str = "", keyword: str = "", limit: int = 500) -> list[dict]:
        sql = "SELECT * FROM cases WHERE 1=1"
        args: list = []
        if module:
            sql += " AND module=?"
            args.append(module)
        if keyword:
            sql += " AND (nodeid LIKE ? OR name LIKE ? OR tags LIKE ?)"
            kw = f"%{keyword}%"
            args += [kw, kw, kw]
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, args).fetchall()
            return [dict(r) for r in rows]

    def upsert_case(self, nodeid: str, name: str = "", module: str = "",
                    tags: str = "", owner: str = "", description: str = "",
                    status: str = "active") -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._conn() as conn:
            row = conn.execute("SELECT id FROM cases WHERE nodeid=?", (nodeid,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE cases SET name=?, module=?, tags=?, owner=?, description=?, "
                    "status=?, updated_at=? WHERE id=?",
                    (name, module, tags, owner, description, status, now, row["id"]),
                )
                return row["id"]
            cur = conn.execute(
                "INSERT INTO cases (nodeid, name, module, tags, owner, description, "
                "status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (nodeid, name, module, tags, owner, description, status, now, now),
            )
            return cur.lastrowid

    def update_case(self, case_id: int, **fields) -> bool:
        allowed = {"name", "module", "tags", "owner", "description", "status"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return False
        sets["updated_at"] = datetime.now().isoformat(timespec="seconds")
        cols = ", ".join(f"{k}=?" for k in sets)
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE cases SET {cols} WHERE id=?", (*sets.values(), case_id)
            )
            return cur.rowcount > 0

    def delete_case(self, case_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM cases WHERE id=?", (case_id,))
            return cur.rowcount > 0

    def import_cases(self, nodeids: list[str]) -> dict:
        """批量导入用例（从 pytest collect），返回新增/更新统计。"""
        imported, updated = 0, 0
        for nodeid in nodeids:
            module = nodeid.split("::")[0].replace("\\", "/").split("/")[-2] \
                if "::" in nodeid else ""
            name = nodeid.split("::")[-1]
            with self._conn() as conn:
                exists = conn.execute(
                    "SELECT id FROM cases WHERE nodeid=?", (nodeid,)
                ).fetchone()
            if exists:
                self.update_case(exists["id"], name=name, module=module)
                updated += 1
            else:
                self.upsert_case(nodeid, name=name, module=module)
                imported += 1
        return {"imported": imported, "updated": updated}

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

    # ---------- audit_log（审计日志） ----------
    def insert_audit(self, username: str, action: str, target: str = "",
                     detail: str = "", ip: str = "", ok: bool = True):
        """记录审计事件。写日志失败绝不阻断业务主流程。"""
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO audit_log (username, action, target, detail, ip, ok, created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (username or "anonymous", action, target or "", (detail or "")[:500],
                     ip or "", 1 if ok else 0,
                     datetime.now().isoformat(timespec="seconds")),
                )
        except Exception as exc:  # 审计失败不影响业务
            import warnings
            warnings.warn(f"审计日志写入失败：{exc}")

    def list_audit(self, limit: int = 200, action: str = "",
                   username: str = "") -> list[dict]:
        """查询审计日志（admin 页面用，可按动作/用户过滤）。"""
        sql = "SELECT * FROM audit_log WHERE 1=1"
        args: list = []
        if action:
            sql += " AND action=?"
            args.append(action)
        if username:
            sql += " AND username=?"
            args.append(username)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, args).fetchall()
            return [dict(r) for r in rows]

    # ---------- ai_settings（AI 配置，管理员维护） ----------
    def get_ai_settings(self) -> dict | None:
        """读取 AI 配置（单行表，取最新一条）。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ai_settings ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def save_ai_settings(self, provider: str, base_url: str, api_key_enc: str,
                         model: str, enabled: bool) -> int:
        """保存 AI 配置（存在则更新最新一条，否则插入）。返回配置 id。"""
        now = datetime.now().isoformat(timespec="seconds")
        existing = self.get_ai_settings()
        with self._conn() as conn:
            if existing:
                conn.execute(
                    "UPDATE ai_settings SET provider=?, base_url=?, api_key_enc=?, "
                    "model=?, enabled=?, updated_at=? WHERE id=?",
                    (provider, base_url, api_key_enc, model, 1 if enabled else 0,
                     now, existing["id"]),
                )
                return existing["id"]
            cur = conn.execute(
                "INSERT INTO ai_settings (provider, base_url, api_key_enc, model, "
                "enabled, updated_at) VALUES (?,?,?,?,?,?)",
                (provider, base_url, api_key_enc, model, 1 if enabled else 0, now),
            )
            return cur.lastrowid


db = _Database()
db.init_db()  # 模块加载即建表（幂等），平台/脚本无需手动初始化

# ---------- 预置管理员账号（首次启动自动创建）----------
import bcrypt as _bcrypt


def ensure_admin():
    with db._conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if row:
            return
        pwd_hash = _bcrypt.hashpw(b"admin123", _bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
            ("admin", pwd_hash, "admin", datetime.now().isoformat(timespec="seconds")),
        )
        print("已创建默认管理员账号：admin / admin123（请尽快修改密码）")


def verify_user(username: str, password: str) -> dict | None:
    """校验用户名密码，成功返回用户 dict。"""
    with db._conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return None
        user = dict(row)
        if _bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return user
        return None


def get_user_by_username(username: str) -> dict | None:
    """按用户名查用户（SSO 免密登录用，不校验密码）。"""
    with db._conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def create_sso_user(username: str, role: str = "user") -> dict:
    """创建 SSO 免密用户（首次单点登录自动开户，幂等）。"""
    with db._conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role, created_at) "
            "VALUES (?,?,?,?)",
            (username, "", role, datetime.now().isoformat(timespec="seconds")),
        )
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row)
