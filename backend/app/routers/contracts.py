"""合同附件管理：上传 / 列表 / 下载 / 删除。

文件保存在 backend/uploads/contracts/，仅允许 PDF / PNG / JPG。
前端通过 /api/contracts/{id}/download 经 vite 代理下载。
"""
import os
import uuid
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/contracts", tags=["合同附件"])

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_ROOT = os.path.join(BACKEND_ROOT, "uploads")
UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "contracts")
ALLOWED_EXT = {"pdf", "png", "jpg", "jpeg"}
MAX_SIZE = 20 * 1024 * 1024  # 20MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


# 文件 magic-bytes 校验：避免 ".html" 改名 ".pdf" 触发存储型 XSS / 钓鱼
# 读取前 16 字节判断真实文件类型
_MAGIC_BYTES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}


def _validate_file_magic(ext: str, content: bytes) -> bool:
    """校验文件内容头部 magic-bytes 与扩展名是否一致。"""
    sigs = _MAGIC_BYTES.get(ext, [])
    if not sigs:
        return False
    head = content[:16]
    return any(head.startswith(sig) for sig in sigs)


def _build_download_url(contract_id: int) -> str:
    return f"/api/contracts/{contract_id}/download"


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    name: str = Form(...),
    supplier_id: int = Form(None),
    supplier_name: str = Form(""),
    related_type: str = Form(""),
    related_id: int = Form(None),
    remark: str = Form(""),
    db: Session = Depends(get_db),
):
    """上传合同附件，可关联设备 / 软件与供应商。"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="合同名称不能为空")
    ext = _ext_of(file.filename or "")
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"仅支持 PDF / PNG / JPG，当前为：{ext or '未知'}")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件过大（上限 20MB）")
    if len(content) < 8:
        raise HTTPException(status_code=400, detail="文件内容过小，可能已损坏")
    # 关键校验：magic-bytes 必须匹配扩展名，防止 ".html" 改名 ".pdf" 等绕过
    if not _validate_file_magic(ext, content):
        raise HTTPException(
            status_code=400,
            detail=f"文件类型与扩展名不符（{ext}）。请确保文件为真实的 PDF / PNG / JPG"
        )

    stored = f"{uuid.uuid4().hex}.{ext}"
    abs_path = os.path.join(UPLOAD_DIR, stored)
    with open(abs_path, "wb") as f:
        f.write(content)

    try:
        c = crud.create_contract(
            db,
            name=name.strip(),
            supplier_id=supplier_id,
            supplier_name=(supplier_name or "").strip(),
            related_type=(related_type or "").strip(),
            related_id=related_id,
            file_path=f"contracts/{stored}",
            file_name=file.filename or name,
            file_type=ext,
            file_size=len(content),
            remark=(remark or "").strip(),
        )
    except Exception:
        # 写库失败则清理已落盘的文件，避免孤儿文件
        if os.path.exists(abs_path):
            os.remove(abs_path)
        raise

    out = schemas.ContractOut.model_validate(c)
    out.download_url = _build_download_url(c.id)
    return {"code": 0, "message": "上传成功", "data": out.model_dump()}


@router.get("")
def list_contracts(
    keyword: str = None,
    supplier_id: int = None,
    related_type: str = None,
    related_id: int = None,
    db: Session = Depends(get_db),
):
    rows = crud.get_contracts(
        db, keyword=keyword, supplier_id=supplier_id,
        related_type=related_type, related_id=related_id,
    )
    data = []
    for c in rows:
        o = schemas.ContractOut.model_validate(c)
        o.download_url = _build_download_url(c.id)
        data.append(o.model_dump())
    return {"code": 0, "data": data, "total": len(data)}


@router.get("/{contract_id}")
def get_one(contract_id: int, db: Session = Depends(get_db)):
    c = crud.get_contract(db, contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="合同不存在")
    o = schemas.ContractOut.model_validate(c)
    o.download_url = _build_download_url(c.id)
    return {"code": 0, "data": o.model_dump()}


@router.put("/{contract_id}")
def update_contract(contract_id: int, item: schemas.ContractUpdate, db: Session = Depends(get_db)):
    updated = crud.update_contract(db, contract_id, item)
    if not updated:
        raise HTTPException(status_code=404, detail="合同不存在")
    o = schemas.ContractOut.model_validate(updated)
    o.download_url = _build_download_url(updated.id)
    return {"code": 0, "message": "更新成功", "data": o.model_dump()}


@router.get("/{contract_id}/download")
def download_contract(contract_id: int, db: Session = Depends(get_db)):
    c = crud.get_contract(db, contract_id)
    if not c or not c.file_path:
        raise HTTPException(status_code=404, detail="合同文件不存在")
    abs_path = os.path.join(UPLOAD_ROOT, c.file_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="合同文件已丢失")
    # RFC 5987：中文文件名用 filename* 编码，兼容大多数浏览器
    ascii_name = c.file_name.encode("ascii", "ignore").decode() or "contract"
    header = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(c.file_name)}"
    return FileResponse(abs_path, media_type=_media(c.file_type), headers={"Content-Disposition": header})


@router.delete("/{contract_id}")
def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    c = crud.get_contract(db, contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="合同不存在")
    if c.file_path:
        abs_path = os.path.join(UPLOAD_ROOT, c.file_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass
    crud.delete_contract(db, contract_id)
    return {"code": 0, "message": "删除成功"}


def _media(ext: str) -> str:
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get((ext or "").lower(), "application/octet-stream")
