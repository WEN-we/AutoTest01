"""
测试报告API接口
"""
import logging
import json
from flask import Blueprint, request, jsonify
from backend.models.report import Report
from backend.utils.decorators import login_required
from backend.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('', methods=['GET'])
@login_required
def get_reports():
    """获取测试报告列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        result = Report.find_all(page, page_size)
        return success_response(result)
    except Exception as e:
        import traceback
        logger.error(f"获取测试报告列表失败: {e}")
        logger.error(traceback.format_exc())
        return error_response(f"获取测试报告列表失败: {str(e)}", 500)


@reports_bp.route('/dashboard-summary', methods=['GET'])
@login_required
def dashboard_report_summary():
    """仪表盘报告汇总 - 返回最近10条报告数据和整体统计"""
    try:
        # 复用 Report.find_all() 的合并逻辑，确保与测试报告页面数据源一致
        result = Report.find_all(page=1, page_size=10)
        reports = result.get('reports', [])

        # 整体统计 - 从 test_report 表聚合
        from backend.utils.database import Database
        stats = {
            'total_reports': 0, 'total_passed': 0, 'total_failed': 0,
            'total_cases': 0, 'avg_pass_rate': 0, 'total_duration': 0
        }

        try:
            sql_stats = """
                SELECT
                    COUNT(*) as total_reports,
                    COALESCE(SUM(passed), 0) as total_passed,
                    COALESCE(SUM(failed), 0) as total_failed,
                    COALESCE(SUM(total), 0) as total_cases,
                    COALESCE(AVG(pass_rate), 0) as avg_pass_rate,
                    COALESCE(SUM(duration), 0) as total_duration
                FROM test_report
            """
            stats = Database.execute_query(sql_stats, fetch_one=True) or stats
        except Exception as e:
            logger.warning(f"查询test_report统计失败: {e}")

        # 如果 test_report 为空，从 test_case_result 聚合统计
        if not stats or (stats.get('total_reports', 0) == 0):
            try:
                sql_stats2 = """
                    SELECT
                        COUNT(DISTINCT cr.execution_id) as total_reports,
                        COALESCE(SUM(CASE WHEN cr.status = 'passed' THEN 1 ELSE 0 END), 0) as total_passed,
                        COALESCE(SUM(CASE WHEN cr.status = 'failed' THEN 1 ELSE 0 END), 0) as total_failed,
                        COALESCE(COUNT(*), 0) as total_cases,
                        COALESCE(SUM(cr.duration), 0) as total_duration
                    FROM test_case_result cr
                """
                stats2 = Database.execute_query(sql_stats2, fetch_one=True)
                if stats2 and stats2.get('total_cases', 0) > 0:
                    stats2['avg_pass_rate'] = round(
                        (stats2['total_passed'] / stats2['total_cases']) * 100, 2
                    ) if stats2['total_cases'] > 0 else 0
                    stats = stats2
            except Exception as e:
                logger.warning(f"查询test_case_result统计失败: {e}")

        return success_response({
            'reports': reports,
            'stats': stats
        })

    except Exception as e:
        import traceback
        logger.error(f"获取仪表盘报告汇总失败: {e}")
        logger.error(traceback.format_exc())
        return error_response("获取报告汇总失败", 500)


@reports_bp.route('/<report_id>', methods=['GET'])
@login_required
def get_report_detail(report_id):
    """获取报告详情 - report_id 可能是整数ID或execution_id字符串"""
    try:
        # 尝试作为整数ID查询
        if report_id.isdigit():
            report = Report.find_by_id(int(report_id))
        else:
            # 作为execution_id查询
            report = Report.find_by_execution_id(report_id)

        if not report:
            return error_response("报告不存在", 404)

        return success_response(data=report)
    except Exception as e:
        logger.error(f"获取报告详情失败: {e}")
        return error_response("获取报告详情失败", 500)


@reports_bp.route('/by-execution/<execution_id>', methods=['GET'])
@login_required
def get_report_by_execution(execution_id):
    """根据执行ID获取报告"""
    try:
        report = Report.find_by_execution_id(execution_id)
        if not report:
            return error_response("报告不存在", 404)
        return success_response(data=report)
    except Exception as e:
        logger.error(f"获取报告失败: {e}")
        return error_response("获取报告失败", 500)


@reports_bp.route('/batch-delete', methods=['POST'])
@login_required
def batch_delete_reports():
    """批量删除报告"""
    try:
        from backend.utils.database import Database

        json_data = request.get_json(silent=True)
        if not json_data or 'report_ids' not in json_data:
            return error_response("缺少 report_ids 参数", 400)

        report_ids = json_data['report_ids']
        if not isinstance(report_ids, list) or len(report_ids) == 0:
            return error_response("report_ids 必须是非空数组", 400)

        deleted_count = 0
        for report_id in report_ids:
            try:
                # report_id 可能是 execution_id 字符串或整型ID
                rid = str(report_id)
                exec_id = None

                # 先尝试从 test_report 表查找（按 execution_id 查询，避免INT/VARCHAR类型转换问题）
                sql_check = "SELECT id, execution_id FROM test_report WHERE execution_id = %s"
                report_record = Database.execute_query(sql_check, (rid,), fetch_one=True)

                if report_record:
                    exec_id = report_record['execution_id']
                else:
                    # 尝试按 id 查询（如果是数字ID）
                    if rid.isdigit():
                        sql_check2 = "SELECT id, execution_id FROM test_report WHERE id = %s"
                        report_record2 = Database.execute_query(sql_check2, (int(rid),), fetch_one=True)
                        if report_record2:
                            exec_id = report_record2['execution_id']

                # 如果没有在 test_report 表找到，直接使用 rid 作为 execution_id
                if not exec_id:
                    exec_id = rid

                # 删除报告记录（test_report）
                try:
                    sql_delete_report = "DELETE FROM test_report WHERE execution_id = %s"
                    affected = Database.execute_update(sql_delete_report, (exec_id,))
                    logger.info(f"删除test_report: execution_id={exec_id}, affected={affected}")
                except Exception as e:
                    logger.warning(f"删除test_report记录失败（可能不存在）: {e}")

                # 删除关联的用例结果
                try:
                    sql_delete_cases = "DELETE FROM test_case_result WHERE execution_id = %s"
                    affected = Database.execute_update(sql_delete_cases, (exec_id,))
                    logger.info(f"删除test_case_result: execution_id={exec_id}, affected={affected}")
                except Exception as e:
                    logger.warning(f"删除test_case_result记录失败: {e}")

                # 删除执行日志
                try:
                    sql_delete_logs = "DELETE FROM execution_log WHERE execution_id = %s"
                    affected = Database.execute_update(sql_delete_logs, (exec_id,))
                    logger.info(f"删除execution_log: execution_id={exec_id}, affected={affected}")
                except Exception as e:
                    logger.warning(f"删除execution_log记录失败: {e}")

                # 删除执行记录
                try:
                    sql_delete_exec = "DELETE FROM test_execution WHERE execution_id = %s"
                    affected = Database.execute_update(sql_delete_exec, (exec_id,))
                    logger.info(f"删除test_execution: execution_id={exec_id}, affected={affected}")
                except Exception as e:
                    logger.warning(f"删除test_execution记录失败: {e}")

                deleted_count += 1
                logger.info(f"报告删除处理完成: report_id={report_id}, exec_id={exec_id}")
            except Exception as e:
                logger.error(f"删除报告失败: report_id={report_id}, error={e}")

        return success_response(data={'deleted_count': deleted_count}, message=f'成功删除 {deleted_count} 条报告记录')

    except Exception as e:
        logger.error(f"批量删除报告失败: {e}")
        return error_response("批量删除报告失败", 500)


@reports_bp.route('/<report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """删除单条报告 - report_id 可能是整数ID或execution_id字符串"""
    try:
        from backend.utils.database import Database

        rid = str(report_id)
        exec_id = None

        # 先尝试从 test_report 表查找（按 execution_id 查询，避免INT/VARCHAR类型转换问题）
        sql_check = "SELECT id, execution_id FROM test_report WHERE execution_id = %s"
        report_record = Database.execute_query(sql_check, (rid,), fetch_one=True)

        if report_record:
            exec_id = report_record['execution_id']
        else:
            # 尝试按 id 查询（如果是数字ID）
            if rid.isdigit():
                sql_check2 = "SELECT id, execution_id FROM test_report WHERE id = %s"
                report_record2 = Database.execute_query(sql_check2, (int(rid),), fetch_one=True)
                if report_record2:
                    exec_id = report_record2['execution_id']

        # 如果没有在 test_report 表找到，直接使用 rid 作为 execution_id
        if not exec_id:
            exec_id = rid

        # 删除报告记录（test_report）
        try:
            Database.execute_update("DELETE FROM test_report WHERE execution_id = %s", (exec_id,))
        except Exception as e:
            logger.warning(f"删除test_report记录失败（可能不存在）: {e}")

        # 删除关联的用例结果
        try:
            Database.execute_update("DELETE FROM test_case_result WHERE execution_id = %s", (exec_id,))
        except Exception as e:
            logger.warning(f"删除test_case_result记录失败: {e}")

        # 删除执行日志
        try:
            Database.execute_update("DELETE FROM execution_log WHERE execution_id = %s", (exec_id,))
        except Exception as e:
            logger.warning(f"删除execution_log记录失败: {e}")

        # 删除执行记录
        try:
            Database.execute_update("DELETE FROM test_execution WHERE execution_id = %s", (exec_id,))
        except Exception as e:
            logger.warning(f"删除test_execution记录失败: {e}")

        return success_response(message="报告已删除")

    except Exception as e:
        logger.error(f"删除报告失败: {e}")
        return error_response("删除报告失败", 500)
