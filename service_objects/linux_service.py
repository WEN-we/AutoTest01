from service_objects.base_service import BaseService
from utils.tools.linux_client import LinuxClient
from utils.tools.config_reader import ConfigReader

class LinuxService(BaseService):
    """Linux SSH 服务对象（SO）"""

    def __init__(self):
        super().__init__()
        # 配置从 YAML 读取 → 完全分离
        cfg = ConfigReader().read_yaml("config/linux_config.yaml")
        self.commands = cfg["linux_service_check"]["check_commands"]

        self.ssh = LinuxClient()
        self.ssh.connect()

    def check_java(self):
        out, _ = self.ssh.exec_command(self.commands["java"])
        return "version" in out

    def check_docker(self):
        out, _ = self.ssh.exec_command(self.commands["docker"])
        return "Docker" in out

    def check_nginx(self):
        out, _ = self.ssh.exec_command(self.commands["nginx"])
        return "active" in out

    def __del__(self):
        self.ssh.close()