"""生辰敏感数据加密工具：AES-256-GCM。

密钥 BIRTH_DATA_KEY（base64 编码 32 字节）从配置读取：
- 未配置时 dev 环境生成临时密钥并打警告日志（重启即失效，仅限本地调试）；
- prod 环境未配置直接启动报错，禁止静默降级。
"""

from __future__ import annotations

import base64
import logging
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger(__name__)


def _load_key() -> bytes:
    raw = (settings.BIRTH_DATA_KEY or "").strip()
    if raw:
        try:
            return base64.b64decode(raw, validate=True)
        except Exception:
            raise RuntimeError("BIRTH_DATA_KEY 不是合法的 base64 字符串") from None
    if settings.APP_ENV == "prod":
        raise RuntimeError(
            "prod 环境必须配置 BIRTH_DATA_KEY（base64 编码 32 字节），"
            "生成方式：openssl rand -base64 32"
        )
    logger.warning("BIRTH_DATA_KEY 未配置，dev 环境生成临时密钥（重启失效，仅限本地调试）")
    return secrets.token_bytes(32)


_KEY = _load_key()


def encrypt_text(plaintext: str) -> str:
    """AES-256-GCM 加密文本，返回 base64(nonce + ciphertext+tag)。"""
    if plaintext is None:
        return plaintext
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_KEY).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_text(ciphertext: str) -> str:
    """解密 encrypt_text 的输出。"""
    data = base64.b64decode(ciphertext)
    nonce, payload = data[:12], data[12:]
    return AESGCM(_KEY).decrypt(nonce, payload, None).decode("utf-8")
