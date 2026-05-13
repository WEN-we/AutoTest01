"""
测试报告服务
生成和管理测试报告
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.tools.path_manager import get_reports_path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportService:
    """测试报告服务"""

    REPORTS_DIR = get_reports_path()

    def __init__(self):
        os.makedirs(self.REPORTS_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.REPORTS_DIR, 'html'), exist_ok=True)
        os.makedirs(os.path.join(self.REPORTS_DIR, 'json'), exist_ok=True)

    def generate_report(self, execution_id: str, test_type: str, result_summary: Dict = None) -> Dict:
        """生成测试报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_id = f"{test_type}_{timestamp}_{execution_id[:8]}"

        report_info = {
            'report_id': report_id,
            'execution_id': execution_id,
            'test_type': test_type,
            'created_at': timestamp,
            'summary': result_summary or {},
            'status': 'generated'
        }

        report_file = os.path.join(self.REPORTS_DIR, 'json', f"{report_id}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_info, f, ensure_ascii=False, indent=2)

        logger.info(f"报告已生成: {report_file}")
        return report_info

    def get_report(self, report_id: str) -> Optional[Dict]:
        """获取报告信息"""
        report_file = os.path.join(self.REPORTS_DIR, 'json', f"{report_id}.json")
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_reports(self, test_type: str = None, limit: int = 50) -> List[Dict]:
        """列出报告"""
        reports = []
        json_dir = os.path.join(self.REPORTS_DIR, 'json')

        if os.path.exists(json_dir):
            files = sorted(os.listdir(json_dir), reverse=True)[:limit]

            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(json_dir, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        if test_type is None or report.get('test_type') == test_type:
                            reports.append(report)

        return reports

    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        report_file = os.path.join(self.REPORTS_DIR, 'json', f"{report_id}.json")
        if os.path.exists(report_file):
            os.remove(report_file)
            logger.info(f"报告已删除: {report_id}")
            return True
        return False

    def get_report_summary(self) -> Dict:
        """获取报告统计摘要"""
        reports = self.list_reports(limit=1000)

        summary = {
            'total': len(reports),
            'by_type': {},
            'recent': []
        }

        for report in reports:
            test_type = report.get('test_type', 'unknown')
            summary['by_type'][test_type] = summary['by_type'].get(test_type, 0) + 1

        summary['recent'] = reports[:10]

        return summary


report_service = ReportService()
