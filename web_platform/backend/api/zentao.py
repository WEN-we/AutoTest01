"""
禅道集成API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.integration import Integration
from backend.utils.decorators import login_required
import requests

zentao_bp = Blueprint('zentao', __name__)


def success_response(data=None, message="操作成功"):
    response = {"code": 200, "message": message}
    if data:
        response["data"] = data
    return jsonify(response)


def error_response(message, code=400):
    return jsonify({"code": code, "message": message}), code


def get_zentao_config():
    """获取禅道配置"""
    return Integration.find_by_type('zentao')


def get_zentao_token():
    """获取禅道访问令牌"""
    config = get_zentao_config()

    if not config:
        return None, "禅道未配置"

    credentials = config.get('credentials', {})
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
            return {
                "token": data.get('token', ''),
                "token_type": data.get('tokenType', 'Bearer')
            }, None
        else:
            return None, f"获取Token失败: {response.status_code}"

    except Exception as e:
        return None, f"获取Token失败: {str(e)}"


def zentao_request(method, path, data=None):
    """禅道API请求"""
    token_info, error = get_zentao_token()

    if error:
        return None, error

    config = get_zentao_config()
    base_url = config['base_url'].rstrip('/')
    url = f"{base_url}/{path}"

    headers = {
        "Content-Type": "application/json",
        "Token": token_info['token']
    }

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return None, f"不支持的方法: {method}"

        return response, None

    except requests.exceptions.Timeout:
        return None, "请求超时"
    except Exception as e:
        return None, f"请求失败: {str(e)}"


@zentao_bp.route('/status', methods=['GET'])
@login_required
def check_status():
    """检查禅道连接状态"""
    try:
        config = get_zentao_config()

        if not config:
            return success_response(data={"connected": False, "message": "禅道未配置"})

        token_info, error = get_zentao_token()

        if error:
            return success_response(data={"connected": False, "message": error})

        return success_response(data={
            "connected": True,
            "message": "连接成功",
            "zentao_url": config['base_url']
        })

    except Exception as e:
        print(f"检查禅道状态失败: {e}")
        return error_response("检查禅道状态失败", 500)


@zentao_bp.route('/products', methods=['GET'])
@login_required
def get_products():
    """获取产品列表"""
    try:
        response, error = zentao_request('GET', 'api.php/v1/products')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()
        products = data.get('data', [])

        return success_response(data={"products": products, "total": len(products)})

    except Exception as e:
        print(f"获取产品列表失败: {e}")
        return error_response("获取产品列表失败", 500)


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

        response, error = zentao_request('GET', api_path)

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()
        cases = data.get('data', [])
        total = data.get('total', len(cases))

        return success_response(data={
            "cases": cases,
            "total": total,
            "page": page,
            "page_size": page_size
        })

    except Exception as e:
        print(f"获取测试用例列表失败: {e}")
        return error_response("获取测试用例列表失败", 500)


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

        response, error = zentao_request('GET', api_path)

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        data = response.json()
        bugs = data.get('data', [])
        total = data.get('total', len(bugs))

        return success_response(data={
            "bugs": bugs,
            "total": total,
            "page": page,
            "page_size": page_size
        })

    except Exception as e:
        print(f"获取Bug列表失败: {e}")
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

        if not title:
            return error_response("Bug标题不能为空")

        bug_data = {
            "product": product_id,
            "title": title,
            "severity": severity,
            "steps": steps,
            "type": "codeerror"
        }

        response, error = zentao_request('POST', 'api.php/v1/bugs', bug_data)

        if error:
            return error_response(error, 400)

        if response.status_code not in [200, 201]:
            return error_response(f"创建Bug失败: {response.status_code}", 400)

        result = response.json()

        return success_response(
            data={
                "bug_id": result.get('data', {}).get('id', 0)
            },
            message="Bug创建成功"
        )

    except Exception as e:
        print(f"创建Bug失败: {e}")
        return error_response("创建Bug失败", 500)


@zentao_bp.route('/sync/cases', methods=['POST'])
@login_required
def sync_cases():
    """同步禅道测试用例"""
    try:
        data = request.get_json()
        product_id = data.get('product_id', 1)

        response, error = zentao_request('GET', f'api.php/v1/testcases?product_id={product_id}')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"禅道返回错误: {response.status_code}", 400)

        result = response.json()
        cases = result.get('data', [])

        synced_count = len(cases)

        return success_response(
            data={
                "synced_count": synced_count,
                "total_cases": len(cases)
            },
            message=f"成功同步 {synced_count} 个测试用例"
        )

    except Exception as e:
        print(f"同步测试用例失败: {e}")
        return error_response("同步测试用例失败", 500)
