import paramiko
import os
from utils.logger import logger
from utils.config_reader import ConfigReader

# ========== 云端 CI 模式：自动识别 GitHub ==========
CI_MODE = os.environ.get("CI") == "true"

class LinuxClient:
    """Linux SSH 客户端（企业标准封装 + 云端CI兼容）"""

    def __init__(self):
        self.config = ConfigReader.read_yaml("config/linux_config.yaml")
        self.server_cfg = self.config["linux_server"]

        self.host = self.server_cfg["host"]
        self.port = self.server_cfg["port"]
        self.username = self.server_cfg["username"]
        self.password = self.server_cfg.get("password")
        self.pkey = self.server_cfg.get("private_key")

        self.ssh = None

    def connect(self):
        """
        关键优化：
        云端 CI 模式 → 不建立 SSH 连接，直接跳过
        本地模式 → 正常连接
        """
        if CI_MODE:
            logger.info("✅ 云端CI模式：直接本地执行，不连接SSH")
            return

        # 下面是你原来的代码，完全不动
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            key_filename=self.pkey,
            timeout=10
        )
        logger.info(f"✅ Linux 连接成功: {self.host}")

    def exec_command(self, command):
        """
        关键优化：
        云端 CI → 本地执行命令
        本地 → SSH 执行
        """
        if CI_MODE:
            # 云端直接跑
            logger.info(f"🐧 [CI模式] 执行命令: {command}")
            result = os.popen(command).read()
            return result, ""

        # 你原来的逻辑不变
        stdin, stdout, stderr = self.ssh.exec_command(command)
        output = stdout.read().decode("utf-8", errors="ignore")
        error = stderr.read().decode("utf-8", errors="ignore")
        logger.info(f"🐧 执行命令: {command}")
        return output, error

    def close(self):
        if CI_MODE:
            return
        if self.ssh:
            self.ssh.close()
            logger.info("🔌 Linux 连接已关闭")