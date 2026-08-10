"""数据库操作层"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, asc
from typing import Optional, List
from app import models, schemas


def _parse_int_csv(s: str) -> List[int]:
    """把逗号分隔的整数字符串解析为 int 列表（用于多值筛选参数）"""
    if not s:
        return []
    out = []
    for x in s.split(','):
        x = x.strip()
        if x.lstrip('-').isdigit():
            out.append(int(x))
    return out


# ========== 文件夹操作 ==========
def create_folder(db: Session, folder: schemas.FolderCreate) -> models.Folder:
    db_folder = models.Folder(**folder.model_dump())
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    _update_folder_path(db, db_folder)
    return db_folder


def _update_folder_path(db: Session, folder: models.Folder):
    """递归更新文件夹路径"""
    if folder.parent_id:
        parent = db.query(models.Folder).filter(models.Folder.id == folder.parent_id).first()
        folder.path = f"{parent.path}{folder.id}/"
    else:
        folder.path = f"/{folder.id}/"
    db.commit()
    db.refresh(folder)
    for child in folder.children:
        _update_folder_path(db, child)


def get_folder(db: Session, folder_id: int) -> Optional[models.Folder]:
    return db.query(models.Folder).filter(models.Folder.id == folder_id).first()


def get_folders(db: Session, parent_id: Optional[int] = None, kind: Optional[str] = None) -> List[models.Folder]:
    query = db.query(models.Folder)
    if parent_id is not None:
        query = query.filter(models.Folder.parent_id == parent_id)
    else:
        query = query.filter(models.Folder.parent_id.is_(None))
    if kind:
        query = query.filter(models.Folder.kind == kind)
    return query.order_by(models.Folder.sort_order).all()


def get_folder_full_path(db: Session, folder_id: int, sep: str = "-") -> str:
    """获取文件夹完整路径名称，如：黄山健康职业学院-信息中心-电脑"""
    if not folder_id:
        return ""
    folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if not folder:
        return ""
    parts = []
    current = folder
    guard = 0
    while current and guard < 50:  # 防御父子环引用
        parts.insert(0, current.name)
        if current.parent_id:
            current = db.query(models.Folder).filter(models.Folder.id == current.parent_id).first()
        else:
            break
        guard += 1
    return sep.join(parts)


def get_folder_department(db: Session, folder_id: int) -> str:
    """向上查找最近的"部门"节点，返回部门名称。

    优先使用显式标记 is_department=True 的节点；
    若整条链上都没有标记，则回退到"根节点的直接子节点"（即二级目录）。
    """
    if not folder_id:
        return ""
    chain = []
    current = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    guard = 0
    while current and guard < 50:
        chain.insert(0, current)  # chain[0] 为最顶层
        if not current.parent_id:
            break
        current = db.query(models.Folder).filter(models.Folder.id == current.parent_id).first()
        guard += 1

    # 从最近的祖先往上找显式标记
    for node in reversed(chain):
        if node.is_department:
            return node.department_name or node.name

    # 回退：二级目录视为部门
    if len(chain) >= 2:
        return chain[1].name
    return ""


# 进程级缓存：(id, parent_id) 关系树。文件夹增删改时调 invalidate_folder_cache() 失效。
_folder_cache = {"built_at": 0, "children_map": None}
_FOLDER_CACHE_TTL = 30  # 秒


def invalidate_folder_cache():
    """文件夹增删改后调用，清缓存重建。"""
    _folder_cache["children_map"] = None
    _folder_cache["built_at"] = 0


def _build_folder_cache(db: Session):
    """一次性载入所有文件夹 (id, parent_id)，构建子节点索引。TTL 30 秒自动重建。"""
    import time
    now = time.time()
    if _folder_cache["children_map"] is not None and now - _folder_cache["built_at"] < _FOLDER_CACHE_TTL:
        return _folder_cache["children_map"]
    rows = db.query(models.Folder.id, models.Folder.parent_id).all()
    children_map = {}
    for fid, pid in rows:
        children_map.setdefault(pid, []).append(fid)
    _folder_cache["children_map"] = children_map
    _folder_cache["built_at"] = now
    return children_map


def get_folder_descendants(db: Session, folder_id: int) -> List[int]:
    """获取某文件夹的所有子孙文件夹ID（包含自身）。

    基于 parent_id 做广度优先遍历。带 30 秒缓存，避免每次列表查询都全表扫一次。
    """
    if not folder_id:
        return []
    children_map = _build_folder_cache(db)
    if folder_id not in children_map and folder_id not in _collect_parents(children_map):
        # 文件夹可能不在缓存里（极少见，因为都是 id→[ids]）
        return [folder_id]

    result = []
    queue = [folder_id]
    seen = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        result.append(current)
        queue.extend(children_map.get(current, []))
    return result


def _collect_parents(children_map: dict) -> set:
    """从 children_map 反推所有出现过的 id（包括作为父节点的）。"""
    all_ids = set()
    for pid, kids in children_map.items():
        if pid is not None:
            all_ids.add(pid)
        all_ids.update(kids)
    return all_ids


def rebuild_all_folder_paths(db: Session) -> int:
    """重建全部文件夹的 path 字段，返回修复条数。"""
    rows = db.query(models.Folder).all()
    by_id = {f.id: f for f in rows}
    fixed = 0

    def resolve(folder, depth=0):
        if depth > 50:
            return ""
        if folder.parent_id and folder.parent_id in by_id:
            parent_path = resolve(by_id[folder.parent_id], depth + 1)
            return f"{parent_path}{folder.id}/"
        return f"/{folder.id}/"

    for f in rows:
        correct = resolve(f)
        if f.path != correct:
            f.path = correct
            fixed += 1
    if fixed:
        db.commit()
    return fixed


def get_folder_tree(db: Session, kind: Optional[str] = None) -> List[dict]:
    """获取完整的文件夹树（含全路径与推导出的部门名）。

    kind 不为空时只返回该种类的树（'org'=组织机构 / 'asset'=设备资产），
    两套树互不干扰，左侧导航可在它们之间切换。
    """
    q = db.query(models.Folder)
    if kind:
        q = q.filter(models.Folder.kind == kind)
    all_folders = q.order_by(models.Folder.sort_order).all()
    folder_map = {}
    for f in all_folders:
        folder_map[f.id] = {
            "id": f.id,
            "name": f.name,
            "parent_id": f.parent_id,
            "path": f.path,
            "sort_order": f.sort_order,
            "is_department": bool(f.is_department),
            "department_name": f.department_name or "",
            "full_path": "",
            "effective_department": "",
            "level": 0,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
            "children": []
        }
    roots = []
    for f in all_folders:
        node = folder_map[f.id]
        if f.parent_id and f.parent_id in folder_map:
            folder_map[f.parent_id]["children"].append(node)
        else:
            roots.append(node)

    # 一次性下推计算 full_path / 部门归属，避免逐节点回溯查询
    def decorate(node, prefix, inherited_dept, level):
        node["level"] = level
        node["full_path"] = f"{prefix}-{node['name']}" if prefix else node["name"]
        if node["is_department"]:
            dept = node["department_name"] or node["name"]
        elif inherited_dept:
            dept = inherited_dept
        elif level == 1:
            dept = node["name"]   # 回退：二级目录视为部门
        else:
            dept = ""
        node["effective_department"] = dept
        for child in node["children"]:
            decorate(child, node["full_path"], dept, level + 1)

    for root in roots:
        decorate(root, "", "", 0)
    return roots


def update_folder(db: Session, folder_id: int, folder_update: schemas.FolderUpdate) -> Optional[models.Folder]:
    db_folder = get_folder(db, folder_id)
    if not db_folder:
        return None
    update_data = folder_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_folder, field, value)
    db.commit()
    db.refresh(db_folder)
    if "parent_id" in update_data:
        _update_folder_path(db, db_folder)
    return db_folder


def delete_folder(db: Session, folder_id: int) -> bool:
    db_folder = get_folder(db, folder_id)
    if not db_folder:
        return False
    for child in list(db_folder.children):
        delete_folder(db, child.id)
    db.delete(db_folder)
    db.commit()
    return True


# ========== 设备状态操作 ==========
def create_status(db: Session, status: schemas.DeviceStatusCreate) -> models.DeviceStatus:
    db_status = models.DeviceStatus(**status.model_dump())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status


def get_statuses(db: Session) -> List[models.DeviceStatus]:
    return db.query(models.DeviceStatus).order_by(models.DeviceStatus.sort_order).all()


def get_status(db: Session, status_id: int) -> Optional[models.DeviceStatus]:
    return db.query(models.DeviceStatus).filter(models.DeviceStatus.id == status_id).first()


def update_status(db: Session, status_id: int, status_update: schemas.DeviceStatusBase) -> Optional[models.DeviceStatus]:
    db_status = get_status(db, status_id)
    if not db_status:
        return None
    for field, value in status_update.model_dump().items():
        setattr(db_status, field, value)
    db.commit()
    db.refresh(db_status)
    return db_status


def delete_status(db: Session, status_id: int) -> bool:
    db_status = get_status(db, status_id)
    if not db_status:
        return False
    db.delete(db_status)
    db.commit()
    return True


# ========== 自定义字段操作 ==========
# (新版定义在文件末尾，含 11 种字段类型 + 布局 + active_only 过滤)


# ========== 设备操作 ==========
def create_device(db: Session, device: schemas.DeviceCreate) -> models.Device:
    device_data = device.model_dump(exclude={"custom_values", "ports"})

    # 未显式填写部门时，按所在文件夹自动推导
    if not device_data.get("department") and device_data.get("folder_id"):
        device_data["department"] = get_folder_department(db, device_data["folder_id"])

    # 产品类型 → 自动推导资产分类
    if device_data.get("product_type_id") and not device_data.get("asset_folder_id"):
        pt = db.query(models.ProductType).filter(
            models.ProductType.id == device_data["product_type_id"]
        ).first()
        if pt and pt.asset_folder_id:
            device_data["asset_folder_id"] = pt.asset_folder_id

    # 自动汇总 port_count_by_type 到 port_count（按类型细分时保证总数正确）
    pcbt = device_data.get("port_count_by_type") or {}
    if pcbt:
        try:
            device_data["port_count"] = sum(int(v) for v in pcbt.values() if v is not None)
        except (TypeError, ValueError):
            pass
    # 保证 port_count_by_type 是 dict
    if not isinstance(device_data.get("port_count_by_type"), dict):
        device_data["port_count_by_type"] = {}

    db_device = models.Device(**device_data)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)

    for cv in device.custom_values:
        db_cv = models.DeviceCustomValue(
            device_id=db_device.id,
            field_id=cv.field_id,
            value=cv.value
        )
        db.add(db_cv)

    for idx, p in enumerate(device.ports or []):
        port_data = p.model_dump()
        port_data["sort_order"] = port_data.get("sort_order") or idx
        db.add(models.DevicePort(device_id=db_device.id, **port_data))

    db.commit()
    db.refresh(db_device)
    return db_device


def get_device(db: Session, device_id: int) -> Optional[models.Device]:
    return db.query(models.Device).options(
        joinedload(models.Device.status),
        joinedload(models.Device.folder),
        joinedload(models.Device.parent_device),
        joinedload(models.Device.rack),
        joinedload(models.Device.product_type),
        joinedload(models.Device.custom_values).joinedload(models.DeviceCustomValue.field),
        joinedload(models.Device.ports).joinedload(models.DevicePort.peer_device)
    ).filter(models.Device.id == device_id).first()


def get_devices(db: Session, params: schemas.DeviceListParams) -> tuple:
    query = db.query(models.Device).options(
        joinedload(models.Device.status),
        joinedload(models.Device.folder),
        joinedload(models.Device.parent_device),
        joinedload(models.Device.rack),
        joinedload(models.Device.product_type),
        joinedload(models.Device.ports).joinedload(models.DevicePort.peer_device)
    )

    # 文件夹筛选（包含所有子文件夹）—— 支持多值：comma-sep 拼接 ids
    folder_ids = _parse_int_csv(params.folder_ids) if params.folder_ids else []
    if folder_ids:
        all_ids = set()
        for fid in folder_ids:
            for d in get_folder_descendants(db, fid):
                all_ids.add(d)
        if all_ids:
            query = query.filter(models.Device.folder_id.in_(all_ids))
    elif params.folder_id:
        descendant_ids = get_folder_descendants(db, params.folder_id)
        if descendant_ids:
            query = query.filter(models.Device.folder_id.in_(descendant_ids))

    # 设备资产分类筛选（资产树，包含所有子文件夹）—— 支持多值
    asset_ids_csv = _parse_int_csv(params.asset_folder_ids) if params.asset_folder_ids else []
    if asset_ids_csv:
        all_ids = set()
        for fid in asset_ids_csv:
            for d in get_folder_descendants(db, fid):
                all_ids.add(d)
        if all_ids:
            query = query.filter(models.Device.asset_folder_id.in_(all_ids))
    elif params.asset_folder_id:
        asset_ids = get_folder_descendants(db, params.asset_folder_id)
        if asset_ids:
            query = query.filter(models.Device.asset_folder_id.in_(asset_ids))

    # 关键词搜索
    if params.keyword:
        keyword_filter = or_(
            models.Device.name.contains(params.keyword),
            models.Device.mac_address.contains(params.keyword),
            models.Device.ip_address.contains(params.keyword),
            models.Device.department.contains(params.keyword),
            models.Device.user.contains(params.keyword)
        )
        query = query.filter(keyword_filter)

    if params.device_type:
        query = query.filter(models.Device.device_type == params.device_type)
    # 多值 device_types
    if params.device_types:
        types = [t.strip() for t in params.device_types.split(',') if t.strip()]
        if types:
            query = query.filter(models.Device.device_type.in_(types))
    # 多值 suppliers
    if params.suppliers:
        sups = [s.strip() for s in params.suppliers.split(',') if s.strip()]
        if sups:
            query = query.filter(models.Device.supplier.in_(sups))
    if params.department:
        query = query.filter(models.Device.department == params.department)
    if params.user:
        query = query.filter(models.Device.user == params.user)
    if params.status_id:
        query = query.filter(models.Device.status_id == params.status_id)

    # 面板默认范围过滤（配合前端组织架构/资产面板）
    if params.scope == 'asset_default':
        # 资产面板默认：有资产分类 或 无部门
        query = query.filter(
            or_(
                models.Device.asset_folder_id.isnot(None),
                models.Device.department == '',
                models.Device.department.is_(None)
            )
        )
    elif params.scope == 'org_default':
        # 组织架构默认：有部门 或 已归属组织机构
        query = query.filter(
            or_(
                models.Device.folder_id.isnot(None),
                and_(models.Device.department != '', models.Device.department.isnot(None))
            )
        )

    # 排序
    sort_column = getattr(models.Device, params.sort_field or "created_at", models.Device.created_at)
    if params.sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # joinedload 一对多会放大行数，用 distinct 保证分页计数正确
    total = query.distinct().count()
    offset = (params.page - 1) * params.page_size
    items = query.distinct().offset(offset).limit(params.page_size).all()
    return items, total


def update_device(db: Session, device_id: int, device_update: schemas.DeviceUpdate) -> Optional[models.Device]:
    db_device = get_device(db, device_id)
    if not db_device:
        return None

    update_data = device_update.model_dump(exclude={"custom_values", "ports"}, exclude_unset=True)

    # 自动汇总 port_count_by_type 到 port_count
    if "port_count_by_type" in update_data:
        pcbt = update_data.get("port_count_by_type") or {}
        if isinstance(pcbt, dict):
            try:
                update_data["port_count"] = sum(int(v) for v in pcbt.values() if v is not None)
            except (TypeError, ValueError):
                pass

    # 允许显式清空：机柜位置（下架）、资产分类（取消归类）
    nullable_fields = {
        "rack_id", "rack_position", "parent_device_id", "status_id", "asset_folder_id"
    }
    for field, value in update_data.items():
        if value is not None or field in nullable_fields:
            setattr(db_device, field, value)

    if device_update.custom_values:
        db.query(models.DeviceCustomValue).filter(
            models.DeviceCustomValue.device_id == device_id
        ).delete()
        for cv in device_update.custom_values:
            db_cv = models.DeviceCustomValue(
                device_id=device_id,
                field_id=cv.field_id,
                value=cv.value
            )
            db.add(db_cv)

    # ports 为 None 表示"本次不改动端口"；为 [] 表示"清空端口"
    if device_update.ports is not None:
        db.query(models.DevicePort).filter(
            models.DevicePort.device_id == device_id
        ).delete()
        for idx, p in enumerate(device_update.ports):
            port_data = p.model_dump()
            port_data["sort_order"] = port_data.get("sort_order") or idx
            db.add(models.DevicePort(device_id=device_id, **port_data))

    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(db: Session, device_id: int) -> bool:
    db_device = get_device(db, device_id)
    if not db_device:
        return False
    db.delete(db_device)
    db.commit()
    return True


# ========== 批量操作 ==========
def bulk_delete_devices(db: Session, ids: List[int]) -> dict:
    """批量删除设备，返回 {deleted, not_found, detached_children}"""
    devices = db.query(models.Device).filter(models.Device.id.in_(ids)).all()
    found_ids = {d.id for d in devices}
    not_found = [i for i in ids if i not in found_ids]

    # 被删设备的子设备解除父子关系，避免外键悬挂
    detached = db.query(models.Device).filter(
        models.Device.parent_device_id.in_(found_ids),
        ~models.Device.id.in_(found_ids),
    ).update({models.Device.parent_device_id: None}, synchronize_session=False) if found_ids else 0

    # 关联的 SNMP 值一并清理
    if found_ids:
        db.query(models.SnmpMetricValue).filter(
            models.SnmpMetricValue.device_id.in_(found_ids)
        ).delete(synchronize_session=False)

    for d in devices:
        db.delete(d)
    db.commit()
    return {"deleted": len(devices), "not_found": not_found, "detached_children": detached or 0}


def bulk_update_devices(db: Session, payload: schemas.DeviceBulkUpdate) -> dict:
    """批量修改设备：只写入显式传入的字段"""
    data = payload.model_dump(exclude={"ids"}, exclude_unset=True)
    data = {k: v for k, v in data.items() if v is not None}
    if not data:
        return {"updated": 0, "fields": [], "not_found": []}

    devices = db.query(models.Device).filter(models.Device.id.in_(payload.ids)).all()
    found_ids = {d.id for d in devices}
    not_found = [i for i in payload.ids if i not in found_ids]

    for d in devices:
        for field, value in data.items():
            setattr(d, field, value)
    db.commit()
    return {"updated": len(devices), "fields": list(data.keys()), "not_found": not_found}


def bulk_delete_softwares(db: Session, ids: List[int]) -> dict:
    items = db.query(models.Software).filter(models.Software.id.in_(ids)).all()
    found_ids = {s.id for s in items}
    for s in items:
        db.delete(s)
    db.commit()
    return {"deleted": len(items), "not_found": [i for i in ids if i not in found_ids]}


def bulk_update_softwares(db: Session, payload: schemas.SoftwareBulkUpdate) -> dict:
    data = payload.model_dump(exclude={"ids"}, exclude_unset=True)
    data = {k: v for k, v in data.items() if v is not None}
    if not data:
        return {"updated": 0, "fields": [], "not_found": []}

    items = db.query(models.Software).filter(models.Software.id.in_(payload.ids)).all()
    found_ids = {s.id for s in items}
    for s in items:
        for field, value in data.items():
            setattr(s, field, value)
    db.commit()
    return {"updated": len(items), "fields": list(data.keys()),
            "not_found": [i for i in payload.ids if i not in found_ids]}


# ========== 端口操作 ==========
def create_port(db: Session, port: schemas.DevicePortCreate, device_id: int) -> models.DevicePort:
    db_port = models.DevicePort(**port.model_dump(), device_id=device_id)
    db.add(db_port)
    db.commit()
    db.refresh(db_port)
    return db_port


def get_ports(db: Session, device_id: int) -> List[models.DevicePort]:
    return db.query(models.DevicePort).filter(models.DevicePort.device_id == device_id).all()


def update_port(db: Session, port_id: int, port_update: schemas.DevicePortBase) -> Optional[models.DevicePort]:
    db_port = db.query(models.DevicePort).filter(models.DevicePort.id == port_id).first()
    if not db_port:
        return None
    for field, value in port_update.model_dump(exclude_unset=True).items():
        setattr(db_port, field, value)
    db.commit()
    db.refresh(db_port)
    return db_port


def delete_port(db: Session, port_id: int) -> bool:
    db_port = db.query(models.DevicePort).filter(models.DevicePort.id == port_id).first()
    if not db_port:
        return False
    db.delete(db_port)
    db.commit()
    return True


# ========== 机柜操作 ==========
def create_rack(db: Session, rack: schemas.RackCreate) -> models.Rack:
    db_rack = models.Rack(**rack.model_dump())
    db.add(db_rack)
    db.commit()
    db.refresh(db_rack)
    return db_rack


def get_rack(db: Session, rack_id: int) -> Optional[models.Rack]:
    return db.query(models.Rack).filter(models.Rack.id == rack_id).first()


def get_racks(db: Session, folder_id: Optional[int] = None) -> List[models.Rack]:
    query = db.query(models.Rack)
    if folder_id:
        descendant_ids = get_folder_descendants(db, folder_id)
        if descendant_ids:
            query = query.filter(models.Rack.folder_id.in_(descendant_ids))
    return query.order_by(models.Rack.sort_order, models.Rack.id).all()


def update_rack(db: Session, rack_id: int, rack_update: schemas.RackUpdate) -> Optional[models.Rack]:
    db_rack = get_rack(db, rack_id)
    if not db_rack:
        return None
    for field, value in rack_update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_rack, field, value)
    db.commit()
    db.refresh(db_rack)
    return db_rack


def delete_rack(db: Session, rack_id: int) -> bool:
    db_rack = get_rack(db, rack_id)
    if not db_rack:
        return False
    # 先把柜内设备下架，避免留下悬空引用
    db.query(models.Device).filter(models.Device.rack_id == rack_id).update(
        {"rack_id": None, "rack_position": None}, synchronize_session=False
    )
    db.delete(db_rack)
    db.commit()
    return True


def get_rack_devices(db: Session, rack_id: int) -> List[models.Device]:
    return db.query(models.Device).options(
        joinedload(models.Device.status)
    ).filter(models.Device.rack_id == rack_id).order_by(models.Device.rack_position).all()


def check_rack_conflict(db: Session, rack_id: int, position: int, units: int,
                        face: str, exclude_device_id: Optional[int] = None) -> Optional[str]:
    """检查目标U位区间是否与柜内已有设备冲突，冲突则返回提示文本。"""
    rack = get_rack(db, rack_id)
    if not rack:
        return "机柜不存在"
    if position < 1 or position + units - 1 > rack.u_height:
        return f"U位超出范围（该机柜共 {rack.u_height}U）"

    new_start, new_end = position, position + units - 1
    query = db.query(models.Device).filter(
        models.Device.rack_id == rack_id,
        models.Device.rack_position.isnot(None)
    )
    if exclude_device_id:
        query = query.filter(models.Device.id != exclude_device_id)

    for d in query.all():
        # 只有同一朝向才算冲突（前后面板可各放一台）
        if (d.rack_face or "front") != face:
            continue
        d_start = d.rack_position
        d_end = d_start + (d.rack_units or 1) - 1
        if new_start <= d_end and d_start <= new_end:
            return f"U位冲突：{d.name} 已占用 U{d_start}-U{d_end}"
    return None


def mount_device(db: Session, rack_id: int, req: schemas.RackMountRequest) -> tuple:
    """设备上架，返回 (成功?, 错误信息)"""
    device = db.query(models.Device).filter(models.Device.id == req.device_id).first()
    if not device:
        return False, "设备不存在"
    conflict = check_rack_conflict(db, rack_id, req.rack_position, req.rack_units,
                                   req.rack_face, exclude_device_id=req.device_id)
    if conflict:
        return False, conflict
    device.rack_id = rack_id
    device.rack_position = req.rack_position
    device.rack_units = req.rack_units
    device.rack_face = req.rack_face
    db.commit()
    return True, ""


def unmount_device(db: Session, device_id: int) -> bool:
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        return False
    device.rack_id = None
    device.rack_position = None
    db.commit()
    return True


# ========== 拓扑数据 ==========
def get_topology(db: Session, folder_id: Optional[int] = None) -> dict:
    """组装拓扑图数据：节点=设备，连线=父子层级 + 端口对端关系。"""
    query = db.query(models.Device).options(
        joinedload(models.Device.status),
        joinedload(models.Device.folder)
    )
    if folder_id:
        descendant_ids = get_folder_descendants(db, folder_id)
        if descendant_ids:
            query = query.filter(models.Device.folder_id.in_(descendant_ids))
    devices = query.all()
    device_ids = {d.id for d in devices}

    nodes = [{
        "id": d.id,
        "name": d.name,
        "device_type": d.device_type or "",
        "brand": d.brand or "",
        "model": d.model or "",
        "ip_address": d.ip_address or "",
        "status_name": d.status.name if d.status else "",
        "status_color": d.status.color if d.status else "#909399",
        "folder_name": d.folder.name if d.folder else "",
        "folder_full_path": get_folder_full_path(db, d.folder_id) if d.folder_id else "",
        "parent_device_id": d.parent_device_id,
        "rack_id": d.rack_id,
    } for d in devices]

    links = []
    seen_pairs = set()

    # 1) 父子层级链路（端口未描述时的兜底连线）
    for d in devices:
        if d.parent_device_id and d.parent_device_id in device_ids:
            key = tuple(sorted([d.id, d.parent_device_id]))
            seen_pairs.add(key)
            links.append({
                "source": d.parent_device_id,
                "target": d.id,
                "link_type": "hierarchy",
                "connection_type": "",
                "label": "",
                "source_port": "",
                "target_port": "",
            })

    # 2) 端口对端链路（更精确，覆盖同一对设备的层级连线）
    ports = db.query(models.DevicePort).all()
    for p in ports:
        if p.device_id not in device_ids:
            continue
        if not p.peer_device_id or p.peer_device_id not in device_ids:
            continue
        key = tuple(sorted([p.device_id, p.peer_device_id]))
        # 端口链路优先：移除同一对设备的层级兜底连线
        if key in seen_pairs:
            links = [l for l in links if not (
                l["link_type"] == "hierarchy" and
                tuple(sorted([l["source"], l["target"]])) == key
            )]
        seen_pairs.add(key)

        label = p.connection_type or ""
        if p.connection_type == "aggregate" and p.lag_group:
            label = f"聚合 {p.lag_group}"
        elif p.connection_type == "stack":
            label = f"堆叠 {p.stack_id}".strip()

        links.append({
            "source": p.device_id,
            "target": p.peer_device_id,
            "link_type": "port",
            "connection_type": p.connection_type or "",
            "label": label,
            "source_port": p.port_name or "",
            "target_port": p.peer_port_name or "",
        })

    return {"nodes": nodes, "links": links}


# ========== 非设备物品操作 ==========
def create_non_device_item(db: Session, item: schemas.NonDeviceItemCreate) -> models.NonDeviceItem:
    db_item = models.NonDeviceItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_non_device_items(db: Session, folder_id: Optional[int] = None) -> List[models.NonDeviceItem]:
    query = db.query(models.NonDeviceItem)
    if folder_id:
        query = query.filter(models.NonDeviceItem.folder_id == folder_id)
    return query.order_by(desc(models.NonDeviceItem.created_at)).all()


def get_non_device_item(db: Session, item_id: int) -> Optional[models.NonDeviceItem]:
    return db.query(models.NonDeviceItem).filter(models.NonDeviceItem.id == item_id).first()


def update_non_device_item(db: Session, item_id: int, item_update: schemas.NonDeviceItemBase) -> Optional[models.NonDeviceItem]:
    db_item = get_non_device_item(db, item_id)
    if not db_item:
        return None
    for field, value in item_update.model_dump().items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_non_device_item(db: Session, item_id: int) -> bool:
    db_item = get_non_device_item(db, item_id)
    if not db_item:
        return False
    db.delete(db_item)
    db.commit()
    return True


# ========== 字典操作 ==========
def create_dict(db: Session, item: schemas.DictionaryCreate) -> models.Dictionary:
    db_item = models.Dictionary(**item.model_dump())
    # 同名同类型不重复插入
    exists = db.query(models.Dictionary).filter(
        models.Dictionary.type == db_item.type,
        models.Dictionary.name == db_item.name
    ).first()
    if exists:
        exists.enabled = True
        db.commit()
        db.refresh(exists)
        return exists
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_dicts_by_type(db: Session, dict_type: str) -> List[models.Dictionary]:
    return db.query(models.Dictionary).filter(
        models.Dictionary.type == dict_type
    ).order_by(models.Dictionary.sort_order, models.Dictionary.id).all()


def get_dicts_grouped(db: Session) -> dict:
    """返回 {type: [DictionaryOut...]}，一次性拿全部分类。"""
    rows = db.query(models.Dictionary).order_by(
        models.Dictionary.type, models.Dictionary.sort_order, models.Dictionary.id
    ).all()
    grouped = {}
    for r in rows:
        grouped.setdefault(r.type, []).append(r)
    return grouped


def update_dict(db: Session, dict_id: int, item_update: schemas.DictionaryUpdate) -> Optional[models.Dictionary]:
    db_item = db.query(models.Dictionary).filter(models.Dictionary.id == dict_id).first()
    if not db_item:
        return None
    for field, value in item_update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_dict(db: Session, dict_id: int) -> bool:
    db_item = db.query(models.Dictionary).filter(models.Dictionary.id == dict_id).first()
    if not db_item:
        return False
    db.delete(db_item)
    db.commit()
    return True


# ========== 软件资产操作 ==========
def create_software(db: Session, item: schemas.SoftwareCreate) -> models.Software:
    db_item = models.Software(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_softwares(db: Session, params: schemas.SoftwareListParams) -> tuple:
    query = db.query(models.Software).options(joinedload(models.Software.folder))
    if params.folder_id:
        descendant_ids = get_folder_descendants(db, params.folder_id)
        if descendant_ids:
            query = query.filter(models.Software.folder_id.in_(descendant_ids))
    if params.category:
        query = query.filter(models.Software.category == params.category)
    if params.keyword:
        kw = params.keyword
        query = query.filter(
            or_(
                models.Software.name.contains(kw),
                models.Software.version.contains(kw),
                models.Software.supplier.contains(kw),
            )
        )
    total = query.count()
    items = query.order_by(desc(models.Software.created_at)).offset(
        (params.page - 1) * params.page_size
    ).limit(params.page_size).all()
    return items, total


def get_software(db: Session, software_id: int) -> Optional[models.Software]:
    return db.query(models.Software).options(joinedload(models.Software.folder)).filter(
        models.Software.id == software_id
    ).first()


def update_software(db: Session, software_id: int, item_update: schemas.SoftwareUpdate) -> Optional[models.Software]:
    db_item = get_software(db, software_id)
    if not db_item:
        return None
    for field, value in item_update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_software(db: Session, software_id: int) -> bool:
    db_item = get_software(db, software_id)
    if not db_item:
        return False
    db.delete(db_item)
    db.commit()
    return True


# ========== 合同附件 ==========
def create_contract(db: Session, **kwargs) -> models.Contract:
    c = models.Contract(**kwargs)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def get_contracts(db: Session, keyword: Optional[str] = None, supplier_id: Optional[int] = None,
                  related_type: Optional[str] = None, related_id: Optional[int] = None) -> List[models.Contract]:
    q = db.query(models.Contract)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(models.Contract.name.like(like), models.Contract.supplier_name.like(like)))
    if supplier_id is not None:
        q = q.filter(models.Contract.supplier_id == supplier_id)
    if related_type is not None:
        q = q.filter(models.Contract.related_type == related_type)
    if related_id is not None:
        q = q.filter(models.Contract.related_id == related_id)
    return q.order_by(desc(models.Contract.uploaded_at)).all()


def get_contract(db: Session, contract_id: int) -> Optional[models.Contract]:
    return db.query(models.Contract).filter(models.Contract.id == contract_id).first()


def update_contract(db: Session, contract_id: int, item_update: schemas.ContractUpdate) -> Optional[models.Contract]:
    c = get_contract(db, contract_id)
    if not c:
        return None
    for field, value in item_update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


def delete_contract(db: Session, contract_id: int) -> Optional[models.Contract]:
    c = get_contract(db, contract_id)
    if not c:
        return None
    db.delete(c)
    db.commit()
    return c


# ========== 产品类型 ==========
def create_product_type(db: Session, pt: schemas.ProductTypeCreate) -> models.ProductType:
    db_pt = models.ProductType(**pt.model_dump())
    db.add(db_pt)
    db.commit()
    db.refresh(db_pt)
    # 自动解析 asset_folder_id
    _resolve_product_type_folder(db, db_pt)
    return db_pt


def _resolve_product_type_folder(db: Session, pt: models.ProductType):
    """根据 asset_type + asset_category 自动查找 asset 树中对应节点"""
    # 查找路径：设备资产 > {资产/组件} > {IT资产/非IT资产 / IT组件/非IT组件}
    asset_root = db.query(models.Folder).filter(
        models.Folder.kind == "asset", models.Folder.parent_id == None
    ).first()
    if not asset_root:
        return
    # 第二级：资产 / 组件
    child_name = "资产" if pt.asset_type == "asset" else "组件"
    child = db.query(models.Folder).filter(
        models.Folder.kind == "asset",
        models.Folder.parent_id == asset_root.id,
        models.Folder.name == child_name
    ).first()
    if not child:
        return
    # 第三级：IT资产/非IT资产 或 IT组件/非IT组件
    cat_map = {
        ("asset", "it"): "IT资产", ("asset", "non_it"): "非IT资产",
        ("component", "it"): "IT组件", ("component", "non_it"): "非IT组件",
    }
    grand_name = cat_map.get((pt.asset_type, pt.asset_category), "")
    if not grand_name:
        return
    grand = db.query(models.Folder).filter(
        models.Folder.kind == "asset",
        models.Folder.parent_id == child.id,
        models.Folder.name == grand_name
    ).first()
    if grand:
        pt.asset_folder_id = grand.id
        db.commit()
        db.refresh(pt)


def get_product_types(db: Session, active_only: bool = False) -> List[models.ProductType]:
    q = db.query(models.ProductType).options(joinedload(models.ProductType.field_links))
    if active_only:
        q = q.filter(models.ProductType.is_active == True)
    return q.order_by(models.ProductType.sort_order).all()


def get_product_type(db: Session, pt_id: int) -> Optional[models.ProductType]:
    return db.query(models.ProductType).filter(models.ProductType.id == pt_id).first()


def update_product_type(db: Session, pt_id: int, pt_update: schemas.ProductTypeUpdate) -> Optional[models.ProductType]:
    pt = get_product_type(db, pt_id)
    if not pt:
        return None
    for field, value in pt_update.model_dump(exclude_unset=True).items():
        setattr(pt, field, value)
    db.commit()
    db.refresh(pt)
    # 重新解析 asset_folder_id
    _resolve_product_type_folder(db, pt)
    return pt


def delete_product_type(db: Session, pt_id: int) -> bool:
    pt = get_product_type(db, pt_id)
    if not pt:
        return False
    db.delete(pt)
    db.commit()
    return True


# ========== 自定义字段（增强版） ==========
def create_custom_field(db: Session, cf: schemas.CustomFieldCreate) -> models.CustomField:
    # 自动生成 field_key
    data = cf.model_dump()
    if not data.get("field_key"):
        import re
        data["field_key"] = re.sub(r'[^a-zA-Z0-9_]', '_', data["name"].lower()).strip('_') or "field"
    db_cf = models.CustomField(**data)
    db.add(db_cf)
    db.commit()
    db.refresh(db_cf)
    return db_cf


def get_custom_fields(db: Session, active_only: bool = False) -> List[models.CustomField]:
    q = db.query(models.CustomField)
    if active_only:
        q = q.filter(models.CustomField.is_active == True)
    return q.order_by(models.CustomField.sort_order).all()


def get_custom_field(db: Session, cf_id: int) -> Optional[models.CustomField]:
    return db.query(models.CustomField).filter(models.CustomField.id == cf_id).first()


def update_custom_field(db: Session, cf_id: int, cf_update: schemas.CustomFieldUpdate) -> Optional[models.CustomField]:
    cf = get_custom_field(db, cf_id)
    if not cf:
        return None
    for field, value in cf_update.model_dump(exclude_unset=True).items():
        setattr(cf, field, value)
    db.commit()
    db.refresh(cf)
    return cf


def delete_custom_field(db: Session, cf_id: int) -> bool:
    cf = get_custom_field(db, cf_id)
    if not cf:
        return False
    # 删除关联的布局和值
    db.query(models.ProductTypeField).filter(models.ProductTypeField.field_id == cf_id).delete()
    db.query(models.DeviceCustomValue).filter(models.DeviceCustomValue.field_id == cf_id).delete()
    db.delete(cf)
    db.commit()
    return True


# ========== 产品类型布局 ==========
def link_fields_to_product_type(db: Session, pt_id: int, field_ids: List[int]) -> models.ProductType:
    """将自定义字段批量关联到产品类型"""
    pt = get_product_type(db, pt_id)
    if not pt:
        return None
    # 清空现有关联
    db.query(models.ProductTypeField).filter(
        models.ProductTypeField.product_type_id == pt_id
    ).delete()
    # 创建新关联
    for idx, fid in enumerate(field_ids):
        link = models.ProductTypeField(
            product_type_id=pt_id, field_id=fid, sort_order=idx
        )
        db.add(link)
    db.commit()
    db.refresh(pt)
    return pt


def get_product_type_fields(db: Session, pt_id: int) -> List[models.ProductTypeField]:
    return db.query(models.ProductTypeField).filter(
        models.ProductTypeField.product_type_id == pt_id
    ).order_by(models.ProductTypeField.sort_order).all()


def get_product_type_field_details(db: Session, pt_id: int) -> List[models.CustomField]:
    """获取产品类型关联的自定义字段（返回完整字段对象，按 sort_order 排序）"""
    links = get_product_type_fields(db, pt_id)
    field_ids = [l.field_id for l in links]
    if not field_ids:
        return []
    sort_map = {l.field_id: l.sort_order for l in links}
    req_map = {l.field_id: l.is_required for l in links}
    fields = db.query(models.CustomField).filter(
        models.CustomField.id.in_(field_ids),
        models.CustomField.is_active == True
    ).all()
    # 注入布局级别的 is_required 和 sort_order
    for f in fields:
        f.sort_order = sort_map.get(f.id, 0)
        f.is_required = req_map.get(f.id, f.is_required)
    fields.sort(key=lambda f: f.sort_order)
    return fields
