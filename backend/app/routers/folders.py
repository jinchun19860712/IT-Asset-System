"""文件夹路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/folders", tags=["文件夹管理"])


@router.post("", response_model=schemas.FolderOut)
def create_folder(folder: schemas.FolderCreate, db: Session = Depends(get_db)):
    out = crud.create_folder(db, folder)
    crud.invalidate_folder_cache()
    return out


@router.get("/tree")
def get_folder_tree(kind: str = None, db: Session = Depends(get_db)):
    """获取完整的文件夹树；kind=org|asset 时只返回对应种类的树。"""
    folders = crud.get_folder_tree(db, kind)
    return {"code": 0, "data": folders}


@router.post("/rebuild-paths")
def rebuild_paths(db: Session = Depends(get_db)):
    """重建全部文件夹的 path 字段。

    历史数据由 init_db.py 直接写库，未经过 crud.create_folder，
    导致 path 为空串，进而使"按文件夹筛选子孙设备"失效。
    """
    fixed = crud.rebuild_all_folder_paths(db)
    return {"code": 0, "message": f"已修复 {fixed} 个文件夹路径", "data": {"fixed": fixed}}


@router.get("/{folder_id}/descendants")
def list_descendants(folder_id: int, db: Session = Depends(get_db)):
    """获取该文件夹及其所有子孙文件夹ID"""
    ids = crud.get_folder_descendants(db, folder_id)
    return {"code": 0, "data": ids}


@router.get("", response_model=List[schemas.FolderOut])
def list_folders(parent_id: int = None, kind: str = None, db: Session = Depends(get_db)):
    return crud.get_folders(db, parent_id, kind)


@router.get("/{folder_id}", response_model=schemas.FolderOut)
def get_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = crud.get_folder(db, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return folder


@router.put("/{folder_id}", response_model=schemas.FolderOut)
def update_folder(folder_id: int, folder: schemas.FolderUpdate, db: Session = Depends(get_db)):
    updated = crud.update_folder(db, folder_id, folder)
    crud.invalidate_folder_cache()
    if not updated:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return updated


@router.delete("/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    success = crud.delete_folder(db, folder_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    crud.invalidate_folder_cache()
    return {"code": 0, "message": "删除成功"}
