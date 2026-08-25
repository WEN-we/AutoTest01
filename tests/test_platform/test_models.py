"""数据访问层单元测试：临时 SQLite / PostgreSQL 双后端全 CRUD 覆盖"""
import uuid

import bcrypt
import pytest

import quality_platform.models as models
from quality_platform.models import db as models_db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """把全局 db 指向隔离库（每次测试独立，双后端兼容）：
    - SQLite：monkeypatch db.path 指向临时文件
    - PostgreSQL：临时建一个独立数据库并切换 PG_CONFIG.dbname，测试结束删除
    """
    if models.DB_TYPE == "postgres":
        import psycopg2

        admin_cfg = dict(models.PG_CONFIG)
        admin_cfg["dbname"] = "postgres"
        conn = psycopg2.connect(**admin_cfg)
        conn.autocommit = True
        cur = conn.cursor()
        dbname = "qp_test_" + uuid.uuid4().hex[:8]
        cur.execute(f'CREATE DATABASE "{dbname}"')
        conn.close()

        new_cfg = dict(models.PG_CONFIG)
        new_cfg["dbname"] = dbname
        monkeypatch.setattr(models, "PG_CONFIG", new_cfg)
        models_db.init_db()
        yield models_db

        conn = psycopg2.connect(**admin_cfg)
        conn.autocommit = True
        conn.cursor().execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        conn.close()
    else:
        monkeypatch.setattr(models_db, "path", str(tmp_path / "test.db"))
        models_db.init_db()
        yield models_db


class TestExecutions:
    def test_insert_and_finish(self, tmp_db):
        exec_id = tmp_db.insert_execution("tests/test_api/")
        assert exec_id >= 1
        row = tmp_db.get_execution(exec_id)
        assert row["status"] == "running"
        assert row["test_path"] == "tests/test_api/"

        tmp_db.finish_execution(exec_id, 10, 8, 2, 0, 12.5)
        row = tmp_db.get_execution(exec_id)
        assert row["status"] == "finished"
        assert (row["total"], row["passed"], row["failed"]) == (10, 8, 2)
        assert row["duration"] == 12.5
        assert row["finished_at"]

    def test_get_execution_not_found(self, tmp_db):
        assert tmp_db.get_execution(99999) is None

    def test_list_executions_desc(self, tmp_db):
        id1 = tmp_db.insert_execution("a")
        id2 = tmp_db.insert_execution("b")
        rows = tmp_db.list_executions(limit=10)
        assert [r["id"] for r in rows] == [id2, id1]


class TestCaseResults:
    def test_insert_and_list(self, tmp_db):
        exec_id = tmp_db.insert_execution("tests/x/")
        tmp_db.insert_case_result(exec_id, "t::a", "passed", 1.0)
        tmp_db.insert_case_result(exec_id, "t::b", "failed", 2.0,
                                   error_type="AssertionError",
                                   error_message="assert 1 == 2")
        rows = tmp_db.list_case_results(exec_id)
        assert len(rows) == 2
        failed = next(r for r in rows if r["nodeid"] == "t::b")
        assert failed["error_type"] == "AssertionError"

    def test_recent_failures_only_failed_error(self, tmp_db):
        exec_id = tmp_db.insert_execution("tests/x/")
        tmp_db.insert_case_result(exec_id, "t::pass", "passed")
        tmp_db.insert_case_result(exec_id, "t::fail", "failed")
        tmp_db.insert_case_result(exec_id, "t::err", "error")
        tmp_db.insert_case_result(exec_id, "t::skip", "skipped")
        failures = tmp_db.recent_failures(limit=10)
        assert {f["nodeid"] for f in failures} == {"t::fail", "t::err"}
        # 联表字段：带执行信息
        assert all(f["exec_id"] == exec_id for f in failures)

    def test_get_case_result_by_pk(self, tmp_db):
        exec_id = tmp_db.insert_execution("tests/x/")
        tmp_db.insert_case_result(exec_id, "t::a", "passed")
        tmp_db.insert_case_result(exec_id, "t::b", "failed",
                                   error_type="TimeoutError")
        rows = tmp_db.list_case_results(exec_id)
        target = next(r for r in rows if r["nodeid"] == "t::b")
        got = tmp_db.get_case_result(target["id"])
        assert got is not None
        assert got["nodeid"] == "t::b"
        assert got["exec_id"] == exec_id
        assert got["exec_time"]

    def test_get_case_result_not_found(self, tmp_db):
        assert tmp_db.get_case_result(424242) is None

    def test_recent_records_excludes_skipped(self, tmp_db):
        exec_id = tmp_db.insert_execution("tests/x/")
        tmp_db.insert_case_result(exec_id, "t::a", "passed")
        tmp_db.insert_case_result(exec_id, "t::b", "skipped")
        records = tmp_db.recent_records(limit=10)
        assert {r["nodeid"] for r in records} == {"t::a"}


class TestCasesLibrary:
    def test_upsert_insert_then_update(self, tmp_db):
        cid1 = tmp_db.upsert_case("tests/a.py::t1", name="t1", module="a",
                                  tags="smoke", owner="qa")
        cid2 = tmp_db.upsert_case("tests/a.py::t1", name="t1改", module="a",
                                  tags="smoke,api", owner="qa2")
        assert cid1 == cid2  # 同 nodeid 更新而非新增
        rows = tmp_db.list_cases()
        assert len(rows) == 1
        assert rows[0]["owner"] == "qa2"

    def test_list_cases_filter(self, tmp_db):
        tmp_db.upsert_case("tests/api/x.py::t", module="api", tags="smoke")
        tmp_db.upsert_case("tests/ui/y.py::t", module="ui", tags="login")
        assert len(tmp_db.list_cases(module="api")) == 1
        assert len(tmp_db.list_cases(keyword="login")) == 1
        assert len(tmp_db.list_cases()) == 2

    def test_update_case_allowed_fields_only(self, tmp_db):
        cid = tmp_db.upsert_case("tests/a.py::t", name="old")
        # 合法字段更新成功
        assert tmp_db.update_case(cid, name="new", owner="qa") is True
        row = next(c for c in tmp_db.list_cases() if c["id"] == cid)
        assert row["name"] == "new"
        # 非法字段被忽略（nodeid 不在白名单，防字段注入）
        assert tmp_db.update_case(cid, nodeid="hacked") is False

    def test_delete_case(self, tmp_db):
        cid = tmp_db.upsert_case("tests/a.py::t")
        assert tmp_db.delete_case(cid) is True
        assert tmp_db.delete_case(cid) is False  # 已删

    def test_import_cases(self, tmp_db):
        result = tmp_db.import_cases([
            "tests/test_api/test_user.py::TestUser::test_login",
            "tests/test_api/test_user.py::TestUser::test_logout",
        ])
        assert result["imported"] == 2
        # 再导入：全部走更新
        result2 = tmp_db.import_cases([
            "tests/test_api/test_user.py::TestUser::test_login",
        ])
        assert result2 == {"imported": 0, "updated": 1}
        # module 取自路径倒数第二段
        rows = tmp_db.list_cases(keyword="test_login")
        assert rows[0]["module"] == "test_api"


class TestAIAnalysis:
    def test_upsert_overwrites(self, tmp_db):
        tmp_db.upsert_analysis(1, {"category": "环境波动", "confidence": 0.5,
                                   "suggestion": "重跑", "key_evidence": "e",
                                   "source": "rule"})
        tmp_db.upsert_analysis(1, {"category": "产品缺陷", "confidence": 0.9,
                                   "suggestion": "提单", "key_evidence": "e2",
                                   "source": "llm"})
        got = tmp_db.get_analysis(1)
        assert got["category"] == "产品缺陷"
        assert got["source"] == "llm"

    def test_get_analysis_missing(self, tmp_db):
        assert tmp_db.get_analysis(999) is None

    def test_failures_join_analysis(self, tmp_db):
        """recent_failures 联表返回归因字段（ana_*），无归因为 None"""
        exec_id = tmp_db.insert_execution("tests/x/")
        tmp_db.insert_case_result(exec_id, "t::analyzed", "failed",
                                   error_type="TimeoutError")
        tmp_db.insert_case_result(exec_id, "t::raw", "failed",
                                   error_type="AssertionError")
        rows = {r["nodeid"]: r for r in tmp_db.recent_failures(limit=10)}
        analyzed_id = rows["t::analyzed"]["id"]
        tmp_db.upsert_analysis(analyzed_id, {"category": "环境波动/页面加载慢",
                                             "confidence": 0.5, "suggestion": "重跑",
                                             "key_evidence": "e", "source": "rule"})
        rows = {r["nodeid"]: r for r in tmp_db.recent_failures(limit=10)}
        assert rows["t::analyzed"]["ana_category"] == "环境波动/页面加载慢"
        assert rows["t::analyzed"]["ana_source"] == "rule"
        assert rows["t::raw"]["ana_category"] is None

    def test_list_case_results_join_analysis(self, tmp_db):
        """list_case_results 联表返回归因字段（执行详情页/自动归因共用）"""
        exec_id = tmp_db.insert_execution("tests/x/")
        tmp_db.insert_case_result(exec_id, "t::a", "failed")
        row = tmp_db.list_case_results(exec_id)[0]
        assert row["ana_category"] is None
        tmp_db.upsert_analysis(row["id"], {"category": "产品缺陷",
                                           "confidence": 0.9, "suggestion": "提单",
                                           "key_evidence": "e", "source": "llm"})
        row = tmp_db.list_case_results(exec_id)[0]
        assert row["ana_category"] == "产品缺陷"
        assert row["ana_source"] == "llm"


class TestUsers:
    def _create_user(self, tmp_db, username="alice", password="pw123456", role="user"):
        pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with tmp_db._conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) "
                "VALUES (?,?,?,datetime('now'))",
                (username, pwd_hash, role),
            )

    def test_verify_user_success(self, tmp_db):
        self._create_user(tmp_db)
        user = models.verify_user("alice", "pw123456")
        assert user is not None
        assert user["role"] == "user"

    def test_verify_user_wrong_password(self, tmp_db):
        self._create_user(tmp_db)
        assert models.verify_user("alice", "wrong") is None

    def test_verify_user_not_found(self, tmp_db):
        assert models.verify_user("ghost", "x") is None

    def test_ensure_admin_idempotent(self, tmp_db):
        models.ensure_admin()
        models.ensure_admin()  # 第二次不重复创建
        with tmp_db._conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE username='admin'").fetchone()["c"]
        assert count == 1
        assert models.verify_user("admin", "admin123") is not None


# ==============================
# PostgreSQL 方言适配层（纯逻辑测试，无需 PG 服务器）
# ==============================
class TestPgDialect:
    """models._PGConn._adapt_sql 的 SQLite→PG 方言转换 + PG 版 DDL 干净性。"""

    def _pg(self):
        return models._PGConn.__new__(models._PGConn)

    def test_placeholder_conversion(self):
        out = self._pg()._adapt_sql("SELECT * FROM users WHERE username=?")
        assert out == "SELECT * FROM users WHERE username=%s"

    def test_insert_auto_returning_id(self):
        sql = "INSERT INTO executions (test_path, status, started_at) VALUES (?, 'running', ?)"
        out = self._pg()._adapt_sql(sql)
        assert out.endswith(" RETURNING id")
        assert "?" not in out
        assert "VALUES (%s, 'running', %s)" in out

    def test_insert_or_ignore_to_on_conflict(self):
        sql = "INSERT OR IGNORE INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)"
        out = self._pg()._adapt_sql(sql)
        assert out.startswith("INSERT INTO users")
        assert "OR IGNORE" not in out
        assert out.endswith(" ON CONFLICT DO NOTHING")

    def test_update_and_limit_params(self):
        out = self._pg()._adapt_sql(
            "UPDATE cases SET name=?, updated_at=? WHERE id=?")
        assert out == "UPDATE cases SET name=%s, updated_at=%s WHERE id=%s"
        out2 = self._pg()._adapt_sql("SELECT * FROM cases WHERE module=? ORDER BY id DESC LIMIT ?")
        assert out2 == "SELECT * FROM cases WHERE module=%s ORDER BY id DESC LIMIT %s"

    def test_pg_schema_no_sqlite_dialect(self):
        s = models._SCHEMA_PG
        assert "AUTOINCREMENT" not in s
        assert "INSERT OR IGNORE" not in s.upper()
        assert "?" not in s
        assert "PRAGMA" not in s.upper()
        assert "SERIAL" in s and "SERIAL PRIMARY KEY" in s

    def test_sqlite_schema_kept(self):
        """SQLite 版 DDL 保持原样（默认后端不受影响）。"""
        assert "AUTOINCREMENT" in models._SCHEMA
