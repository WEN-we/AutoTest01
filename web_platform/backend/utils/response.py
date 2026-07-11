"""
统一API响应封装
提供标准化的成功和错误响应格式

响应格式与项目现有代码兼容：
- 成功：{"code": 200, "message": "...", "data": ...}
- 错误：{"code": 400/500, "message": "..."}
"""
from flask import jsonify


def success_response(data=None, message="操作成功", code=200):
    """成功响应

    Args:
        data: 响应数据
        message: 成功消息
        code: HTTP状态码

    Returns:
        flask.Response: JSON响应
    """
    response = {"code": code, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response)


def error_response(message="操作失败", code=400, details=None):
    """错误响应

    Args:
        message: 错误消息
        code: HTTP状态码
        details: 详细错误信息（可选）

    Returns:
        flask.Response: JSON响应
    """
    response = {"code": code, "message": message}
    if details is not None:
        response["details"] = details
    return jsonify(response), code


def paginated_response(data, total, page, page_size, message="查询成功"):
    """分页响应

    Args:
        data: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        message: 成功消息

    Returns:
        flask.Response: JSON响应
    """
    return jsonify({
        "code": 200,
        "message": message,
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
        }
    })
