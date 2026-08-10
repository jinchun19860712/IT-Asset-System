"""鉴权路由：登录 / 登出 / 用户管理。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    SESSION_TTL,
    DEFAULT_ADMIN_USERNAME,
    create_session,
    destroy_session,
    get_current_user_optional,
    hash_password,
    require_admin,
    require_user,
)
from app.database import get_db
from app.models import User
from app.utils.security import validate_password_strength, verify_password


router = APIRouter(prefix="/auth", tags=["鉴权"])


# ============== Pydantic schemas ==============

class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    display_name: Optional[str] = ""
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class ChangePasswordPayload(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class ResetPasswordPayload(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


def _user_to_out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name or "",
        "role": u.role,
        "is_active": bool(u.is_active),
        "last_login_at": u.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if u.last_login_at else None,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
    }


# ============== 公开路由 ==============

@router.post("/login")
def login(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """登录验证。成功返回用户信息并设置 cookie。"""
    username = (username or "").strip()
    if not username or not password:
        return {"code": 1, "message": "账号和密码不能为空"}

    user = db.query(User).filter(User.username == username).first()
    from app.routers.audit_logs import record_audit
    if not user or not verify_password(password, user.password_hash):
        # 用户名密码任意错误统一返回「账号或密码错误」，避免用户名枚举
        record_audit(
            db, actor_name=username, action="login", target_type="auth",
            target_name=username, message="登录失败：账号或密码错误",
            request=request, success=False,
        )
        return {"code": 1, "message": "账号或密码错误"}

    if not user.is_active:
        record_audit(
            db, actor_name=username, action="login", target_type="auth",
            target_name=username, message="登录失败：账号已停用",
            request=request, success=False,
        )
        return {"code": 1, "message": "账号已停用，请联系管理员"}

    # 写入最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = create_session(user.id, user.username, user.role)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        # secure=True,  # 生产 HTTPS 启用；本地开发保持 False（vite 走 http）
        path="/",
    )
    record_audit(
        db, actor=user, action="login", target_type="auth",
        target_id=user.id, target_name=user.username,
        message=f"登录成功：{user.username}", request=request, success=True,
    )
    return {"code": 0, "message": "登录成功", "data": _user_to_out(user)}


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """登出：销毁进程级 session，并清 cookie。

    即便 session 已过期，前端调登出也能成功清 cookie。
    """
    from app.routers.audit_logs import record_audit
    if user:
        record_audit(
            db, actor=user, action="logout", target_type="auth",
            target_id=user.id, target_name=user.username,
            message=f"用户登出：{user.username}", request=request, success=True,
        )
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"code": 0, "message": "已登出"}


# ============== 需要登录的路由 ==============

@router.get("/me")
def get_me(user: User = Depends(require_user)):
    """获取当前登录用户信息。"""
    return {"code": 0, "data": _user_to_out(user)}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordPayload,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """当前用户自助改密。"""
    if not verify_password(payload.old_password, user.password_hash):
        return {"code": 1, "message": "原密码错误"}
    err = validate_password_strength(payload.new_password)
    if err:
        return {"code": 1, "message": err}
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"code": 0, "message": "密码已修改，下次登录生效"}


# ============== 管理员专属：用户管理 ==============

@router.get("/users")
def list_users(
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = db.query(User).order_by(User.id)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(
            (User.username.like(like)) | (User.display_name.like(like))
        )
    items = [_user_to_out(u) for u in q.all()]
    return {"code": 0, "data": items}


@router.post("/users")
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    username = (payload.username or "").strip()
    if not username:
        return {"code": 1, "message": "用户名不能为空"}
    if db.query(User).filter(User.username == username).first():
        return {"code": 1, "message": f"用户名「{username}」已存在"}
    err = validate_password_strength(payload.password)
    if err:
        return {"code": 1, "message": err}
    user = User(
        username=username,
        display_name=(payload.display_name or "").strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 0, "message": "创建成功", "data": _user_to_out(user)}


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"code": 1, "message": "用户不存在"}

    # 唯一内置 admin 不能被降级或停用，避免系统无人可管
    if user.username == DEFAULT_ADMIN_USERNAME and user_id == admin.id:
        # 自己改自己：可以改 display_name，但不能把自己降级或停用
        if payload.role is not None and payload.role != "admin":
            return {"code": 1, "message": "不能把自己降级为普通用户"}
        if payload.is_active is False:
            return {"code": 1, "message": "不能停用自己"}
    elif user.username == DEFAULT_ADMIN_USERNAME and user_id != admin.id:
        # 别人不能改默认 admin
        return {"code": 1, "message": "默认管理员账号不可修改"}

    if payload.display_name is not None:
        user.display_name = (payload.display_name or "").strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = bool(payload.is_active)
    db.commit()
    db.refresh(user)
    return {"code": 0, "message": "更新成功", "data": _user_to_out(user)}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"code": 1, "message": "用户不存在"}
    if user.id == admin.id:
        return {"code": 1, "message": "不能删除自己"}
    if user.username == DEFAULT_ADMIN_USERNAME:
        return {"code": 1, "message": "默认管理员账号不可删除"}
    # 至少保留一个管理员
    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if admin_count <= 1:
            return {"code": 1, "message": "至少保留一个管理员账号"}
    db.delete(user)
    db.commit()
    return {"code": 0, "message": "已删除"}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: ResetPasswordPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"code": 1, "message": "用户不存在"}
    err = validate_password_strength(payload.new_password)
    if err:
        return {"code": 1, "message": err}
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"code": 0, "message": f"已重置「{user.username}」的密码"}
