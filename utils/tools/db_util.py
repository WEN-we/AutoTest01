"""
统一的数据库工具类
用于本地服务、性能测试和测试脚本
"""
import pymysql
from pymysql.cursors import DictCursor
from utils.tools.config_reader import ConfigReader
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Database:
    """
    数据库工具类：用于接口/UI测试后数据校验
    作用：查询、验证用户是否存在、数据是否正确
    """

    _pool = None

    @classmethod
    def get_connection(cls):
        """获取数据库连接"""
        # 自动读取当前环境的数据库配置
        db_config = ConfigReader().get_db_config()
        return pymysql.connect(
            host=db_config["host"],
            port=int(db_config["port"]),
            user=db_config["user"],
            password=db_config["pwd"],
            database=db_config["database"],
            charset="utf8mb4",
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

    # 兼容旧版本的接口
    @classmethod
    def query_one(cls, sql: str):
        """查询单条数据（兼容旧版本）"""
        return cls.execute_query(sql, fetch_one=True)

    @classmethod
    def execute(cls, sql: str):
        """执行增删改（兼容旧版本）"""
        return cls.execute_update(sql)
