"""一键编排启动全链路（集中化收口：MySQL -> 被测服务 -> 质量平台 -> 分布式 worker）。

替代"四个窗口手动起进程"，一条命令拉起整条链并做健康等待：

    python -m quality_platform.scripts.orchestrate              # MySQL检查 + SUT + 平台
    python -m quality_platform.scripts.orchestrate --workers    # 额外启动 9101/9102 两个执行节点
    python -m quality_platform.scripts.orchestrate --stop       # 停止本脚本拉起的全部进程
    python -m quality_platform.scripts.orchestrate --status     # 查看各组件健康状态

说明：
- 自动加载项目根 .env（LOCAL_DB_* 等凭据不入库，透传给被测服务）
- PID 记录在 quality_platform/data/orchestrate.pids（data/ 已 gitignore）
- 每个组件日志写入 logs/orchestrate_<name>.log
"""
import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PIDS_FILE = PROJECT_ROOT / "quality_platform" / "data" / "orchestrate.pids"
LOG_DIR = PROJECT_ROOT / "logs"

COMPONENTS = {
    "sut": {"cmd": [sys.executable, "local_web_login/backend_server.py"], "port": 8090},
    "platform": {"cmd": [sys.executable, "-m", "quality_platform.app"], "port": 8081},
    "worker-9101": {"cmd": [sys.executable, "-m", "quality_platform.remote.worker",
                            "--port", "9101"], "port": 9101},
    "worker-9102": {"cmd": [sys.executable, "-m", "quality_platform.remote.worker",
                            "--port", "9102"], "port": 9102},
}


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((host, port)) == 0


def _wait_port(port: int, name: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(port):
            print(f"  ✅ {name} 就绪（127.0.0.1:{port}）")
            return True
        time.sleep(1)
    print(f"  ❌ {name} 等待超时（{timeout}s，端口 {port} 未监听），看日志 logs/orchestrate_{name}.log")
    return False


def _load_env() -> None:
    """加载 .env（存在才加载），凭据只进本进程环境、不打印。"""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print("  已加载 .env 环境变量")
        except ImportError:
            print("  ⚠️ 未安装 python-dotenv，跳过 .env 加载（SUT 可能缺 LOCAL_DB_*）")


def _spawn(name: str) -> int | None:
    comp = COMPONENTS[name]
    LOG_DIR.mkdir(exist_ok=True)
    log_file = open(LOG_DIR / f"orchestrate_{name}.log", "ab")
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    proc = subprocess.Popen(comp["cmd"], cwd=str(PROJECT_ROOT), env=env,
                            stdout=log_file, stderr=subprocess.STDOUT)
    _save_pid(name, proc.pid)
    return proc.pid


def _save_pid(name: str, pid: int) -> None:
    PIDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = _read_pids()
    lines = [ln for ln in lines if not ln.startswith(name + "=")]
    lines.append(f"{name}={pid}")
    PIDS_FILE.write_text("\n".join(lines), encoding="utf-8")


def _read_pids() -> list[str]:
    if PIDS_FILE.exists():
        return [ln.strip() for ln in PIDS_FILE.read_text(encoding="utf-8").splitlines()
                if "=" in ln]
    return []


def cmd_start(start_workers: bool) -> int:
    print("=== 一键编排启动（集中化全链路）===")
    _load_env()

    print("\n[1/4] 检查 MySQL（3306）...")
    if _port_open(3306):
        print("  ✅ MySQL 已在运行")
    else:
        print("  ❌ MySQL 未运行：请先启动 MySQL 服务后重试（平台与 SUT 都依赖）")
        return 1

    order = ["sut", "platform"] + (["worker-9101", "worker-9102"] if start_workers else [])
    total = 2 + (2 if start_workers else 0)
    for i, name in enumerate(order, start=2):
        comp = COMPONENTS[name]
        print(f"\n[{i}/{total}] 启动 {name}（端口 {comp['port']}）...")
        if _port_open(comp["port"]):
            print(f"  ✅ {name} 端口已占用，视为已在运行，跳过启动")
            continue
        pid = _spawn(name)
        print(f"  已拉起（PID {pid}），等待就绪...")
        if not _wait_port(comp["port"], name):
            return 1

    print("\n=== 全链路就绪 ===")
    print("  质量平台：http://127.0.0.1:8081（admin / admin123）")
    print("  被测服务：http://127.0.0.1:8090")
    if start_workers:
        print("  执行节点：9101 / 9102（在 platform_config.yaml distributed.workers 登记后生效）")
    print("  停止全部：python -m quality_platform.scripts.orchestrate --stop")
    return 0


def cmd_stop() -> int:
    print("=== 停止编排进程 ===")
    pids = _read_pids()
    if not pids:
        print("  无本脚本拉起的进程记录")
        return 0
    for ln in pids:
        name, pid = ln.split("=", 1)
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", pid, "/F", "/T"],
                               capture_output=True, timeout=15)
            else:
                subprocess.run(["kill", "-9", pid], capture_output=True, timeout=15)
            print(f"  ✅ {name}（PID {pid}）已停止")
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠️ {name}（PID {pid}）停止失败：{exc}")
    PIDS_FILE.unlink(missing_ok=True)
    return 0


def cmd_status() -> int:
    print("=== 链路健康状态 ===")
    checks = [("MySQL", 3306)] + [(n, c["port"]) for n, c in COMPONENTS.items()]
    for name, port in checks:
        state = "✅ 在线" if _port_open(port) else "❌ 离线"
        print(f"  {name:14s} :{port}  {state}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="质量平台一键编排（MySQL/SUT/平台/worker）")
    ap.add_argument("--workers", action="store_true", help="同时启动 9101/9102 执行节点")
    ap.add_argument("--stop", action="store_true", help="停止本脚本拉起的全部进程")
    ap.add_argument("--status", action="store_true", help="查看各组件健康状态")
    args = ap.parse_args()
    if args.stop:
        return cmd_stop()
    if args.status:
        return cmd_status()
    return cmd_start(args.workers)


if __name__ == "__main__":
    sys.exit(main())
