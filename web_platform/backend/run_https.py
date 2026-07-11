"""
测试平台HTTPS启动脚本
同时启动HTTP(8081)和HTTPS(8443)服务，HTTP自动重定向到HTTPS
"""
import os
import sys
import ssl
import threading
from ipaddress import ip_address
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app import create_app


def generate_self_signed_cert(cert_dir):
    """生成自签名SSL证书"""
    cert_path = os.path.join(cert_dir, 'server.crt')
    key_path = os.path.join(cert_dir, 'server.key')

    # 如果证书已存在，直接返回
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"使用现有SSL证书: {cert_dir}")
        return cert_path, key_path

    print("正在生成自签名SSL证书...")
    os.makedirs(cert_dir, exist_ok=True)

    # 生成RSA私钥
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 构建证书主题
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Platform"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    # 构建证书
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("*.localhost"),
            x509.IPAddress(ip_address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # 保存私钥
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # 保存证书
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"SSL证书已生成: {cert_dir}")
    return cert_path, key_path


def run_http_redirect_server():
    """启动HTTP重定向服务器，将所有请求重定向到HTTPS"""
    from flask import Flask, redirect, request

    redirect_app = Flask('redirect')

    @redirect_app.route('/', defaults={'path': ''})
    @redirect_app.route('/<path:path>')
    def redirect_to_https(path):
        """将HTTP请求重定向到HTTPS"""
        https_url = request.url.replace('http://', 'https://', 1).replace(':8081', ':8443', 1)
        return redirect(https_url, code=301)

    print("HTTP重定向服务已启动: http://localhost:8081 -> https://localhost:8443")
    redirect_app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False)


def run_https_server():
    """启动HTTPS服务器"""
    cert_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'certs')

    cert_path, key_path = generate_self_signed_cert(cert_dir)

    app = create_app()

    print("=" * 60)
    print("测试平台服务已启动")
    print(f"HTTPS访问地址: https://localhost:8443")
    print(f"HTTP访问地址:  http://localhost:8081 (自动重定向到HTTPS)")
    print(f"API地址:        https://localhost:8443/api/")
    print("=" * 60)
    print("注意: 由于是自签名证书，浏览器可能会显示安全警告，")
    print("      请点击'高级' -> '继续前往localhost(不安全)'")
    print("=" * 60)

    app.run(
        host='0.0.0.0',
        port=8443,
        ssl_context=(cert_path, key_path),
        debug=True,
        use_reloader=False
    )


if __name__ == '__main__':
    # 启动HTTP重定向服务（在后台线程）
    http_thread = threading.Thread(target=run_http_redirect_server, daemon=True)
    http_thread.start()

    # 启动HTTPS主服务
    run_https_server()
