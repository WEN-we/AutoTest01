"""
禅道集成接口 - 通过MySQL数据库直连获取数据
支持禅道22.0开源版
"""
import json
import os
import re
from flask import Blueprint, request, jsonify
from backend.models.integration import Integration
from backend.utils.decorators import login_required
from backend.utils.response import success_response, error_response

try:
    import pymysql
except ImportError:
    pymysql = None

zentao_bp = Blueprint('zentao', __name__)


def get_zentao_config():
    """获取禅道配置（优先返回默认配置）"""
    # 先查找默认配置
    config = Integration.find_default_by_type('zentao')
    if config:
        return config
    # 没有默认配置，则返回第一条可用配置
    return Integration.find_by_type('zentao')


def get_db_connection_for_config(config):
    """获取禅道MySQL数据库连接 - 使用指定配置"""
    if pymysql is None:
        return None, "PyMySQL未安装"

    if not config:
        return None, "禅道未配置"

    base_url = config.get('base_url', '').strip().rstrip('/')

    host = 'localhost'
    match = re.search(r'https?://([^/:]+)', base_url)
    if match:
        host = match.group(1)

    db_config = {
        'host': host,
        'port': int(config.get('db_port', 3307)),
        'user': config.get('db_user', 'root'),
        'password': config.get('db_password', '123456'),
        'database': config.get('db_name', 'zentao'),
        'connect_timeout': 5,
        'charset': 'utf8mb4',
    }

    try:
        conn = pymysql.connect(**db_config)
        return conn, None
    except pymysql.Error as e:
        return None, f"数据库连接失败: {str(e)}"


def _is_zentao_response(resp):
    """检查HTTP响应是否来自禅道系统"""
    try:
        content = resp.text.lower()
        # 禅道系统的特征标识
        zentao_markers = [
            'zentao', '禅道', 'zentaopms', 'zt-product', 'zt-bug',
            'zentaoclient', 'pms.zentao', 'zbox', 'ranzhi'
        ]
        return any(marker in content for marker in zentao_markers)
    except Exception:
        return False


def check_status_for_config(config):
    """检查指定禅道配置的连接状态"""
    import requests as req_lib
    try:
        if not config:
            return success_response(data={"connected": False, "message": "禅道未配置"})

        base_url = config.get('base_url', '').strip().rstrip('/')
        if not base_url:
            return success_response(data={"connected": False, "message": "服务地址未配置"})

        # 严格的URL格式验证
        if '://' not in base_url:
            return success_response(data={"connected": False, "message": "服务地址格式不正确，需要包含协议（如 http://）"})

        # 解析URL，检查host和port是否有效
        import urllib.parse
        parsed = urllib.parse.urlparse(base_url)
        if not parsed.scheme or not parsed.hostname:
            return success_response(data={"connected": False, "message": "服务地址格式不正确，无法解析主机名"})

        # 检查端口号是否有效（如果显式指定了端口）
        # 例如 http://localhost: 这种URL，urlparse会解析出空端口
        netloc = parsed.netloc
        if ':' in netloc:
            port_part = netloc.split(':')[-1]
            if not port_part or not port_part.isdigit():
                return success_response(data={"connected": False, "message": "服务地址中的端口号格式不正确"})

        # 第一步：检查禅道HTTP服务是否可达
        try:
            resp = req_lib.get(base_url, timeout=5, allow_redirects=True)
            if resp.status_code not in (200, 301, 302):
                return success_response(data={"connected": False, "message": f"服务地址不可达: HTTP {resp.status_code}"})
            # 验证响应内容是否来自禅道
            if not _is_zentao_response(resp):
                return success_response(data={"connected": False, "message": f"该地址未运行禅道服务，请确认地址正确且禅道已启动"})
        except req_lib.exceptions.ConnectionError:
            return success_response(data={"connected": False, "message": f"无法连接到禅道服务: {base_url}，请确认服务已启动"})
        except req_lib.exceptions.Timeout:
            return success_response(data={"connected": False, "message": f"连接禅道服务超时: {base_url}"})
        except req_lib.exceptions.RequestException as e:
            return success_response(data={"connected": False, "message": f"无法连接到禅道服务: {base_url} ({str(e)})"})

        # 第二步：检查数据库连接
        # 禅道配置的数据库参数：如果配置中有则使用，否则使用禅道默认参数
        # 禅道一键安装包默认：端口3307，用户root，密码123456，数据库zentao
        db_config_values = {
            'db_port': config.get('db_port', '3307'),
            'db_user': config.get('db_user', 'root'),
            'db_password': config.get('db_password', '123456'),
            'db_name': config.get('db_name', 'zentao'),
        }

        # 将数据库配置合并到config中供get_db_connection_for_config使用
        test_config = dict(config)
        test_config.update(db_config_values)

        conn, error = get_db_connection_for_config(test_config)
        if error:
            return success_response(data={"connected": False, "message": error})

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM zt_product WHERE deleted = '0'")
            product_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM zt_bug WHERE deleted = '0'")
            bug_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM zt_case WHERE deleted = '0'")
            case_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            return success_response(data={
                "connected": True,
                "message": "连接成功",
                "zentao_url": config['base_url'],
                "stats": {
                    "products": product_count,
                    "bugs": bug_count,
                    "cases": case_count,
                }
            })
        except Exception as e:
            return success_response(data={"connected": False, "message": f"查询失败: {str(e)}"})
    except Exception as e:
        return error_response(f"检查禅道状态失败: {e}", 500)


def get_db_connection():
    """获取禅道MySQL数据库连接"""
    if pymysql is None:
        return None, "PyMySQL未安装"

    config = get_zentao_config()
    if not config:
        return None, "禅道未配置"

    base_url = config.get('base_url', '').strip().rstrip('/')

    # 从base_url解析host
    host = 'localhost'
    match = re.search(r'https?://([^/:]+)', base_url)
    if match:
        host = match.group(1)

    # MySQL连接参数
    db_config = {
        'host': host,
        'port': int(config.get('db_port', 3307)),
        'user': config.get('db_user', 'root'),
        'password': config.get('db_password', '123456'),
        'database': config.get('db_name', 'zentao'),
        'connect_timeout': 5,
        'charset': 'utf8mb4',
    }

    try:
        conn = pymysql.connect(**db_config)
        return conn, None
    except pymysql.Error as e:
        return None, f"数据库连接失败: {str(e)}"


@zentao_bp.route('/status', methods=['GET'])
@login_required
def check_status():
    """检查禅道连接状态 - 使用统一的check_status_for_config逻辑"""
    try:
        config = get_zentao_config()
        if not config:
            return success_response(data={"connected": False, "message": "禅道未配置"})

        # 复用 check_status_for_config 的完整验证逻辑
        return check_status_for_config(config)
    except Exception as e:
        return error_response(f"检查禅道状态失败: {e}", 500)


@zentao_bp.route('/products', methods=['GET'])
@login_required
def get_products():
    try:
        conn, error = get_db_connection()
        if error:
            return error_response(error, 400)

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT id, name, code, `status`, `desc`, PO, QD, RD "
            "FROM zt_product WHERE deleted = '0' ORDER BY id"
        )
        rows = cursor.fetchall()

        products = []
        for row in rows:
            products.append({
                "id": row['id'],
                "name": row.get('name', ''),
                "code": row.get('code', ''),
                "status": row.get('status', ''),
                "description": row.get('desc', ''),
                "PO": row.get('PO', ''),
                "QD": row.get('QD', ''),
                "RD": row.get('RD', ''),
            })

        cursor.close()
        conn.close()
        return success_response(data={"products": products, "total": len(products)})
    except Exception as e:
        return error_response(f"获取产品列表失败: {e}", 500)


@zentao_bp.route('/bugs', methods=['GET'])
@login_required
def get_bugs():
    try:
        product_id = request.args.get('product_id', type=int)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)

        conn, error = get_db_connection()
        if error:
            return error_response(error, 400)

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where = "WHERE deleted = '0'"
        params = []
        if product_id:
            where += " AND product = %s"
            params.append(product_id)

        sql = (
            f"SELECT id, title, `status`, severity, pri, product, openedDate, "
            f"assignedTo, confirmed, activatedCount, resolvedBy, resolution, "
            f"openedBuild, type "
            f"FROM zt_bug {where} ORDER BY id DESC LIMIT %s OFFSET %s"
        )
        params.extend([limit, (page - 1) * limit])
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        bugs = []
        for row in rows:
            bugs.append({
                "id": row['id'],
                "title": row.get('title', ''),
                "status": row.get('status', ''),
                "severity": row.get('severity', 0),
                "priority": row.get('pri', 0),
                "product_id": row.get('product', 0),
                "openedDate": str(row.get('openedDate', '')) if row.get('openedDate') else '',
                "assignedTo": row.get('assignedTo', ''),
                "confirmed": row.get('confirmed', ''),
                "type": row.get('type', ''),
            })

        cursor.close()
        conn.close()
        return success_response(data={"bugs": bugs, "total": len(bugs), "page": page})
    except Exception as e:
        return error_response(f"获取Bug列表失败: {e}", 500)


@zentao_bp.route('/cases', methods=['GET'])
@login_required
def get_cases():
    try:
        product_id = request.args.get('product_id', type=int)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)

        conn, error = get_db_connection()
        if error:
            return error_response(error, 400)

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where = "WHERE deleted = '0'"
        params = []
        if product_id:
            where += " AND product = %s"
            params.append(product_id)

        sql = (
            f"SELECT id, title, `type`, `status`, pri, product, openedDate, "
            f"lastRunner, lastRunDate, lastRunResult, `stage`, precondition, keywords "
            f"FROM zt_case {where} ORDER BY id DESC LIMIT %s OFFSET %s"
        )
        params.extend([limit, (page - 1) * limit])
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cases = []
        for row in rows:
            cases.append({
                "id": row['id'],
                "title": row.get('title', ''),
                "type": row.get('type', ''),
                "status": row.get('status', ''),
                "priority": row.get('pri', 0),
                "product_id": row.get('product', 0),
                "openedDate": str(row.get('openedDate', '')) if row.get('openedDate') else '',
                "lastRunner": row.get('lastRunner', ''),
                "lastRunDate": str(row.get('lastRunDate', '')) if row.get('lastRunDate') else '',
                "lastRunResult": row.get('lastRunResult', ''),
                "stage": row.get('stage', ''),
                "precondition": row.get('precondition', ''),
                "keywords": row.get('keywords', ''),
            })

        cursor.close()
        conn.close()
        return success_response(data={"cases": cases, "total": len(cases), "page": page})
    except Exception as e:
        return error_response(f"获取测试用例列表失败: {e}", 500)


@zentao_bp.route('/sync/cases', methods=['POST'])
@login_required
def sync_cases():
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')

        conn, error = get_db_connection()
        if error:
            return error_response(error, 400)

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where = "WHERE deleted = '0'"
        params = []
        if product_id:
            where += " AND product = %s"
            params.append(product_id)

        cursor.execute(
            f"SELECT id, title, `type`, `status`, pri, product, openedDate, "
            f"lastRunner, lastRunDate, lastRunResult, `stage` "
            f"FROM zt_case {where} ORDER BY id",
            params
        )
        rows = cursor.fetchall()

        cases = []
        for row in rows:
            cases.append({
                "id": row['id'],
                "title": row.get('title', ''),
                "type": row.get('type', ''),
                "status": row.get('status', ''),
                "priority": row.get('pri', 0),
                "product_id": row.get('product', 0),
                "openedDate": str(row.get('openedDate', '')) if row.get('openedDate') else '',
                "lastRunner": row.get('lastRunner', ''),
                "lastRunDate": str(row.get('lastRunDate', '')) if row.get('lastRunDate') else '',
                "lastRunResult": row.get('lastRunResult', ''),
                "stage": row.get('stage', ''),
            })

        cursor.close()
        conn.close()
        return success_response(
            data={"synced_count": len(cases), "cases": cases},
            message=f"成功同步 {len(cases)} 个测试用例"
        )
    except Exception as e:
        return error_response(f"同步测试用例失败: {e}", 500)