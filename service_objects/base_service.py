"""
服务层（Service Object）基类

大厂三层架构规范：
- PO 层（page_objects）      ：页面元素 + 操作，不写断言
- SO 层（service_objects）   ：组合 PO，实现业务流程（登录/下单/支付），记录执行步骤
- 用例层（tests）            ：调用 SO，写断言，管理测试数据

SO 层的价值：
- 跨页面业务流（如"登录→搜索→加购→结算"）只写一次，用例层按数据驱动复用；
- 业务规则变化只改 SO；页面元素变化只改 PO；互不影响，维护成本降到最低。

升级记录（2026-08-22）：由 4 行空壳升级为完整服务层基类（步骤日志 + 摘要返回）。
"""
from datetime import datetime

from utils.tools.logger import log


class BaseService:
    """服务层基类（所有 SO 继承）"""

    def __init__(self, logger=None):
        self.logger = logger or log
        self._steps: list[str] = []

    def log_step(self, message: str):
        """记录业务步骤（大厂标准：用例执行轨迹可回溯，失败可快速定位到第几步）"""
        step = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self._steps.append(step)
        self.logger.info(f"步骤：{message}")

    @property
    def steps(self) -> list[str]:
        """已执行的业务步骤（按时间顺序）"""
        return list(self._steps)

    def summary(self) -> dict:
        """服务执行摘要（供用例层/报告使用）"""
        return {"steps": self._steps, "step_count": len(self._steps)}

    def clear_steps(self):
        """清空步骤记录（复用同一服务实例执行多条业务流时调用）"""
        self._steps.clear()
