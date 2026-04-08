"""Linux 服务状态检查（服务对象 SO）"""
from service_objects.linux_service import LinuxService

def test_linux_services():
    service = LinuxService()

    # 执行检查
    assert service.check_java(), "Java 未安装"
    assert service.check_docker(), "Docker 未运行"
    assert service.check_nginx(), "Nginx 未启动"