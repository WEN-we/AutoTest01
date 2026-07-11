"""
Flask应用工厂
Web平台后端入口
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from utils.tools.path_manager import (
    get_web_platform_frontend_path,
    get_web_platform_config_path,
    get_web_platform_backend_path,
    get_path
)
from backend.config.settings import Config
from backend.api import (
    auth_bp, tasks_bp, ai_models_bp, jenkins_bp,
    zentao_bp, reports_bp, integrations_bp, execution_bp, ai_agents_bp
)
from backend.constants.app import MAX_CONTENT_LENGTH, UPLOAD_FOLDER, CORS_ORIGINS, CORS_RESOURCES
from backend.constants.routes import API_PREFIXES, FRONTEND_ROUTES, DYNAMIC_ROUTES, STATIC_ROUTES


class SecurityHeadersMiddleware:
    """WSGI中间件：为所有响应注入安全响应头"""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        is_https = environ.get('wsgi.url_scheme') == 'https'

        def custom_start_response(status, headers, exc_info=None):
            headers.append(('X-Content-Type-Options', 'nosniff'))
            headers.append(('X-Frame-Options', 'DENY'))
            headers.append(('X-XSS-Protection', '1; mode=block'))
            headers.append(('Referrer-Policy', 'strict-origin-when-cross-origin'))
            headers.append(('Permissions-Policy', 'camera=(), microphone=(), geolocation=()'))
            if is_https:
                headers.append(('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'))
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)


def create_app(config_name='development'):
    """创建Flask应用"""
    backend_dir = get_web_platform_backend_path()
    frontend_dir = get_web_platform_frontend_path()
    config_dir = get_web_platform_config_path()
    project_root = get_path()

    app = Flask(__name__, template_folder=frontend_dir, static_folder=frontend_dir)

    # 加载配置
    config = Config(config_name, config_dir=config_dir)
    app.config['SECRET_KEY'] = config.get('security.jwt_secret')
    app.config['JWT_EXPIRATION_HOURS'] = config.get('security.jwt_expiration_hours')
    app.config['MAX_LOGIN_ATTEMPTS'] = config.get('security.max_login_attempts')
    app.config['LOCKOUT_MINUTES'] = config.get('security.lockout_minutes')
    app.config['DATABASE'] = config.get('database')

    # 文件上传配置（使用常量）
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = get_web_platform_backend_path(UPLOAD_FOLDER)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # CORS配置（使用常量）
    CORS(app, resources={CORS_RESOURCES: {"origins": CORS_ORIGINS}})

    # 注册API蓝图（使用常量）
    app.register_blueprint(auth_bp, url_prefix=API_PREFIXES['auth'])
    app.register_blueprint(tasks_bp, url_prefix=API_PREFIXES['tasks'])
    app.register_blueprint(execution_bp, url_prefix=API_PREFIXES['execution'])
    app.register_blueprint(ai_models_bp, url_prefix=API_PREFIXES['ai_models'])
    app.register_blueprint(ai_agents_bp, url_prefix=API_PREFIXES['ai_agents'])
    app.register_blueprint(integrations_bp, url_prefix=API_PREFIXES['integrations'])
    app.register_blueprint(jenkins_bp, url_prefix=API_PREFIXES['jenkins'])
    app.register_blueprint(zentao_bp, url_prefix=API_PREFIXES['zentao'])
    app.register_blueprint(reports_bp, url_prefix=API_PREFIXES['reports'])

    # 应用安全响应头WSGI中间件
    app.wsgi_app = SecurityHeadersMiddleware(app.wsgi_app)

    # 注册前端静态路由（使用常量循环注册）
    for route in FRONTEND_ROUTES:
        _register_static_route(app, route['path'], route['file'], frontend_dir)

    # 注册动态路由（使用常量）
    for route in DYNAMIC_ROUTES:
        _register_dynamic_route(app, route['path'], route['file'], frontend_dir)

    # 注册静态资源路由（使用路径管理工具）
    @app.route(STATIC_ROUTES['static'])
    def serve_static(filename):
        return send_from_directory(get_web_platform_frontend_path('static'), filename)

    @app.route(STATIC_ROUTES['avatars'])
    def serve_avatars(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route(STATIC_ROUTES['allure_report'])
    def serve_allure_report(filename):
        """服务Allure报告HTML文件"""
        return send_from_directory(get_path('reports', 'allure-report'), filename)

    @app.route(STATIC_ROUTES['allure_results'])
    def serve_allure_results(filename):
        """服务Allure原始结果文件"""
        return send_from_directory(get_path('reports', 'allure-results'), filename)

    # 健康检查
    @app.route('/health')
    def health():
        return jsonify({"status": "healthy", "service": "test-platform-web"})

    # API根路径
    @app.route('/api/')
    def api_root():
        return jsonify({
            "name": "Test Platform API",
            "version": "1.0.0",
            "endpoints": API_PREFIXES
        })

    return app


def _register_static_route(app, path, filename, frontend_dir):
    """注册静态前端路由"""
    # 使用路径生成唯一端点名称，避免冲突
    endpoint = f"static_{path.strip('/').replace('/', '_').replace('.', '_').replace('-', '_') or 'root'}"
    def route_handler():
        return send_from_directory(frontend_dir, filename)
    route_handler.__name__ = endpoint
    app.route(path, endpoint=endpoint)(route_handler)


def _register_dynamic_route(app, path, filename, frontend_dir):
    """注册动态前端路由（含URL参数）"""
    # 使用路径生成唯一端点名称，避免冲突
    endpoint = f"dynamic_{path.strip('/').replace('/', '_').replace('.', '_').replace('-', '_').replace('<', '').replace('>', '')}"
    def route_handler(**kwargs):
        return send_from_directory(frontend_dir, filename)
    route_handler.__name__ = endpoint
    app.route(path, endpoint=endpoint)(route_handler)


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8081, debug=True)
