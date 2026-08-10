"""设备路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas, models
from app.utils.secret_box import secret_box

# B3 - 加密字段（B1 后被设计为存密文，接口默认遮蔽）
_SENSITIVE_FIELDS = ('mgmt_password', 'snmp_community', 'snmp_v3_auth_key', 'snmp_v3_priv_key')

router = APIRouter(prefix="/devices", tags=["设备管理"])


def _build_port_dict(p) -> dict:
    return {
        "id": p.id,
        "device_id": p.device_id,
        "port_name": p.port_name,
        "port_type": p.port_type,
        "connection_type": p.connection_type,
        "peer_device_id": p.peer_device_id,
        "peer_device_name": p.peer_device.name if p.peer_device else None,
        "peer_port_name": p.peer_port_name,
        "lag_group": p.lag_group,
        "lag_mode": p.lag_mode,
        "stack_id": p.stack_id,
        "vlan_info": p.vlan_info,
        "port_speed": p.port_speed,
        "description": p.description,
        "sort_order": p.sort_order,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _render_sensitive(value: str, unmask: bool) -> str:
    """B3 敏感字段渲染：默认 ****** 遮蔽；前端显式 unmask=1 时返回明文（已解密）。"""
    if not value:
        return ""
    if unmask:
        return secret_box.decrypt(value)
    return secret_box.mask(value)


def _build_device_dict(item, db: Session, folder_path_cache: dict = None, unmask: bool = False) -> dict:
    """构建统一的设备响应字典，包含 folder_full_path"""
    if item.folder_id:
        if folder_path_cache is not None:
            if item.folder_id not in folder_path_cache:
                folder_path_cache[item.folder_id] = crud.get_folder_full_path(db, item.folder_id)
            folder_full_path = folder_path_cache[item.folder_id]
        else:
            folder_full_path = crud.get_folder_full_path(db, item.folder_id)
    else:
        folder_full_path = ""
    return {
        "id": item.id,
        "name": item.name,
        "device_type": item.device_type,
        "product_type_id": item.product_type_id,
        "product_type_name": item.product_type.name if item.product_type else None,
        "brand": item.brand,
        "supplier": item.supplier,
        "model": item.model,
        "parent_device_id": item.parent_device_id,
        "parent_device_name": item.parent_device.name if item.parent_device else None,
        "ip_address": item.ip_address,
        "network_mask": item.network_mask,
        "mac_address": item.mac_address,
        "management_vlan": item.management_vlan,
        "area": item.area,
        "room_type": item.room_type,
        "room_number": item.room_number,
        "service_code": item.service_code,
        "status_id": item.status_id,
        "status_name": item.status.name if item.status else None,
        "status_color": item.status.color if item.status else None,
        "disuse_date": item.disuse_date,
        "department": item.department,
        "user": item.user,
        "support_ssh2": item.support_ssh2,
        "support_telnet": item.support_telnet,
        "support_web": item.support_web,
        "support_snmp": item.support_snmp,
        "support_rdp": item.support_rdp,
        "support_console": item.support_console,
        "management_services": item.management_services,
        "bmc_ip": item.bmc_ip,
        "bmc_mac": item.bmc_mac,
        "mgmt_username": item.mgmt_username,
        "mgmt_password": _render_sensitive(item.mgmt_password, unmask),
        "rack_id": item.rack_id,
        "rack_name": item.rack.name if item.rack else None,
        "rack_position": item.rack_position,
        "rack_units": item.rack_units,
        "rack_face": item.rack_face,
        "folder_id": item.folder_id,
        "folder_name": item.folder.name if item.folder else None,
        "folder_full_path": folder_full_path,
        "asset_folder_id": item.asset_folder_id,
        "asset_folder_name": item.asset_folder.name if item.asset_folder else None,
        "description": item.description,
        "remark": item.remark,
        "snmp_template_name": item.snmp_template_name,
        "snmp_selected_metrics": item.snmp_selected_metrics,
        "port_count": item.port_count,
        "port_types": item.port_types or [],
        "port_count_by_type": item.port_count_by_type or {},
        # SNMP 连接参数（真实采集）
        "snmp_version": item.snmp_version,
        "snmp_port": item.snmp_port,
        "snmp_community": _render_sensitive(item.snmp_community, unmask),
        "snmp_v3_user": item.snmp_v3_user,
        "snmp_v3_auth_protocol": item.snmp_v3_auth_protocol,
        "snmp_v3_auth_key": _render_sensitive(item.snmp_v3_auth_key, unmask),
        "snmp_v3_priv_protocol": item.snmp_v3_priv_protocol,
        "snmp_v3_priv_key": _render_sensitive(item.snmp_v3_priv_key, unmask),
        "snmp_last_poll_at": item.snmp_last_poll_at,
        "snmp_last_error": item.snmp_last_error,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "custom_values": [
            {
                "id": cv.id,
                "field_id": cv.field_id,
                "value": cv.value,
                "field_name": cv.field.name if cv.field else None,
                "field_type": cv.field.field_type if cv.field else None
            }
            for cv in item.custom_values
        ],
        "ports": [_build_port_dict(p) for p in sorted(
            item.ports, key=lambda x: (x.sort_order or 0, x.id)
        )] if item.ports else []
    }


@router.get("/all")
def list_all_devices(limit: int = 500, keyword: str = "", db: Session = Depends(get_db)):
    """获取所有设备（用于父设备选择）。limit 上限 1000 防止性能爆炸。"""
    limit = max(1, min(int(limit or 500), 1000))
    q = db.query(models.Device)
    if keyword:
        like = f"%{keyword}%"
        from sqlalchemy import or_
        q = q.filter(or_(models.Device.name.like(like), models.Device.ip_address.like(like)))
    items = q.order_by(models.Device.id.desc()).limit(limit).all()
    total = q.count()
    return {"code": 0, "data": [{"id": d.id, "name": d.name, "device_type": d.device_type} for d in items],
            "truncated": total > limit, "total": total}


@router.post("")
def create_device(unmask: int = 0, device: schemas.DeviceCreate = None, db: Session = Depends(get_db)):
    # B3 写入前：把 4 个敏感字段统一加密成 enc:<b64>
    for f in _SENSITIVE_FIELDS:
        v = getattr(device, f, None)
        if v:
            setattr(device, f, secret_box.maybe_encrypt(v))
    created = crud.create_device(db, device)
    full = crud.get_device(db, created.id)
    return {"code": 0, "message": "创建成功", "data": _build_device_dict(full, db, unmask=bool(unmask))}


@router.get("", response_model=dict)
def list_devices(
    unmask: int = 0,
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    folder_id: int = None,
    asset_folder_id: int = None,
    device_type: str = None,
    department: str = None,
    user: str = None,
    status_id: int = None,
    sort_field: str = "created_at",
    sort_order: str = "desc",
    scope: str = None,
    db: Session = Depends(get_db)
):
    params = schemas.DeviceListParams(
        page=page, page_size=page_size, keyword=keyword,
        folder_id=folder_id, asset_folder_id=asset_folder_id, device_type=device_type,
        department=department, user=user, status_id=status_id,
        sort_field=sort_field, sort_order=sort_order, scope=scope
    )
    items, total = crud.get_devices(db, params)
    path_cache = {}
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_build_device_dict(item, db, path_cache, unmask=bool(unmask)) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }


# ========== 批量操作（须注册在 /{device_id} 之前，避免路径被吞） ==========
@router.post("/bulk-delete", response_model=dict)
def bulk_delete_devices(payload: schemas.BulkIds, db: Session = Depends(get_db)):
    """批量删除设备"""
    result = crud.bulk_delete_devices(db, payload.ids)
    msg = f"已删除 {result['deleted']} 台设备"
    if result["not_found"]:
        msg += f"，{len(result['not_found'])} 台未找到"
    if result["detached_children"]:
        msg += f"，{result['detached_children']} 台子设备已解除关联"
    return {"code": 0, "message": msg, "data": result}


@router.post("/bulk-update", response_model=dict)
def bulk_update_devices(payload: schemas.DeviceBulkUpdate, db: Session = Depends(get_db)):
    """批量修改设备（只更新显式传入的字段）"""
    result = crud.bulk_update_devices(db, payload)
    if not result["fields"]:
        return {"code": 1, "message": "未指定要修改的字段", "data": result}
    return {"code": 0, "message": f"已更新 {result['updated']} 台设备", "data": result}


@router.get("/{device_id}", response_model=dict)
def get_device(device_id: int, unmask: int = 0, db: Session = Depends(get_db)):
    item = crud.get_device(db, device_id)
    if not item:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"code": 0, "message": "success", "data": _build_device_dict(item, db, unmask=bool(unmask))}


@router.put("/{device_id}")
def update_device(device_id: int, device: schemas.DeviceUpdate, unmask: int = 0, db: Session = Depends(get_db)):
    # B3 写入前：加密 4 个敏感字段
    for f in _SENSITIVE_FIELDS:
        v = getattr(device, f, None)
        if v:
            setattr(device, f, secret_box.maybe_encrypt(v))
    updated = crud.update_device(db, device_id, device)
    if not updated:
        raise HTTPException(status_code=404, detail="设备不存在")
    full = crud.get_device(db, device_id)
    return {"code": 0, "message": "更新成功", "data": _build_device_dict(full, db, unmask=bool(unmask))}


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    success = crud.delete_device(db, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"code": 0, "message": "删除成功"}


@router.get("/types/list", response_model=dict)
def list_device_types(db: Session = Depends(get_db)):
    """获取所有设备类型（去重）"""
    from app.models import Device
    types = db.query(Device.device_type).distinct().all()
    type_list = [t[0] for t in types if t[0]]
    return {"code": 0, "data": type_list}


@router.get("/departments/list", response_model=dict)
def list_departments(db: Session = Depends(get_db)):
    """获取所有部门（去重）"""
    from app.models import Device
    depts = db.query(Device.department).distinct().all()
    dept_list = [d[0] for d in depts if d[0]]
    return {"code": 0, "data": dept_list}


# ========== 端口管理 ==========
@router.get("/{device_id}/ports")
def list_ports(device_id: int, db: Session = Depends(get_db)):
    """获取设备端口列表"""
    ports = crud.get_ports(db, device_id)
    result = []
    for p in ports:
        peer_name = p.peer_device.name if p.peer_device else None
        result.append({
            "id": p.id,
            "device_id": p.device_id,
            "port_name": p.port_name,
            "port_type": p.port_type,
            "connection_type": p.connection_type,
            "peer_device_id": p.peer_device_id,
            "peer_device_name": peer_name,
            "peer_port_name": p.peer_port_name,
            "lag_group": p.lag_group,
            "description": p.description,
            "created_at": p.created_at,
            "updated_at": p.updated_at
        })
    return {"code": 0, "data": result}


@router.post("/{device_id}/ports")
def create_port(device_id: int, port: schemas.DevicePortCreate, db: Session = Depends(get_db)):
    """添加端口"""
    db_port = crud.create_port(db, port, device_id)
    return {"code": 0, "data": db_port.id}


@router.put("/{device_id}/ports/{port_id}")
def update_port(port_id: int, port: schemas.DevicePortBase, db: Session = Depends(get_db)):
    """更新端口"""
    updated = crud.update_port(db, port_id, port)
    if not updated:
        raise HTTPException(status_code=404, detail="端口不存在")
    return {"code": 0, "message": "更新成功"}


@router.delete("/{device_id}/ports/{port_id}")
def delete_port(port_id: int, db: Session = Depends(get_db)):
    """删除端口"""
    success = crud.delete_port(db, port_id)
    if not success:
        raise HTTPException(status_code=404, detail="端口不存在")
    return {"code": 0, "message": "删除成功"}
