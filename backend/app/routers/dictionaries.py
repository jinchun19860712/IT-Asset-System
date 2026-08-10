"""通用字典路由：品牌 / 供应商 / 软件分类 等
（产品类型已迁移到独立 /product-types 路由，由 ProductTypeManager 统一管理）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/dictionaries", tags=["字典管理"])

# 前端约定的 type 取值
DICT_TYPES = {
    # product_type 已迁移到 /product-types 独立管理
    "device_type": "设备类型",  # 设备型号/类型的快速标签字典（基础数据 → 设备类型）
    "brand": "品牌",
    "supplier": "供应商",
    "software_category": "软件分类",
}


@router.get("/types")
def list_types():
    """返回所有字典分类及其中文名"""
    return {"code": 0, "data": [{"type": k, "label": v} for k, v in DICT_TYPES.items()]}


@router.get("/all")
def list_all(db: Session = Depends(get_db)):
    """一次性返回全部分类（前端用于填充各下拉框）"""
    grouped = crud.get_dicts_grouped(db)
    # 保证每个已知分类都有 key，哪怕为空
    for t in DICT_TYPES:
        grouped.setdefault(t, [])
    data = {
        t: [schemas.DictionaryOut.model_validate(x).model_dump() for x in items]
        for t, items in grouped.items()
    }
    return {"code": 0, "data": data}


@router.get("/{dict_type}")
def list_by_type(dict_type: str, db: Session = Depends(get_db)):
    if dict_type not in DICT_TYPES:
        raise HTTPException(status_code=400, detail="未知字典类型")
    items = crud.get_dicts_by_type(db, dict_type)
    return {
        "code": 0,
        "data": [schemas.DictionaryOut.model_validate(x).model_dump() for x in items],
    }


@router.post("")
def create(dict_item: schemas.DictionaryCreate, db: Session = Depends(get_db)):
    if dict_item.type not in DICT_TYPES:
        raise HTTPException(status_code=400, detail="未知字典类型")
    created = crud.create_dict(db, dict_item)
    return {
        "code": 0,
        "message": "创建成功",
        "data": schemas.DictionaryOut.model_validate(created).model_dump(),
    }


@router.put("/{dict_id}")
def update(dict_id: int, item_update: schemas.DictionaryUpdate, db: Session = Depends(get_db)):
    updated = crud.update_dict(db, dict_id, item_update)
    if not updated:
        raise HTTPException(status_code=404, detail="字典项不存在")
    return {
        "code": 0,
        "message": "更新成功",
        "data": schemas.DictionaryOut.model_validate(updated).model_dump(),
    }


@router.delete("/{dict_id}")
def delete(dict_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_dict(db, dict_id)
    if not ok:
        raise HTTPException(status_code=404, detail="字典项不存在")
    return {"code": 0, "message": "删除成功"}
