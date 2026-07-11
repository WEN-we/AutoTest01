"""
local_web_login 专用数据库连接类
独立于 web_platform 的 Database 类，直接连接 local_web_login 数据库
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
import os

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("LOCAL_DB_HOST", "localhost"),
    "port": int(os.getenv("LOCAL_DB_PORT", 3306)),
    "user": os.getenv("LOCAL_DB_USER", "root"),
    "password": os.getenv("LOCAL_DB_PASSWORD", ""),
    "database": os.getenv("LOCAL_DB_NAME", "local_web_login"),
    "charset": "utf8mb4",
}


class LocalDatabase:
    """
    local_web_login 专用数据库工具类
    直接连接 local_web_login 数据库，不依赖 ConfigReader 或 web_platform 配置
    """

    @classmethod
    def get_connection(cls):
        """获取数据库连接"""
        return pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            charset=DB_CONFIG["charset"],
            cursorclass=DictCursor
        )

    @classmethod
    @contextmanager
    def get_cursor(cls):
        """上下文管理器，自动管理连接"""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def execute_query(cls, sql: str, params: tuple = (), fetch_one: bool = False):
        """执行查询"""
        with cls.get_cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone() if fetch_one else cursor.fetchall()
            return result

    @classmethod
    def execute_update(cls, sql: str, params: tuple = ()) -> int:
        """执行更新（INSERT/UPDATE/DELETE）"""
        with cls.get_cursor() as cursor:
            affected = cursor.execute(sql, params)
            return affected

    @classmethod
    def execute_insert(cls, sql: str, params: tuple = ()) -> int:
        """执行插入并返回ID"""
        with cls.get_cursor() as cursor:
            cursor.execute(sql, params)
            cursor.execute("SELECT LAST_INSERT_ID() as id")
            result = cursor.fetchone()
            return result['id']

    @classmethod
    def query_one(cls, sql: str):
        """查询单条数据（兼容旧版本）"""
        return cls.execute_query(sql, fetch_one=True)

    @classmethod
    def execute(cls, sql: str):
        """执行增删改（兼容旧版本）"""
        return cls.execute_update(sql)
