"""
禅道集成API
"""
from flask import Blueprint, request, jsonify
from local_web_login.backend_server import (
    login_required, success_response, error_response,
    Database
)
import requests
from utils.tools.logger import log as logger

zentao_bp = Blueprint('zentao', __name__, url_prefix='/api/integrations/zentao')


def get_zentao_config():
    """获取禅道配置"""
    sql = """
        SELECT * FROM integration_config
        WHERE integration_type = 'zentao' AND is_active = TRUE
        LIMIT 1
    """
    return Database.execute_query(sql, fetch_one=True)


def zentao_api_request(method, api_path, data=None):
    """禅道API请求"""
    config = get_zentao_config()

    if not config:
        return None, "禅道未配置"

    credentials = config.get('credentials', '{}')
    if isinstance(credentials, str):
        import json
        credentials = json.loads(credentials)

    account = credentials.get('account', '')
    password = credentials.get('password', '')

    if not account or not password:
        return None, "禅道凭证未配置"

    base_url = config['base_url'].rstrip('/')
    session_key = credentials.get('session_key', 'zentaosid')

    url = f"{base_url}/{api_path}"

    cookies = {session_key: credentials.get('session_value', '')}

    headers = {
        "Content-Type": "application/json"
    }

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, cookies=cookies, timeout=30)
        else:
            return None, f"不支持的请求方法: {method}"

        return response, None
    except requests.exceptions.Timeout:
        return None, "禅道请求超时"
    except requests.exceptions.RequestException as e:
        return None, f"禅道请求失败: {str(e)}"


def zentao_get_session():
    """获取禅道Session"""
    config = get_zentao_config()

    if not config:
        return None, "禅道未配置"

    credentials = config.get('credentials', '{}')
    if isinstance(credentials, str):
        import json
        credentials = json.loads(credentials)

    base_url = config['base_url'].rstrip('/')
    account = credentials.get('account', '')
    password = credentials.get('password', '')

    url = f"{base_url}/api.php/v1/tokens"

    try:
        response = requests.post(
            url,
            json={"account": account, "password": password},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get('token', '')
            return {
                "token": token,
                "token_type": data.get('tokenType', 'Bearer')
            }, None
        else:
            return None, f"获取Session失败: {response.status_code}"

    except Exception as e:
        return None, f"获取Session失败: {str(e)}"


def zentao_api_request_with_auth(method, api_path, data=None):
    """禅道API请求（带认证）"""
    token_info, error = zentao_get_session()

    if error:
        return None, error

    config = get_zentao_config()
    base_url = config['base_url'].rstrip('/')

    url = f"{base_url}/{api_path}"

    headers = {
        "Content-Type": "application/json",
        "Token": token_info['token']
    }

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return None, f"不支持的请求方法: {method}"

        return response, None
    except requests.exceptions.Timeout:
        return None, "禅道请求超时"
    except requests.exceptions.RequestException as e:
        return None, f"禅道请求失败: {str(e)}"


@zentao_bp.route('/status', methods=['GET'])
@login_required
def check_status():
    """检查禅道连接状态"""
    try:
        config = get_zentao_config()

        if not config:
            return jsonify(success_response(
                data={
                    "connected": False,
                    "message": "禅道未配置"
                }
            ))

        token_info, error = zentao_get_session()

        if error:
            return jsonify(success_response(
                data={
                    "connected": False,
                    "message": error
                }
            ))

        return jsonify(success_response(
            data={
                "connected": True,
                "message": "连接成功",
                "zentao_url": config['base_url']
            }
        ))

    except Exception as e:
        logger.error(f"检查禅道状态失败: {e}")
        return error_response("检查禅道状态失败", 500)


@zentao_bp.route('/products', methods=['GET'])
@login_required
def get_products():
    """获取产品列表"""
    try:
        response, error = zentao_api_request_with_auth('GET', 'api.php/v1/products')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        products = data.get('data', [])

        return jsonify(success_response(
            data={
                "products": products,
                "total": len(products)
            }
        ))

    except Exception as e:
        logger.error(f"获取产品列表失败: {e}")
        return error_response("获取产品列表失败", 500)


@zentao_bp.route('/products/<int:product_id>', methods=['GET'])
@login_required
def get_product_detail(product_id):
    """获取产品详情"""
    try:
        response, error = zentao_api_request_with_auth('GET', f'api.php/v1/products/{product_id}')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        return jsonify(success_response(data=data.get('data', {})))

    except Exception as e:
        logger.error(f"获取产品详情失败: {e}")
        return error_response("获取产品详情失败", 500)


@zentao_bp.route('/cases', methods=['GET'])
@login_required
def get_cases():
    """获取测试用例列表"""
    try:
        product_id = request.args.get('product_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        api_path = f'api.php/v1/testcases?page={page}&limit={page_size}'
        if product_id:
            api_path += f'&product_id={product_id}'

        response, error = zentao_api_request_with_auth('GET', api_path)

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        cases = data.get('data', [])
        total = data.get('total', len(cases))

        return jsonify(success_response(
            data={
                "cases": cases,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        ))

    except Exception as e:
        logger.error(f"获取测试用例列表失败: {e}")
        return error_response("获取测试用例列表失败", 500)


@zentao_bp.route('/cases/<int:case_id>', methods=['GET'])
@login_required
def get_case_detail(case_id):
    """获取用例详情"""
    try:
        response, error = zentao_api_request_with_auth('GET', f'api.php/v1/testcases/{case_id}')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        return jsonify(success_response(data=data.get('data', {})))

    except Exception as e:
        logger.error(f"获取用例详情失败: {e}")
        return error_response("获取用例详情失败", 500)


@zentao_bp.route('/cases/<int:case_id>/execute', methods=['POST'])
@login_required
def execute_case(case_id):
    """执行测试用例"""
    try:
        data = request.get_json()

        run_type = data.get('run_type', 'manual')
        version = data.get('version', 1)

        api_path = f'api.php/v1/testruns'
        request_data = {
            "product": data.get('product_id', 1),
            "execution": data.get('execution', 1),
            "cases": [str(case_id)],
            "version": version,
            "run_type": run_type
        }

        response, error = zentao_api_request_with_auth('POST', api_path, request_data)

        if error:
            return error_response(error, 400)

        if response.status_code not in [200, 201]:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        result = response.json()

        return jsonify(success_response(
            data=result.get('data', {}),
            message="测试用例已开始执行"
        ))

    except Exception as e:
        logger.error(f"执行测试用例失败: {e}")
        return error_response("执行测试用例失败", 500)


@zentao_bp.route('/bugs', methods=['GET'])
@login_required
def get_bugs():
    """获取Bug列表"""
    try:
        product_id = request.args.get('product_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        api_path = f'api.php/v1/bugs?page={page}&limit={page_size}'
        if product_id:
            api_path += f'&product_id={product_id}'

        response, error = zentao_api_request_with_auth('GET', api_path)

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        bugs = data.get('data', [])
        total = data.get('total', len(bugs))

        return jsonify(success_response(
            data={
                "bugs": bugs,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        ))

    except Exception as e:
        logger.error(f"获取Bug列表失败: {e}")
        return error_response("获取Bug列表失败", 500)


@zentao_bp.route('/bugs', methods=['POST'])
@login_required
def create_bug():
    """创建Bug"""
    try:
        data = request.get_json()

        title = data.get('title', '').strip()
        product_id = data.get('product_id', 1)
        severity = data.get('severity', 3)
        steps = data.get('steps', '')
        assigned_to = data.get('assigned_to', '')

        if not title:
            return error_response("Bug标题不能为空")

        api_path = 'api.php/v1/bugs'
        bug_data = {
            "product": product_id,
            "title": title,
            "severity": severity,
            "steps": steps,
            "type": "codeerror"
        }

        if assigned_to:
            bug_data["assignedTo"] = assigned_to

        response, error = zentao_api_request_with_auth('POST', api_path, bug_data)

        if error:
            return error_response(error, 400)

        if response.status_code not in [200, 201]:
            return error_response(f"创建Bug失败: {response.status_code}", 400)

        result = response.json()
        bug_id = result.get('data', {}).get('id', 0)

        Database.execute_update(
            """INSERT INTO test_execution (task_id, executor_id, status, logs)
               VALUES (0, %s, 'failed', %s)""",
            (request.current_user['id'], f"创建禅道Bug: {bug_id}")
        )

        return jsonify(success_response(
            data={
                "bug_id": bug_id,
                "url": result.get('data', {}).get('url', '')
            },
            message="Bug创建成功"
        ))

    except Exception as e:
        logger.error(f"创建Bug失败: {e}")
        return error_response("创建Bug失败", 500)


@zentao_bp.route('/executions', methods=['GET'])
@login_required
def get_executions():
    """获取测试执行列表"""
    try:
        product_id = request.args.get('product_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        api_path = f'api.php/v1/testtasks?page={page}&limit={page_size}'
        if product_id:
            api_path += f'&product_id={product_id}'

        response, error = zentao_api_request_with_auth('GET', api_path)

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        executions = data.get('data', [])
        total = data.get('total', len(executions))

        return jsonify(success_response(
            data={
                "executions": executions,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        ))

    except Exception as e:
        logger.error(f"获取测试执行列表失败: {e}")
        return error_response("获取测试执行列表失败", 500)


@zentao_bp.route('/executions/<int:execution_id>', methods=['GET'])
@login_required
def get_execution_detail(execution_id):
    """获取执行详情"""
    try:
        response, error = zentao_api_request_with_auth('GET', f'api.php/v1/testtasks/{execution_id}')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()

        return jsonify(success_response(data=data.get('data', {})))

    except Exception as e:
        logger.error(f"获取执行详情失败: {e}")
        return error_response("获取执行详情失败", 500)


@zentao_bp.route('/sync/cases', methods=['POST'])
@login_required
def sync_cases():
    """同步禅道测试用例到本地"""
    try:
        data = request.get_json()
        product_id = data.get('product_id', 1)

        response, error = zentao_api_request_with_auth('GET', f'api.php/v1/testcases?product_id={product_id}')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        result = response.json()
        cases = result.get('data', [])

        synced_count = 0

        for case in cases:
            sql = """
                INSERT INTO test_task (name, description, task_type, target_url, created_by)
                VALUES (%s, %s, 'zentao', %s, %s)
                ON DUPLICATE KEY UPDATE
                    description = VALUES(description),
                    updated_at = NOW()
            """

            try:
                Database.execute_update(
                    sql,
                    (
                        case.get('title', 'Unknown'),
                        case.get('precondition', ''),
                        f"zentao://testcase/{case.get('id', 0)}",
                        request.current_user['id']
                    )
                )
                synced_count += 1
            except Exception as e:
                logger.warning(f"同步用例失败: {case.get('title')}, {e}")
                continue

        return jsonify(success_response(
            data={
                "synced_count": synced_count,
                "total_cases": len(cases)
            },
            message=f"成功同步 {synced_count} 个测试用例"
        ))

    except Exception as e:
        logger.error(f"同步测试用例失败: {e}")
        return error_response("同步测试用例失败", 500)
