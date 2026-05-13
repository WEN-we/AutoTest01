"""
测试报告API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.report import Report
from backend.utils.decorators import login_required

reports_bp = Blueprint('reports', __name__)


def success_response(data=None, message="操作成功"):
    response = {"code": 200, "message": message}
    if data:
        response["data"] = data
    return jsonify(response)


def error_response(message, code=400):
    return jsonify({"code": code, "message": message}), code


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
        print(f"获取测试报告列表失败: {e}")
        return error_response("获取测试报告列表失败", 500)


@reports_bp.route('/<int:report_id>', methods=['GET'])
@login_required
def get_report_detail(report_id):
    """获取报告详情"""
    try:
        report = Report.find_by_id(report_id)

        if not report:
            return error_response("报告不存在", 404)

        return success_response(data=report)
    except Exception as e:
        print(f"获取报告详情失败: {e}")
        return error_response("获取报告详情失败", 500)
