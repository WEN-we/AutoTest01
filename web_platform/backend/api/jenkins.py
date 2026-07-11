"""
Jenkins集成API接口
"""
from flask import Blueprint, request, jsonify
from backend.models.integration import Integration
from backend.utils.decorators import login_required
from backend.utils.response import success_response, error_response
import requests
import base64
from urllib.parse import quote

jenkins_bp = Blueprint('jenkins', __name__)


def get_jenkins_config():
    """获取Jenkins配置（优先返回默认配置）"""
    # 先查找默认配置
    config = Integration.find_default_by_type('jenkins')
    if config:
        return config
    # 没有默认配置，则返回第一条有凭证的配置
    return Integration.find_by_type_with_credentials('jenkins')


def jenkins_request_for_config(config, method, path, data=None):
    """Jenkins API请求 - 使用指定配置"""
    if not config:
        return None, "Jenkins未配置"

    # 兼容两种存储格式：credentials嵌套字典 或 直接字段
    username = config.get('username', '')
    api_token = config.get('api_token', '')

    if not username or not api_token:
        return None, "Jenkins凭证未配置"

    base_url = config['base_url'].rstrip('/')
    url = f"{base_url}/{path}"

    auth_str = f"{username}:{api_token}"
    auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
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


def check_status_for_config(config):
    """检查指定配置的连接状态"""
    try:
        if not config:
            return success_response(data={"connected": False, "message": "Jenkins未配置"})

        base_url = config.get('base_url', '').strip().rstrip('/')
        if not base_url:
            return success_response(data={"connected": False, "message": "服务地址未配置"})

        if not base_url.startswith('http://') and not base_url.startswith('https://'):
            return success_response(data={"connected": False, "message": "服务地址必须以http://或https://开头"})

        if len(base_url.split('://')[1]) < 3:
            return success_response(data={"connected": False, "message": "服务地址格式不正确"})

        username = config.get('username') or ''
        api_token = config.get('api_token') or ''

        if not username:
            return success_response(data={"connected": False, "message": "用户名未配置"})

        if not api_token:
            return success_response(data={"connected": False, "message": "API Token未配置"})

        response, error = jenkins_request_for_config(config, 'GET', 'api/json')

        if error:
            return success_response(data={"connected": False, "message": error})

        if response and response.status_code == 200:
            data = response.json()
            return success_response(data={
                "connected": True,
                "message": "连接成功",
                "jenkins_url": config['base_url'],
                "version": data.get('version', 'Unknown'),
                "jobs_count": len(data.get('jobs', []))
            })
        else:
            return success_response(data={
                "connected": False,
                "message": f"Jenkins返回错误: {response.status_code if response else 'None'}"
            })
    except Exception as e:
        print(f"检查Jenkins状态失败: {e}")
        return error_response("检查Jenkins状态失败", 500)


def jenkins_request(method, path, data=None):
    """Jenkins API请求"""
    config = get_jenkins_config()
    return jenkins_request_for_config(config, method, path, data)


@jenkins_bp.route('/status', methods=['GET'])
@login_required
def check_status():
    """检查Jenkins连接状态"""
    try:
        config = get_jenkins_config()

        if not config:
            return success_response(data={"connected": False, "message": "Jenkins未配置"})

        response, error = jenkins_request('GET', 'api/json')

        if error:
            return success_response(data={"connected": False, "message": error})

        if response and response.status_code == 200:
            data = response.json()
            return success_response(data={
                "connected": True,
                "message": "连接成功",
                "jenkins_url": config['base_url'],
                "version": data.get('version', 'Unknown'),
                "jobs_count": len(data.get('jobs', []))
            })
        else:
            return success_response(data={
                "connected": False,
                "message": f"Jenkins返回错误: {response.status_code if response else 'None'}"
            })

    except Exception as e:
        print(f"检查Jenkins状态失败: {e}")
        return error_response("检查Jenkins状态失败", 500)


@jenkins_bp.route('/jobs', methods=['GET'])
@login_required
def get_jobs():
    """获取Jenkins任务列表"""
    try:
        response, error = jenkins_request('GET', 'api/json')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        data = response.json()
        jobs = data.get('jobs', [])

        job_list = []
        for job in jobs:
            job_list.append({
                "name": job.get('name'),
                "url": job.get('url'),
                "color": job.get('color'),
                "last_build": job.get('lastBuild', {}),
                "last_success": job.get('lastSuccessfulBuild', {}),
                "last_failure": job.get('lastFailedBuild', {})
            })

        return success_response(data={"jobs": job_list, "total": len(job_list)})

    except Exception as e:
        print(f"获取Jenkins任务列表失败: {e}")
        return error_response("获取任务列表失败", 500)


@jenkins_bp.route('/jobs/<job_name>', methods=['GET'])
@login_required
def get_job_detail(job_name):
    """获取任务详情"""
    try:
        encoded_job = quote(job_name, safe='')
        response, error = jenkins_request('GET', f'job/{encoded_job}/api/json')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        data = response.json()

        return success_response(data={
            "name": data.get('name'),
            "description": data.get('description'),
            "url": data.get('url'),
            "buildable": data.get('buildable'),
            "builds_count": len(data.get('builds', []))
        })

    except Exception as e:
        print(f"获取任务详情失败: {e}")
        return error_response("获取任务详情失败", 500)


@jenkins_bp.route('/build', methods=['POST'])
@login_required
def trigger_build():
    """触发Jenkins构建"""
    try:
        data = request.get_json()
        job_name = data.get('job_name')
        parameters = data.get('parameters', {})

        if not job_name:
            return error_response("任务名称不能为空")

        encoded_job = quote(job_name, safe='')

        if parameters:
            path = f'job/{encoded_job}/buildWithParameters'
            response, error = jenkins_request('POST', path, parameters)
        else:
            path = f'job/{encoded_job}/build'
            response, error = jenkins_request('POST', path)

        if error:
            return error_response(error, 400)

        if response and response.status_code in [200, 201]:
            queue_location = response.headers.get('Location', '')
            return success_response(
                data={
                    "status": "triggered",
                    "job_name": job_name,
                    "queue_url": queue_location
                },
                message="构建已触发"
            )
        else:
            return error_response(f"构建触发失败: {response.status_code if response else 'None'}", 400)

    except Exception as e:
        print(f"触发Jenkins构建失败: {e}")
        return error_response("触发构建失败", 500)


@jenkins_bp.route('/build/<job_name>/<int:build_number>', methods=['GET'])
@login_required
def get_build_status(job_name, build_number):
    """获取构建状态"""
    try:
        encoded_job = quote(job_name, safe='')
        response, error = jenkins_request('GET', f'job/{encoded_job}/{build_number}/api/json')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        data = response.json()

        return success_response(data={
            "number": data.get('number'),
            "result": data.get('result'),
            "building": data.get('building'),
            "duration": data.get('duration'),
            "url": data.get('url')
        })

    except Exception as e:
        print(f"获取构建状态失败: {e}")
        return error_response("获取构建状态失败", 500)


@jenkins_bp.route('/build/<job_name>/<int:build_number>/console', methods=['GET'])
@login_required
def get_build_console(job_name, build_number):
    """获取构建日志"""
    try:
        encoded_job = quote(job_name, safe='')
        response, error = jenkins_request('GET', f'job/{encoded_job}/{build_number}/consoleText')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        return success_response(data={
            "console_output": response.text,
            "length": len(response.text)
        })

    except Exception as e:
        print(f"获取构建日志失败: {e}")
        return error_response("获取构建日志失败", 500)
