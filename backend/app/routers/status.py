"""设备状态路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/statuses", tags=["设备状态"])


@router.post("", response_model=schemas.DeviceStatusOut)
def create_status(status: schemas.DeviceStatusCreate, db: Session = Depends(get_db)):
    return crud.create_status(db, status)


@router.get("")
def list_statuses(db: Session = Depends(get_db)):
    items = crud.get_statuses(db)
    return {"code": 0, "data": items}


@router.put("/{status_id}", response_model=schemas.DeviceStatusOut)
def update_status(status_id: int, status: schemas.DeviceStatusBase, db: Session = Depends(get_db)):
    updated = crud.update_status(db, status_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="状态不存在")
    return updated


@router.delete("/{status_id}")
def delete_status(status_id: int, db: Session = Depends(get_db)):
    success = crud.delete_status(db, status_id)
    if not success:
        raise HTTPException(status_code=404, detail="状态不存在")
    return {"code": 0, "message": "删除成功"}
