"""机柜管理与网络拓扑路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas, models

router = APIRouter(prefix="/racks", tags=["机柜管理"])


def _rack_dict(rack, db: Session) -> dict:
    devices = crud.get_rack_devices(db, rack.id)
    used = sum((d.rack_units or 1) for d in devices if d.rack_position)
    return {
        "id": rack.id,
        "name": rack.name,
        "u_height": rack.u_height,
        "location": rack.location,
        "row_label": rack.row_label,
        "folder_id": rack.folder_id,
        "folder_full_path": crud.get_folder_full_path(db, rack.folder_id) if rack.folder_id else "",
        "description": rack.description,
        "sort_order": rack.sort_order,
        "device_count": len(devices),
        "used_units": used,
        "created_at": rack.created_at,
        "updated_at": rack.updated_at,
    }


@router.get("")
def list_racks(folder_id: int = None, db: Session = Depends(get_db)):
    """机柜列表（可按文件夹过滤，含子孙文件夹）"""
    racks = crud.get_racks(db, folder_id)
    return {"code": 0, "data": [_rack_dict(r, db) for r in racks]}


@router.post("")
def create_rack(rack: schemas.RackCreate, db: Session = Depends(get_db)):
    created = crud.create_rack(db, rack)
    return {"code": 0, "message": "创建成功", "data": _rack_dict(created, db)}


@router.put("/{rack_id}")
def update_rack(rack_id: int, rack: schemas.RackUpdate, db: Session = Depends(get_db)):
    updated = crud.update_rack(db, rack_id, rack)
    if not updated:
        raise HTTPException(status_code=404, detail="机柜不存在")
    return {"code": 0, "message": "更新成功", "data": _rack_dict(updated, db)}


@router.delete("/{rack_id}")
def delete_rack(rack_id: int, db: Session = Depends(get_db)):
    if not crud.delete_rack(db, rack_id):
        raise HTTPException(status_code=404, detail="机柜不存在")
    return {"code": 0, "message": "删除成功，柜内设备已自动下架"}


@router.get("/{rack_id}/layout")
def get_rack_layout(rack_id: int, db: Session = Depends(get_db)):
    """机柜正视图布局：返回机柜信息 + 已上架设备的U位占用"""
    rack = crud.get_rack(db, rack_id)
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在")

    devices = crud.get_rack_devices(db, rack_id)
    mounted = []
    for d in devices:
        if not d.rack_position:
            continue
        mounted.append({
            "device_id": d.id,
            "name": d.name,
            "device_type": d.device_type or "",
            "brand": d.brand or "",
            "model": d.model or "",
            "ip_address": d.ip_address or "",
            "status_name": d.status.name if d.status else "",
            "status_color": d.status.color if d.status else "#909399",
            "rack_position": d.rack_position,
            "rack_units": d.rack_units or 1,
            "rack_face": d.rack_face or "front",
        })

    # 计算空闲U位（前后面板分别统计）
    def free_slots(face):
        occupied = set()
        for m in mounted:
            if m["rack_face"] != face:
                continue
            for u in range(m["rack_position"], m["rack_position"] + m["rack_units"]):
                occupied.add(u)
        return [u for u in range(1, rack.u_height + 1) if u not in occupied]

    return {"code": 0, "data": {
        "rack": _rack_dict(rack, db),
        "mounted": mounted,
        "free_front": free_slots("front"),
        "free_rear": free_slots("rear"),
    }}


@router.post("/{rack_id}/mount")
def mount_device(rack_id: int, req: schemas.RackMountRequest, db: Session = Depends(get_db)):
    """设备上架到指定U位"""
    ok, err = crud.mount_device(db, rack_id, req)
    if not ok:
        return {"code": 1, "message": err}
    return {"code": 0, "message": "上架成功"}


@router.post("/unmount/{device_id}")
def unmount_device(device_id: int, db: Session = Depends(get_db)):
    """设备下架"""
    if not crud.unmount_device(db, device_id):
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"code": 0, "message": "已下架"}


@router.get("/available-devices/list")
def list_available_devices(folder_id: int = None, db: Session = Depends(get_db)):
    """可上架设备列表（尚未分配机柜的设备）"""
    query = db.query(models.Device).filter(models.Device.rack_id.is_(None))
    if folder_id:
        ids = crud.get_folder_descendants(db, folder_id)
        if ids:
            query = query.filter(models.Device.folder_id.in_(ids))
    devices = query.order_by(models.Device.name).all()
    return {"code": 0, "data": [
        {"id": d.id, "name": d.name, "device_type": d.device_type or "",
         "model": d.model or "", "ip_address": d.ip_address or ""}
        for d in devices
    ]}


# ========== 拓扑 ==========
topology_router = APIRouter(prefix="/topology", tags=["网络拓扑"])


@topology_router.get("")
def get_topology(folder_id: int = None, db: Session = Depends(get_db)):
    """拓扑图数据：节点为设备，连线来自父设备层级与端口对端关系"""
    return {"code": 0, "data": crud.get_topology(db, folder_id)}
