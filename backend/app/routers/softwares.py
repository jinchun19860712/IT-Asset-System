"""软件资产管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/softwares", tags=["软件资产"])


def _build_dict(item, db):
    folder_name = item.folder.name if item.folder else None
    return {
        "id": item.id,
        "name": item.name,
        "version": item.version,
        "category": item.category,
        "supplier": item.supplier,
        "folder_id": item.folder_id,
        "folder_name": folder_name,
        "remark": item.remark,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("", response_model=dict)
def list_softwares(
    page: int = 1,
    page_size: int = 50,
    keyword: str = None,
    folder_id: int = None,
    category: str = None,
    db: Session = Depends(get_db)
):
    params = schemas.SoftwareListParams(
        page=page, page_size=page_size, keyword=keyword,
        folder_id=folder_id, category=category
    )
    items, total = crud.get_softwares(db, params)
    return {
        "code": 0,
        "data": {
            "items": [_build_dict(x, db) for x in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }


@router.post("", response_model=dict)
def create(software: schemas.SoftwareCreate, db: Session = Depends(get_db)):
    created = crud.create_software(db, software)
    return {"code": 0, "message": "创建成功", "data": _build_dict(created, db)}


# ========== 批量操作（须注册在 /{software_id} 之前） ==========
@router.post("/bulk-delete", response_model=dict)
def bulk_delete(payload: schemas.BulkIds, db: Session = Depends(get_db)):
    """批量删除软件"""
    result = crud.bulk_delete_softwares(db, payload.ids)
    msg = f"已删除 {result['deleted']} 条软件记录"
    if result["not_found"]:
        msg += f"，{len(result['not_found'])} 条未找到"
    return {"code": 0, "message": msg, "data": result}


@router.post("/bulk-update", response_model=dict)
def bulk_update(payload: schemas.SoftwareBulkUpdate, db: Session = Depends(get_db)):
    """批量修改软件（只更新显式传入的字段）"""
    result = crud.bulk_update_softwares(db, payload)
    if not result["fields"]:
        return {"code": 1, "message": "未指定要修改的字段", "data": result}
    return {"code": 0, "message": f"已更新 {result['updated']} 条软件记录", "data": result}


@router.get("/{software_id}", response_model=dict)
def get(software_id: int, db: Session = Depends(get_db)):
    item = crud.get_software(db, software_id)
    if not item:
        raise HTTPException(status_code=404, detail="软件不存在")
    return {"code": 0, "data": _build_dict(item, db)}


@router.put("/{software_id}", response_model=dict)
def update(software_id: int, item_update: schemas.SoftwareUpdate, db: Session = Depends(get_db)):
    updated = crud.update_software(db, software_id, item_update)
    if not updated:
        raise HTTPException(status_code=404, detail="软件不存在")
    return {"code": 0, "message": "更新成功", "data": _build_dict(updated, db)}


@router.delete("/{software_id}")
def delete(software_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_software(db, software_id)
    if not ok:
        raise HTTPException(status_code=404, detail="软件不存在")
    return {"code": 0, "message": "删除成功"}
