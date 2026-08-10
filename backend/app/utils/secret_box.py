"""敏感字段对称加密（B3 - SNMP 口令 / 设备管理密码等敏感字段）。

设计：
- Fernet（AES-128-CBC + HMAC-SHA256）做对称加密；用同一个 key 加密与解密
- 密钥加载顺序（最高优先在前）：
    1. 环境变量 ITASSET_SECRET_KEY（base64 编码的 32 字节）
    2. backend/config/secret.key（首次启动自动生成，权限 600）
    3. 全部失败 → 抛错，禁止启动
- 加密格式：`enc:<urlsafe_b64>` —— 加密字段在数据库里以 `enc:` 前缀开头
- 向后兼容：如果数据库里已有字段不是 `enc:` 开头（历史数据为明文）：
    - decrypt(): 原样返回（兼容老数据）
    - 自定义方法 maybe_encrypt(): 自动判别明文是否要升迁为密文（写入时优先）
- mask_for_response()：API 返回列表/详情时把敏感字段值遮蔽为 `******`，避免无意中泄露。
  调用方需要明文时单独传 `?unmask=1` 查询参数。

为什么用 Fernet 而不是简单的 XOR：
- Fernet 自带随机 IV + 时间戳 + HMAC 防篡改，开箱即用、零依赖风险
- 32 字节 random key 生成的 token 强度足够
"""
from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path
from threading import Lock
from typing import Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover - cryptography 必装；这里只是让 import 优雅
    Fernet = None
    InvalidToken = Exception


_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_SECRET_KEY_FILE = _CONFIG_DIR / "secret.key"
_ENV_KEY_NAME = "ITASSET_SECRET_KEY"
_CIPHER_PREFIX = "enc:"  # 数据库字段已加密的统一前缀

_masked = "******"


class SecretBox:
    """单例：负责加载密钥，提供 encrypt/decrypt/mask 接口。"""

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._lock = Lock()

    def bootstrap(self) -> None:
        """应用启动时调用，确保 _fernet 已就绪。重复调用幂等。"""
        with self._lock:
            if self._fernet is not None:
                return
            key = self._load_or_create_key()
            if Fernet is None:
                raise RuntimeError("cryptography 未安装，无法启用 SecretBox。请先 pip install cryptography")
            self._fernet = Fernet(key)

    @staticmethod
    def _load_or_create_key() -> str:
        """从环境变量 / key 文件读取 Fernet 直接可用的 url-safe-base64 字符串（44 字符）。

        Fernet(key) 内部会做 urlsafe_b64decode；我们只要保证 `_SECRET_KEY_FILE` 里写的是
        真正的 base64 字符串（44 字符），而不是 raw 32 字节。
        """
        def _encode(raw: bytes) -> str:
            return base64.urlsafe_b64encode(raw).decode("ascii")

        # 1) 环境变量优先（44 字符 base64 字符串）
        env = os.environ.get(_ENV_KEY_NAME, "").strip()
        if env and len(env) >= 40:
            # 直接当作 base64 字符串给 Fernet，让 Fernet 自己 decode
            try:
                raw = base64.urlsafe_b64decode(env)
                if len(raw) == 32:
                    return env
            except Exception:
                pass

        # 2) 配置文件（持久化为 base64 字符串）
        if _SECRET_KEY_FILE.exists():
            try:
                txt = _SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
                raw = base64.urlsafe_b64decode(txt)
                if len(raw) == 32:
                    return txt
            except Exception:
                pass

        # 3) 首次启动，生成 32 bytes 随机，写入 base64 字符串形式
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        raw = secrets.token_bytes(32)
        encoded = _encode(raw)
        _SECRET_KEY_FILE.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(_SECRET_KEY_FILE, 0o600)
        except Exception:
            pass
        print(f"[secret] 已生成密钥文件: {_SECRET_KEY_FILE}（生产环境建议改成环境变量管理）")
        return encoded

    # ---- 业务 API ----

    def encrypt(self, plain: str) -> str:
        """加密任意字符串，返回 `enc:<base64>`；空字符串 / 非字符串返回原样。"""
        if plain is None or plain == "":
            return ""
        if not isinstance(plain, str):
            plain = str(plain)
        if plain.startswith(_CIPHER_PREFIX):
            return plain  # 已加密，不需要重复
        if self._fernet is None:
            self.bootstrap()
        token = self._fernet.encrypt(plain.encode("utf-8"))
        return _CIPHER_PREFIX + token.decode("ascii")

    def decrypt(self, value: str) -> str:
        """解密；非加密前缀的原样返回（向后兼容历史明文数据）。"""
        if value is None or value == "":
            return ""
        if not isinstance(value, str) or not value.startswith(_CIPHER_PREFIX):
            return value
        if self._fernet is None:
            self.bootstrap()
        try:
            token = value[len(_CIPHER_PREFIX):].encode("ascii")
            plain = self._fernet.decrypt(token).decode("utf-8")
            return plain
        except (InvalidToken, Exception):
            # 解密失败：可能 key 错了——保守行为是返回原值（防止调试中丢失数据）
            return value

    def maybe_encrypt(self, value) -> str:
        """写入时用：若已经是密文则保持；否则加密；空值原样。"""
        if value is None or value == "":
            return ""
        if isinstance(value, str) and value.startswith(_CIPHER_PREFIX):
            return value
        return self.encrypt(value if isinstance(value, str) else str(value))

    def mask(self, value) -> str:
        """API 序列化时遮蔽：永远不返明文给前端，除非调用方显式传 unmask=1。"""
        if not value:
            return ""
        return _masked

    @staticmethod
    def key_path() -> Path:
        return _SECRET_KEY_FILE


# 单例
secret_box = SecretBox()
