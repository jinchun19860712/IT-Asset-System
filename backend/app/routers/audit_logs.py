"""审计日志路由与工具函数（N3）。

工具函数 record_audit() 供其他 router 调用，一行记录一条审计日志。
GET /audit-logs/list 供前端列表查询（仅管理员可看）。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth import require_admin, require_user
from app.database import get_db
from app.models import AuditLog, User


router = APIRouter(prefix="/audit-logs", tags=["审计日志"])


def record_audit(
    db: Session,
    *,
    actor: Optional[User] = None,
    actor_name: str = "",
    action: str,
    target_type: str = "",
    target_id: Optional[int] = None,
    target_name: str = "",
    message: str = "",
    request: Optional[Request] = None,
    success: bool = True,
    diff: Optional[Dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """写入一条审计日志。失败不抛错（审计不能阻塞主流程）。"""
    try:
        ip = ""
        ua = ""
        if request is not None:
            # 优先取反向代理头
            xff = request.headers.get("x-forwarded-for")
            ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else ""))
            ua = (request.headers.get("user-agent") or "")[:200]

        log = AuditLog(
            actor_id=actor.id if actor else None,
            actor_name=actor_name or (actor.username if actor else ""),
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            message=message[:500] if message else "",
            ip=ip,
            user_agent=ua,
            success=success,
            diff=json.dumps(diff, ensure_ascii=False, default=str) if diff else "",
        )
        db.add(log)
        db.commit()
        return log
    except Exception as e:
        print(f"[audit] 记录失败: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _log_to_out(l: AuditLog) -> dict:
    return {
        "id": l.id,
        "actor_id": l.actor_id,
        "actor_name": l.actor_name,
        "action": l.action,
        "target_type": l.target_type,
        "target_id": l.target_id,
        "target_name": l.target_name,
        "message": l.message,
        "ip": l.ip,
        "user_agent": l.user_agent,
        "success": l.success,
        "diff": l.diff,
        "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "",
    }


@router.get("")
def list_logs(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """审计日志列表（仅管理员可查）。"""
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if actor:
        q = q.filter(AuditLog.actor_name == actor)
    if action:
        q = q.filter(AuditLog.action == action)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if target_id is not None:
        q = q.filter(AuditLog.target_id == target_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(
            (AuditLog.actor_name.like(like))
            | (AuditLog.target_name.like(like))
            | (AuditLog.message.like(like))
        )

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "data": {
            "items": [_log_to_out(l) for l in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """最近 7 天每天新增审计日志数量（按 action 分类）。"""
    from sqlalchemy import func as sqlfunc
    from datetime import timedelta

    rows = db.query(
        sqlfunc.date(AuditLog.created_at).label("d"),
        AuditLog.action,
        sqlfunc.count(AuditLog.id),
    ).filter(
        AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)
    ).group_by(sqlfunc.date(AuditLog.created_at), AuditLog.action).all()

    by_day = {}
    actions = set()
    for d, a, c in rows:
        actions.add(a)
        by_day.setdefault(str(d), {})[a] = c
    return {
        "code": 0,
        "data": {
            "actions": sorted(actions),
            "by_day": by_day,
        },
    }
