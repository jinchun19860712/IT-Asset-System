"""告警路由：列表 / ack / 统计。

权限：所有登录用户可查看自己设备相关的告警；ack 写操作仅登录用户即可，
管理员可加特殊过滤（全部设备）。靠现有 AuthMiddleware + Depends(require_user)。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.auth import require_user
from app.database import get_db
from app.models import Alert, User


router = APIRouter(prefix="/alerts", tags=["告警"])


class BatchAckPayload(BaseModel):
    ids: List[int] = []


def _alert_to_out(a: Alert) -> dict:
    return {
        "id": a.id,
        "device_id": a.device_id,
        "device_name": a.device_name,
        "metric_name": a.metric_name,
        "metric_oid": a.metric_oid,
        "value": a.value,
        "unit": a.unit,
        "threshold": a.threshold,
        "level": a.level,
        "message": a.message,
        "acknowledged": bool(a.acknowledged),
        "acknowledged_by": a.acknowledged_by or "",
        "acknowledged_at": a.acknowledged_at.strftime("%Y-%m-%d %H:%M:%S") if a.acknowledged_at else None,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "",
    }


@router.get("")
def list_alerts(
    keyword: Optional[str] = None,
    level: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    device_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """告警列表（分页），可按 level / device / ack 状态过滤。

    默认只返回最新的 page_size 条；前端可继续翻页。
    """
    q = db.query(Alert).order_by(Alert.created_at.desc())
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(
            (Alert.device_name.like(like))
            | (Alert.metric_name.like(like))
            | (Alert.message.like(like))
        )
    if level in ("warning", "critical", "ok"):
        q = q.filter(Alert.level == level)
    if acknowledged is not None:
        q = q.filter(Alert.acknowledged == bool(acknowledged))
    if device_id is not None:
        q = q.filter(Alert.device_id == device_id)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "data": {
            "items": [_alert_to_out(a) for a in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/active-count")
def active_count(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """当前未确认告警数量（含按 level 拆分），供 Layout 顶部铃铛 badge 轮询。"""
    rows = db.query(Alert.level, sqlfunc.count(Alert.id)).filter(
        Alert.acknowledged == False
    ).group_by(Alert.level).all()
    by_level = {row[0]: row[1] for row in rows}
    total = sum(by_level.values())
    return {
        "code": 0,
        "data": {
            "total": total,
            "warning": by_level.get("warning", 0),
            "critical": by_level.get("critical", 0),
            "ok": by_level.get("ok", 0),
        },
    }


@router.get("/active")
def active_alerts(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """未确认告警最近 N 条，铃铛下拉里直接展示。"""
    items = db.query(Alert).filter(
        Alert.acknowledged == False
    ).order_by(Alert.created_at.desc()).limit(limit).all()
    return {
        "code": 0,
        "data": [_alert_to_out(a) for a in items],
    }


@router.post("/{alert_id}/ack")
def ack_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """确认一条告警（标 acknowledged=当前用户名 + 时间）。"""
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        return {"code": 1, "message": "告警不存在"}
    if a.acknowledged:
        return {"code": 0, "message": "该告警已确认", "data": _alert_to_out(a)}
    a.acknowledged = True
    a.acknowledged_by = user.username
    a.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(a)
    return {"code": 0, "message": "已确认", "data": _alert_to_out(a)}


@router.post("/ack-batch")
def ack_batch(
    payload: BatchAckPayload,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """批量确认告警。payload: { ids: [int] }"""
    if not payload.ids:
        return {"code": 1, "message": "请提供 ids 列表"}
    rows = db.query(Alert).filter(
        Alert.id.in_(payload.ids),
        Alert.acknowledged == False,
    ).all()
    for a in rows:
        a.acknowledged = True
        a.acknowledged_by = user.username
        a.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"code": 0, "message": f"已确认 {len(rows)} 条", "data": {"acknowledged": len(rows)}}


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """删除一条告警（任何登录用户均可用于清理已确认 / 误报告警）。"""
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        return {"code": 1, "message": "告警不存在"}
    db.delete(a)
    db.commit()
    return {"code": 0, "message": "已删除"}
