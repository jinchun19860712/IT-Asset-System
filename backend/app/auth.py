"""鉴权层：session 管理 + FastAPI 依赖函数。

设计：
- 密码哈希用 pbkdf2（见 utils/security.py），无第三方依赖。
- 会话存储在进程级 dict：重启后登录失效（开发够用；生产可换 Redis）。
- Session 通过 HttpOnly Cookie 传递（key 名 `itam_session`）。
- FastAPI 依赖：
    get_current_user_optional  - 可选用户（未登录返回 None）
    require_user              - 必须登录（否则 401）
    require_admin             - 必须管理员（否则 403）

公开路径白名单见 main.py 的 PUBLIC_PATHS，未登录也可访问。
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.utils.security import hash_password as _hash_pw


SESSION_COOKIE = "itam_session"
SESSION_TTL = timedelta(days=7)  # 7 天有效期
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # 仅首次启动未配置用户时使用，提醒用户尽快改


# 进程级 session 存储：token -> {user_id, username, role, expires_at}
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def hash_password(password: str) -> str:
    """对外暴露的密码哈希（包装 utils.security）。"""
    return _hash_pw(password)


def _purge_expired() -> None:
    """惰性清理过期 session。get_session 时调用。"""
    now = datetime.utcnow()
    expired = [tok for tok, s in _SESSIONS.items() if s["expires_at"] < now]
    for tok in expired:
        _SESSIONS.pop(tok, None)


def create_session(user_id: int, username: str, role: str) -> str:
    """创建新 session 并返回 token（同时也已写入 _SESSIONS）。"""
    _purge_expired()
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    _SESSIONS[token] = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "created_at": now,
        "expires_at": now + SESSION_TTL,
    }
    return token


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """从 token 取出 session info。过期 / 不存在返回 None。"""
    sess = _SESSIONS.get(token)
    if not sess:
        return None
    if sess["expires_at"] < datetime.utcnow():
        _SESSIONS.pop(token, None)
        return None
    return sess


def destroy_session(token: str) -> bool:
    """销毁 session，返回是否实际删除（用于判断之前是否登录过）。"""
    return _SESSIONS.pop(token, None) is not None


def active_session_count() -> int:
    """当前在线 session 数（调试用）。"""
    _purge_expired()
    return len(_SESSIONS)


# ============== FastAPI 依赖 ==============

def _read_session_cookie(itam_session: Optional[str] = Cookie(default=None)) -> Optional[str]:
    return itam_session


def get_current_user_optional(
    db: Session = Depends(get_db),
    itam_session: Optional[str] = Depends(_read_session_cookie),
) -> Optional[User]:
    """可选用户：未登录返回 None，登录返回 User 对象。is_active=False 也视为未登录。"""
    if not itam_session:
        return None
    sess = get_session(itam_session)
    if not sess:
        return None
    user = db.query(User).filter(User.id == sess["user_id"]).first()
    if user is None or not user.is_active:
        # 用户被删或停用，session 立即作废
        destroy_session(itam_session)
        return None
    return user


def require_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """强制要求登录。未登录返回 401。"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "未登录或登录已过期"},
        )
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """强制要求管理员身份。非管理员返回 403。"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "message": "需要管理员权限"},
        )
    return user
