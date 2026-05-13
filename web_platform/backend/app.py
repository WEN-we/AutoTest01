"""
Flask应用工厂
Web平台后端入口
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from utils.tools.path_manager import get_web_platform_path, get_web_platform_frontend_path, get_web_platform_config_path, get_web_platform_backend_path
from backend.config.settings import Config
from backend.api import auth_bp, tasks_bp, ai_models_bp, jenkins_bp, zentao_bp, reports_bp, integrations_bp, execution_bp


def create_app(config_name='development'):
    """创建Flask应用"""
    backend_dir = get_web_platform_backend_path()
    frontend_dir = get_web_platform_frontend_path()
    config_dir = get_web_platform_config_path()

    app = Flask(__name__, template_folder=frontend_dir, static_folder=frontend_dir)

    config = Config(config_name, config_dir=config_dir)
    app.config['SECRET_KEY'] = config.get('security.jwt_secret')
    app.config['JWT_EXPIRATION_HOURS'] = config.get('security.jwt_expiration_hours')
    app.config['MAX_LOGIN_ATTEMPTS'] = config.get('security.max_login_attempts')
    app.config['LOCKOUT_MINUTES'] = config.get('security.lockout_minutes')
    app.config['DATABASE'] = config.get('database')

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(execution_bp, url_prefix='/api')
    app.register_blueprint(ai_models_bp, url_prefix='/api/ai-models')
    app.register_blueprint(integrations_bp, url_prefix='/api/integrations')
    app.register_blueprint(jenkins_bp, url_prefix='/api/integrations/jenkins')
    app.register_blueprint(zentao_bp, url_prefix='/api/integrations/zentao')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')

    @app.route('/')
    def index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/index.html')
    def index_html():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/dashboard')
    def dashboard():
        return send_from_directory(frontend_dir, 'dashboard.html')

    @app.route('/dashboard.html')
    def dashboard_html():
        return send_from_directory(frontend_dir, 'dashboard.html')

    @app.route('/tasks')
    def tasks():
        return send_from_directory(frontend_dir, 'tasks.html')

    @app.route('/tasks.html')
    def tasks_html():
        return send_from_directory(frontend_dir, 'tasks.html')

    @app.route('/tasks/create')
    def tasks_create():
        return send_from_directory(frontend_dir, 'tasks-create.html')

    @app.route('/tasks-create.html')
    def tasks_create_html():
        return send_from_directory(frontend_dir, 'tasks-create.html')

    @app.route('/tasks/<task_id>')
    def task_detail(task_id):
        return send_from_directory(frontend_dir, 'tasks-detail.html')

    @app.route('/tasks-detail.html')
    def tasks_detail_html():
        return send_from_directory(frontend_dir, 'tasks-detail.html')

    @app.route('/execution/<execution_id>')
    def execution_monitor(execution_id):
        return send_from_directory(frontend_dir, 'execution-monitor.html')

    @app.route('/execution-monitor.html')
    def execution_monitor_html():
        return send_from_directory(frontend_dir, 'execution-monitor.html')

    @app.route('/execution-list.html')
    def execution_list_html():
        return send_from_directory(frontend_dir, 'execution-list.html')

    @app.route('/jenkins')
    def jenkins():
        return send_from_directory(frontend_dir, 'jenkins.html')

    @app.route('/jenkins.html')
    def jenkins_html():
        return send_from_directory(frontend_dir, 'jenkins.html')

    @app.route('/zentao')
    def zentao():
        return send_from_directory(frontend_dir, 'zentao.html')

    @app.route('/zentao.html')
    def zentao_html():
        return send_from_directory(frontend_dir, 'zentao.html')

    @app.route('/integrations')
    def integrations():
        return send_from_directory(frontend_dir, 'integrations.html')

    @app.route('/integrations.html')
    def integrations_html():
        return send_from_directory(frontend_dir, 'integrations.html')

    @app.route('/reports')
    def reports():
        return send_from_directory(frontend_dir, 'reports.html')

    @app.route('/reports.html')
    def reports_html():
        return send_from_directory(frontend_dir, 'reports.html')

    @app.route('/ai-models')
    def ai_models():
        return send_from_directory(frontend_dir, 'ai-models.html')

    @app.route('/ai-models.html')
    def ai_models_html():
        return send_from_directory(frontend_dir, 'ai-models.html')

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(os.path.join(frontend_dir, 'static'), filename)

    @app.route('/health')
    def health():
        return jsonify({"status": "healthy", "service": "test-platform-web"})

    @app.route('/api/')
    def api_root():
        return jsonify({
            "name": "Test Platform API",
            "version": "1.0.0",
            "endpoints": {
                "auth": "/api/auth",
                "tasks": "/api/tasks",
                "ai_models": "/api/ai-models",
                "integrations": "/api/integrations",
                "reports": "/api/reports",
                "execution": "/api/execution"
            }
        })

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8081, debug=True)
