"""产品类型路由（AssetExplorer 风格：定义类型 + 资产分类归属 + 自定义字段布局）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/product-types", tags=["产品类型"])


@router.post("", response_model=schemas.ProductTypeOut)
def create_product_type(pt: schemas.ProductTypeCreate, db: Session = Depends(get_db)):
    """创建产品类型（自动解析资产树归属节点）"""
    return crud.create_product_type(db, pt)


@router.get("")
def list_product_types(active_only: bool = False, db: Session = Depends(get_db)):
    """列出所有产品类型"""
    items = crud.get_product_types(db, active_only=active_only)
    return {
        "code": 0,
        "data": [schemas.ProductTypeOut.model_validate(p).model_dump() for p in items]
    }


@router.get("/{pt_id}", response_model=schemas.ProductTypeOut)
def get_product_type(pt_id: int, db: Session = Depends(get_db)):
    pt = crud.get_product_type(db, pt_id)
    if not pt:
        raise HTTPException(status_code=404, detail="产品类型不存在")
    return pt


@router.put("/{pt_id}", response_model=schemas.ProductTypeOut)
def update_product_type(pt_id: int, pt_update: schemas.ProductTypeUpdate, db: Session = Depends(get_db)):
    """更新产品类型"""
    updated = crud.update_product_type(db, pt_id, pt_update)
    if not updated:
        raise HTTPException(status_code=404, detail="产品类型不存在")
    return updated


@router.delete("/{pt_id}")
def delete_product_type(pt_id: int, db: Session = Depends(get_db)):
    success = crud.delete_product_type(db, pt_id)
    if not success:
        raise HTTPException(status_code=404, detail="产品类型不存在")
    return {"code": 0, "message": "删除成功"}


# ========== 布局关联 ==========

@router.get("/{pt_id}/fields")
def get_product_type_fields(pt_id: int, db: Session = Depends(get_db)):
    """获取产品类型绑定的自定义字段（含完整字段信息，按 sort_order 排序）"""
    fields = crud.get_product_type_field_details(db, pt_id)
    return {"code": 0, "data": [schemas.CustomFieldOut.model_validate(f) for f in fields]}


@router.put("/{pt_id}/fields")
def link_fields(pt_id: int, link: schemas.ProductTypeFieldLink, db: Session = Depends(get_db)):
    """批量关联自定义字段到产品类型（覆盖式，旧关联先清空）"""
    pt = crud.link_fields_to_product_type(db, pt_id, link.field_ids)
    if not pt:
        raise HTTPException(status_code=404, detail="产品类型不存在")
    return {"code": 0, "message": "关联成功", "data": {"product_type_id": pt_id, "field_ids": link.field_ids}}
