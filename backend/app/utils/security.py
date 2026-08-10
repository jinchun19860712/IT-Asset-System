"""鉴权基础工具：密码 hash / verify。

使用 Python 标准库 hashlib.pbkdf2_hmac（不需要额外依赖），格式：

    pbkdf2$<salt-hex>$<hash-hex>

- 16 字节随机 salt（hex 后 32 字符）
- SHA-256
- 100,000 次迭代（OWASP 推荐值）

存储为单字符串便于 SQLite 直接存放。
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Optional


_PBKDF2_ITERATIONS = 100_000
_SALT_BYTES = 16
_ALGO = "pbkdf2"


def hash_password(password: str) -> str:
    """生成密码哈希串。空密码直接抛错。"""
    if not password:
        raise ValueError("password must be non-empty")
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return f"{_ALGO}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码是否匹配存储的哈希。"""
    if not password or not stored:
        return False
    try:
        algo, salt, expected_hex = stored.split("$", 2)
    except ValueError:
        return False
    if algo != _ALGO or not salt or not expected_hex:
        return False
    try:
        actual_hex = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            _PBKDF2_ITERATIONS,
        ).hex()
    except Exception:
        return False
    # 恒时比较，避免时间侧信道
    return secrets.compare_digest(actual_hex, expected_hex)


def is_password_hash(value: str) -> bool:
    """快速嗅探字符串是否是我们的哈希格式（用于迁移脚本）。"""
    if not value or not isinstance(value, str):
        return False
    return value.startswith(f"{_ALGO}$") and value.count("$") == 2


def validate_password_strength(password: str, min_length: int = 6) -> Optional[str]:
    """校验密码强度，返回 None 表示通过，否则返回错误信息。"""
    if password is None:
        return "密码不能为空"
    if len(password) < min_length:
        return f"密码长度至少 {min_length} 个字符"
    return None
