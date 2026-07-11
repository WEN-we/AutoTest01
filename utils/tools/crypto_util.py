"""
RSA加密工具模块
用于前后端密码加密传输
"""
import base64
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class RSAKeyManager:
    """RSA密钥管理器"""

    def __init__(self, key_dir=None):
        if key_dir is None:
            key_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'keys')
        self.key_dir = key_dir
        os.makedirs(self.key_dir, exist_ok=True)
        self.private_key_path = os.path.join(self.key_dir, 'private_key.pem')
        self.public_key_path = os.path.join(self.key_dir, 'public_key.pem')

    def generate_keys(self):
        """生成RSA密钥对"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        # 保存私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)

        # 保存公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)

        return public_pem.decode('utf-8')

    def load_private_key(self):
        """加载私钥"""
        if not os.path.exists(self.private_key_path):
            self.generate_keys()
        with open(self.private_key_path, 'rb') as f:
            return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

    def load_public_key(self):
        """加载公钥"""
        if not os.path.exists(self.public_key_path):
            self.generate_keys()
        with open(self.public_key_path, 'rb') as f:
            return serialization.load_pem_public_key(f.read(), backend=default_backend())

    def get_public_key_pem(self):
        """获取公钥PEM字符串"""
        if not os.path.exists(self.public_key_path):
            self.generate_keys()
        with open(self.public_key_path, 'r') as f:
            return f.read()


class PasswordCrypto:
    """密码加密工具"""

    def __init__(self, key_dir=None):
        self.key_manager = RSAKeyManager(key_dir)

    def get_public_key(self):
        """获取公钥（用于前端加密）"""
        return self.key_manager.get_public_key_pem()

    def decrypt_password(self, encrypted_password_b64):
        """解密密码（后端使用私钥解密）"""
        try:
            private_key = self.key_manager.load_private_key()
            encrypted_data = base64.b64decode(encrypted_password_b64)
            decrypted = private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted.decode('utf-8')
        except Exception:
            return None


# 全局实例
_password_crypto = None


def get_password_crypto():
    """获取密码加密工具单例"""
    global _password_crypto
    if _password_crypto is None:
        _password_crypto = PasswordCrypto()
    return _password_crypto
