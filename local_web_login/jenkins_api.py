"""
Jenkins集成API
适配web_platform数据库表结构
"""
from flask import Blueprint, request, jsonify
from local_web_login.backend_server import (
    login_required, success_response, error_response,
    Database
)
import requests
import base64
import json
from utils.tools.logger import log as logger

jenkins_bp = Blueprint('jenkins', __name__, url_prefix='/api/integrations/jenkins')


def get_jenkins_config():
    """获取Jenkins配置"""
    sql = """
        SELECT * FROM integration_config
        WHERE integration_type = 'jenkins' AND status = 'active'
        LIMIT 1
    """
    return Database.execute_query(sql, fetch_one=True)


def jenkins_api_request(method, url_path, data=None):
    """Jenkins API请求"""
    config = get_jenkins_config()

    if not config:
        return None, "Jenkins未配置"

    username = config.get('username', '')
    api_token = config.get('api_token', '') or config.get('api_key', '')

    if not username or not api_token:
        return None, "Jenkins凭证未配置"

    base_url = config['base_url'].rstrip('/')
    url = f"{base_url}/{url_path}"

    auth = base64.b64encode(f"{username}:{api_token}".encode()).decode()

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
            return None, f"不支持的请求方法: {method}"

        return response, None
    except requests.exceptions.Timeout:
        return None, "Jenkins请求超时"
    except requests.exceptions.RequestException as e:
        return None, f"Jenkins请求失败: {str(e)}"


@jenkins_bp.route('/status', methods=['GET'])
@login_required
def check_status():
    """检查Jenkins连接状态"""
    try:
        config = get_jenkins_config()

        if not config:
            return jsonify(success_response(
                data={
                    "connected": False,
                    "message": "Jenkins未配置"
                }
            ))

        response, error = jenkins_api_request('GET', 'api/json')

        if error:
            return jsonify(success_response(
                data={
                    "connected": False,
                    "message": error
                }
            ))

        if response.status_code == 200:
            data = response.json()
            return jsonify(success_response(
                data={
                    "connected": True,
                    "message": "连接成功",
                    "jenkins_url": config['base_url'],
                    "version": data.get('version', 'Unknown'),
                    "jobs_count": len(data.get('jobs', []))
                }
            ))
        else:
            return jsonify(success_response(
                data={
                    "connected": False,
                    "message": f"Jenkins返回错误: {response.status_code}"
                }
            ))

    except Exception as e:
        logger.error(f"检查Jenkins状态失败: {e}")
        return error_response("检查Jenkins状态失败", 500)


@jenkins_bp.route('/jobs', methods=['GET'])
@login_required
def get_jobs():
    """获取Jenkins任务列表"""
    try:
        response, error = jenkins_api_request('GET', 'api/json')

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

        return jsonify(success_response(
            data={
                "jobs": job_list,
                "total": len(job_list)
            }
        ))

    except Exception as e:
        logger.error(f"获取Jenkins任务列表失败: {e}")
        return error_response("获取Jenkins任务列表失败", 500)


@jenkins_bp.route('/jobs/<job_name>', methods=['GET'])
@login_required
def get_job_detail(job_name):
    """获取任务详情"""
    try:
        import urllib.parse
        encoded_job = urllib.parse.quote(job_name, safe='')

        response, error = jenkins_api_request('GET', f'job/{encoded_job}/api/json')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        data = response.json()

        job_detail = {
            "name": data.get('name'),
            "description": data.get('description'),
            "url": data.get('url'),
            "buildable": data.get('buildable'),
            "builds": []
        }

        for build in data.get('builds', [])[:10]:
            job_detail['builds'].append({
                "number": build.get('number'),
                "url": build.get('url')
            })

        return jsonify(success_response(data=job_detail))

    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
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

        import urllib.parse
        encoded_job = urllib.parse.quote(job_name, safe='')

        if parameters:
            url_path = f'job/{encoded_job}/buildWithParameters'
            response, error = jenkins_api_request('POST', url_path, data=parameters)
        else:
            url_path = f'job/{encoded_job}/build'
            response, error = jenkins_api_request('POST', url_path)

        if error:
            return error_response(error, 400)

        if response.status_code in [200, 201]:
            queue_location = response.headers.get('Location', '')

            return jsonify(success_response(
                data={
                    "status": "triggered",
                    "job_name": job_name,
                    "queue_url": queue_location
                },
                message="构建已触发"
            ))
        else:
            return error_response(f"构建触发失败: {response.status_code}", 400)

    except Exception as e:
        logger.error(f"触发Jenkins构建失败: {e}")
        return error_response("触发构建失败", 500)


@jenkins_bp.route('/build/<job_name>/<int:build_number>', methods=['GET'])
@login_required
def get_build_status(job_name, build_number):
    """获取构建状态"""
    try:
        import urllib.parse
        encoded_job = urllib.parse.quote(job_name, safe='')

        response, error = jenkins_api_request('GET', f'job/{encoded_job}/{build_number}/api/json')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        data = response.json()

        build_info = {
            "number": data.get('number'),
            "result": data.get('result'),
            "building": data.get('building'),
            "duration": data.get('duration'),
            "timestamp": data.get('timestamp'),
            "url": data.get('url'),
            "artifacts": []
        }

        for artifact in data.get('artifacts', []):
            build_info['artifacts'].append({
                "displayPath": artifact.get('displayPath'),
                "fileName": artifact.get('fileName'),
                "relativePath": artifact.get('relativePath')
            })

        return jsonify(success_response(data=build_info))

    except Exception as e:
        logger.error(f"获取构建状态失败: {e}")
        return error_response("获取构建状态失败", 500)


@jenkins_bp.route('/build/<job_name>/<int:build_number>/console', methods=['GET'])
@login_required
def get_build_console(job_name, build_number):
    """获取构建日志"""
    try:
        import urllib.parse
        encoded_job = urllib.parse.quote(job_name, safe='')

        response, error = jenkins_api_request('GET', f'job/{encoded_job}/{build_number}/consoleText')

        if error:
            return error_response(error, 400)

        if response.status_code != 200:
            return error_response(f"Jenkins返回错误: {response.status_code}", 400)

        return jsonify(success_response(
            data={
                "console_output": response.text,
                "length": len(response.text)
            }
        ))

    except Exception as e:
        logger.error(f"获取构建日志失败: {e}")
        return error_response("获取构建日志失败", 500)
