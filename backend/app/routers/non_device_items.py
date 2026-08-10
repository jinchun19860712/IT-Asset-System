"""非设备物品路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/non-device-items", tags=["非设备物品"])


@router.post("", response_model=schemas.NonDeviceItemOut)
def create_item(item: schemas.NonDeviceItemCreate, db: Session = Depends(get_db)):
    return crud.create_non_device_item(db, item)


@router.get("")
def list_items(folder_id: int = None, db: Session = Depends(get_db)):
    items = crud.get_non_device_items(db, folder_id)
    return {"code": 0, "data": items}


@router.get("/{item_id}", response_model=schemas.NonDeviceItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = crud.get_non_device_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    return item


@router.put("/{item_id}", response_model=schemas.NonDeviceItemOut)
def update_item(item_id: int, item: schemas.NonDeviceItemBase, db: Session = Depends(get_db)):
    updated = crud.update_non_device_item(db, item_id, item)
    if not updated:
        raise HTTPException(status_code=404, detail="物品不存在")
    return updated


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    success = crud.delete_non_device_item(db, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="物品不存在")
    return {"code": 0, "message": "删除成功"}
