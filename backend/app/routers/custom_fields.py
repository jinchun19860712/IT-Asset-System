"""自定义字段路由（增强版：11 种字段类型）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/custom-fields", tags=["自定义字段"])


@router.post("", response_model=schemas.CustomFieldOut)
def create_custom_field(field: schemas.CustomFieldCreate, db: Session = Depends(get_db)):
    """创建自定义字段"""
    return crud.create_custom_field(db, field)


@router.get("")
def list_custom_fields(db: Session = Depends(get_db)):
    """列出所有自定义字段"""
    items = crud.get_custom_fields(db)
    return {"code": 0, "data": items}


@router.get("/{field_id}", response_model=schemas.CustomFieldOut)
def get_custom_field(field_id: int, db: Session = Depends(get_db)):
    """获取单个自定义字段"""
    field = crud.get_custom_field(db, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="字段不存在")
    return field


@router.put("/{field_id}", response_model=schemas.CustomFieldOut)
def update_custom_field(field_id: int, field_update: schemas.CustomFieldUpdate, db: Session = Depends(get_db)):
    """更新自定义字段"""
    updated = crud.update_custom_field(db, field_id, field_update)
    if not updated:
        raise HTTPException(status_code=404, detail="字段不存在")
    return updated


@router.delete("/{field_id}")
def delete_custom_field(field_id: int, db: Session = Depends(get_db)):
    """删除自定义字段（同时清除关联布局与设备值）"""
    success = crud.delete_custom_field(db, field_id)
    if not success:
        raise HTTPException(status_code=404, detail="字段不存在")
    return {"code": 0, "message": "删除成功"}
