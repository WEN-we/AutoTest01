/**
 * RSA密码加密工具
 * 使用Web Crypto API实现RSA-OAEP加密
 * 兼容HTTP环境：如果crypto.subtle不可用，回退到明文传输
 */

const PasswordCrypto = {
    /**
     * 检查是否支持Web Crypto API
     */
    isSupported() {
        return typeof window !== 'undefined' &&
               window.crypto &&
               window.crypto.subtle &&
               typeof window.crypto.subtle.importKey === 'function';
    },

    /**
     * 将PEM格式的公钥导入为CryptoKey
     */
    async importPublicKey(pem) {
        const pemHeader = '-----BEGIN PUBLIC KEY-----';
        const pemFooter = '-----END PUBLIC KEY-----';
        const pemContents = pem
            .replace(pemHeader, '')
            .replace(pemFooter, '')
            .replace(/\s/g, '');
        const binaryDer = window.atob(pemContents);
        const binaryDerBuffer = new Uint8Array(binaryDer.length);
        for (let i = 0; i < binaryDer.length; i++) {
            binaryDerBuffer[i] = binaryDer.charCodeAt(i);
        }
        return window.crypto.subtle.importKey(
            'spki',
            binaryDerBuffer,
            {
                name: 'RSA-OAEP',
                hash: 'SHA-256'
            },
            false,
            ['encrypt']
        );
    },

    /**
     * 加密密码
     * @param {string} password - 明文密码
     * @param {string} publicKeyPem - PEM格式公钥
     * @returns {string} Base64编码的加密密码
     */
    async encryptPassword(password, publicKeyPem) {
        if (!this.isSupported()) {
            console.warn('Web Crypto API不可用，密码将以明文传输。请使用HTTPS以确保安全。');
            return password;
        }
        const publicKey = await this.importPublicKey(publicKeyPem);
        const encoder = new TextEncoder();
        const data = encoder.encode(password);
        const encrypted = await window.crypto.subtle.encrypt(
            {
                name: 'RSA-OAEP'
            },
            publicKey,
            data
        );
        return window.btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    },

    /**
     * 获取公钥并加密密码
     * @param {string} password - 明文密码
     * @param {string} publicKeyUrl - 获取公钥的API地址
     * @returns {string} Base64编码的加密密码
     */
    async encryptPasswordWithKey(password, publicKeyPem) {
        return await this.encryptPassword(password, publicKeyPem);
    }
};
