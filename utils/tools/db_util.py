import pymysql
from utils.tools.config_reader import ConfigReader

class DBUtil:
    """
    数据库工具类：用于接口/UI测试后数据校验
    作用：查询、验证用户是否存在、数据是否正确
    """
    def __init__(self):
        # 自动读取当前环境的数据库配置
        self.db_config = ConfigReader().get_db_config()

    def __get_connection(self):
        # 创建数据库连接
        return pymysql.connect(
            host=self.db_config["host"],
            port=int(self.db_config["port"]),
            user=self.db_config["user"],
            password=self.db_config["pwd"],
            database=self.db_config["database"],
            charset="utf8mb4"
        )

    # 查询单条数据（常用：判断用户是否存在）
    def query_one(self, sql):
        conn = self.__get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result

    # 执行增删改（如重置数据）
    def execute(self, sql):
        conn = self.__get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()