"""
数据库工具模块
"""
import pymysql
from pymysql.cursors import DictCursor
from backend.config.settings import config
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Database:
    """数据库工具类"""

    _pool = None

    @classmethod
    def get_connection(cls):
        """获取数据库连接"""
        db_config = config.get_database_config()
        return pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            database=db_config['database'],
            charset=db_config['charset'],
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
