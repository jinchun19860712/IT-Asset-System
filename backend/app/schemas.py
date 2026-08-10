"""Pydantic 数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== 通用响应 ==========
class ResponseModel(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


# ========== 文件夹 ==========
class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[int] = None
    sort_order: int = 0
    is_department: bool = False
    department_name: Optional[str] = ""
    kind: str = "org"  # 'org' = 组织机构；'asset' = 设备资产


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_department: Optional[bool] = None
    department_name: Optional[str] = None
    kind: Optional[str] = None


class FolderOut(FolderBase):
    id: int
    path: str
    full_path: Optional[str] = None
    effective_department: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: List["FolderOut"] = []

    class Config:
        from_attributes = True


FolderOut.model_rebuild()


# ========== 设备状态 ==========
class DeviceStatusBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = Field(default="#67C23A", max_length=20)
    sort_order: int = 0


class DeviceStatusCreate(DeviceStatusBase):
    pass


class DeviceStatusOut(DeviceStatusBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 自定义字段 ==========
# ========== 产品类型 ==========
class ProductTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    asset_type: str = "asset"              # asset / component
    asset_category: str = "it"             # it / non_it / ''
    device_type: Optional[str] = ""        # 关联的「设备类型」字典值
    icon: Optional[str] = ""
    sort_order: int = 0
    is_active: bool = True


class ProductTypeCreate(ProductTypeBase):
    pass


class ProductTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[str] = None
    asset_category: Optional[str] = None
    device_type: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductTypeOut(ProductTypeBase):
    id: int
    asset_folder_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 产品类型布局 ==========
class ProductTypeFieldLink(BaseModel):
    """批量关联请求：将自定义字段绑定到产品类型"""
    field_ids: List[int] = Field(..., min_length=1)


class ProductTypeFieldOut(BaseModel):
    id: int
    product_type_id: int
    field_id: int
    sort_order: int
    is_required: bool = False

    class Config:
        from_attributes = True


# ========== 自定义字段（增强版） ==========
class CustomFieldBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    field_key: Optional[str] = ""
    field_type: str = Field(default="text")
    is_required: bool = False
    options: Optional[List[dict]] = []    # [{"label":"选项A","value":"a"},...]
    config: Optional[dict] = {}           # {required, default_value, placeholder, ...}
    is_active: bool = True
    sort_order: int = 0


class CustomFieldCreate(CustomFieldBase):
    pass


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = None
    field_key: Optional[str] = None
    field_type: Optional[str] = None
    is_required: Optional[bool] = None
    options: Optional[List[dict]] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CustomFieldOut(CustomFieldBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 设备自定义值 ==========
class DeviceCustomValueBase(BaseModel):
    field_id: int
    value: str = ""


class DeviceCustomValueOut(DeviceCustomValueBase):
    id: int
    field_name: Optional[str] = None
    field_type: Optional[str] = None

    class Config:
        from_attributes = True


# ========== 端口 ==========
class DevicePortBase(BaseModel):
    port_name: str = Field(..., min_length=1, max_length=100)
    port_type: str = "downlink"          # uplink/downlink/peer
    connection_type: str = "access"      # access/trunk/hybrid/aggregate/stack/routed
    peer_device_id: Optional[int] = None
    peer_port_name: Optional[str] = ""
    lag_group: Optional[str] = ""
    lag_mode: Optional[str] = ""
    stack_id: Optional[str] = ""
    vlan_info: Optional[str] = ""
    port_speed: Optional[str] = ""
    description: Optional[str] = ""
    sort_order: Optional[int] = 0


class DevicePortCreate(DevicePortBase):
    pass


class DevicePortOut(DevicePortBase):
    id: int
    device_id: int
    peer_device_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 设备 ==========
class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    device_type: Optional[str] = ""
    product_type_id: Optional[int] = None
    brand: Optional[str] = ""
    supplier: Optional[str] = ""
    model: Optional[str] = ""
    parent_device_id: Optional[int] = None

    ip_address: Optional[str] = ""
    network_mask: Optional[str] = ""
    mac_address: Optional[str] = ""
    management_vlan: Optional[str] = ""

    area: Optional[str] = ""
    room_type: Optional[str] = ""
    room_number: Optional[str] = ""

    service_code: Optional[str] = ""
    status_id: Optional[int] = None
    disuse_date: Optional[str] = ""
    department: Optional[str] = ""
    user: Optional[str] = ""

    support_ssh2: Optional[bool] = False
    support_telnet: Optional[bool] = False
    support_web: Optional[bool] = False
    support_snmp: Optional[bool] = False
    support_rdp: Optional[bool] = False
    support_console: Optional[bool] = False
    management_services: Optional[str] = ""

    bmc_ip: Optional[str] = ""
    bmc_mac: Optional[str] = ""
    mgmt_username: Optional[str] = ""
    mgmt_password: Optional[str] = ""

    rack_id: Optional[int] = None
    rack_position: Optional[int] = None
    rack_units: Optional[int] = 1
    rack_face: Optional[str] = "front"

    folder_id: Optional[int] = None
    asset_folder_id: Optional[int] = None
    description: Optional[str] = ""
    remark: Optional[str] = ""
    snmp_template_name: Optional[str] = ""
    snmp_selected_metrics: Optional[str] = ""

    # 端口统计
    port_count: Optional[int] = 0
    port_types: Optional[List[str]] = []
    port_count_by_type: Optional[Dict[str, int]] = {}  # {"electric":48,"optical":4}

    # SNMP 连接参数
    snmp_version: Optional[str] = "v2c"
    snmp_port: Optional[int] = 161
    snmp_community: Optional[str] = ""
    snmp_v3_user: Optional[str] = ""
    snmp_v3_auth_protocol: Optional[str] = "SHA"
    snmp_v3_auth_key: Optional[str] = ""
    snmp_v3_priv_protocol: Optional[str] = "AES"
    snmp_v3_priv_key: Optional[str] = ""


class DeviceCreate(DeviceBase):
    custom_values: List[DeviceCustomValueBase] = []
    ports: List[DevicePortCreate] = []


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_type: Optional[str] = None
    product_type_id: Optional[int] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    parent_device_id: Optional[int] = None
    snmp_template_name: Optional[str] = None
    snmp_selected_metrics: Optional[str] = None

    port_count: Optional[int] = None
    port_types: Optional[List[str]] = None
    port_count_by_type: Optional[Dict[str, int]] = None

    snmp_version: Optional[str] = None
    snmp_port: Optional[int] = None
    snmp_community: Optional[str] = None
    snmp_v3_user: Optional[str] = None
    snmp_v3_auth_protocol: Optional[str] = None
    snmp_v3_auth_key: Optional[str] = None
    snmp_v3_priv_protocol: Optional[str] = None
    snmp_v3_priv_key: Optional[str] = None

    ip_address: Optional[str] = None
    network_mask: Optional[str] = None
    mac_address: Optional[str] = None
    management_vlan: Optional[str] = None

    area: Optional[str] = None
    room_type: Optional[str] = None
    room_number: Optional[str] = None

    service_code: Optional[str] = None
    status_id: Optional[int] = None
    disuse_date: Optional[str] = None
    department: Optional[str] = None
    user: Optional[str] = None

    support_ssh2: Optional[bool] = None
    support_telnet: Optional[bool] = None
    support_web: Optional[bool] = None
    support_snmp: Optional[bool] = None
    support_rdp: Optional[bool] = None
    support_console: Optional[bool] = None
    management_services: Optional[str] = None

    bmc_ip: Optional[str] = None
    bmc_mac: Optional[str] = None
    mgmt_username: Optional[str] = None
    mgmt_password: Optional[str] = None

    rack_id: Optional[int] = None
    rack_position: Optional[int] = None
    rack_units: Optional[int] = None
    rack_face: Optional[str] = None

    supplier: Optional[str] = None
    folder_id: Optional[int] = None
    asset_folder_id: Optional[int] = None
    description: Optional[str] = None
    custom_values: List[DeviceCustomValueBase] = []
    ports: Optional[List[DevicePortCreate]] = None


class DeviceOut(DeviceBase):
    id: int
    status_name: Optional[str] = None
    status_color: Optional[str] = None
    folder_name: Optional[str] = None
    folder_full_path: Optional[str] = None
    asset_folder_id: Optional[int] = None
    asset_folder_name: Optional[str] = None
    parent_device_name: Optional[str] = None
    product_type_name: Optional[str] = None
    rack_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    custom_values: List[DeviceCustomValueOut] = []
    ports: List[DevicePortOut] = []

    class Config:
        from_attributes = True


# ========== 机柜 ==========
class RackBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    u_height: int = 42
    location: Optional[str] = ""
    row_label: Optional[str] = ""
    folder_id: Optional[int] = None
    description: Optional[str] = ""
    sort_order: Optional[int] = 0


class RackCreate(RackBase):
    pass


class RackUpdate(BaseModel):
    name: Optional[str] = None
    u_height: Optional[int] = None
    location: Optional[str] = None
    row_label: Optional[str] = None
    folder_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class RackOut(RackBase):
    id: int
    device_count: Optional[int] = 0
    used_units: Optional[int] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RackMountRequest(BaseModel):
    """设备上架请求"""
    device_id: int
    rack_position: int = Field(..., ge=1)
    rack_units: int = Field(default=1, ge=1)
    rack_face: str = "front"


# ========== SNMP ==========
class SnmpMetricValueOut(BaseModel):
    id: int
    device_id: int
    metric_name: str
    metric_oid: str
    value: str
    unit: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 非设备物品 ==========
class NonDeviceItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    item_type: Optional[str] = ""
    brand: Optional[str] = ""
    model: Optional[str] = ""
    quantity: Optional[int] = 0
    location: Optional[str] = ""
    folder_id: Optional[int] = None
    warning_threshold: Optional[int] = 0


class NonDeviceItemCreate(NonDeviceItemBase):
    pass


class NonDeviceItemOut(NonDeviceItemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 列表查询参数 ==========
class DeviceListParams(BaseModel):
    page: int = 1
    page_size: int = 20
    keyword: Optional[str] = None
    folder_id: Optional[int] = None
    asset_folder_id: Optional[int] = None
    device_type: Optional[str] = None
    department: Optional[str] = None
    user: Optional[str] = None
    status_id: Optional[int] = None
    sort_field: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    # 面板默认范围：asset_default=资产面板默认，org_default=组织架构默认
    scope: Optional[str] = None
    # ====== 多值筛选（仪表盘等场景，逗号分隔字符串传入） ======
    folder_ids: Optional[str] = None          # 多个组织机构文件夹 id
    asset_folder_ids: Optional[str] = None    # 多个资产文件夹 id
    device_types: Optional[str] = None        # 多个设备类型
    suppliers: Optional[str] = None           # 多个供应商


# ========== 字典 ==========
class DictionaryBase(BaseModel):
    type: str = Field(..., min_length=1, max_length=30)  # product_type/brand/supplier/software_category
    name: str = Field(..., min_length=1, max_length=200)
    sort_order: int = 0
    enabled: bool = True
    # 供应商联系信息（仅 type='supplier' 使用）
    contact_person: Optional[str] = ""
    contact_phone: Optional[str] = ""
    company_name: Optional[str] = ""
    company_address: Optional[str] = ""


class DictionaryCreate(DictionaryBase):
    pass


class DictionaryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None


class DictionaryOut(DictionaryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 软件资产 ==========
class SoftwareBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    version: Optional[str] = ""
    category: Optional[str] = ""
    supplier: Optional[str] = ""
    folder_id: Optional[int] = None
    remark: Optional[str] = ""


class SoftwareCreate(SoftwareBase):
    pass


class SoftwareUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    supplier: Optional[str] = None
    folder_id: Optional[int] = None
    remark: Optional[str] = None


class SoftwareOut(SoftwareBase):
    id: int
    folder_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 合同附件 ==========
class ContractBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = ""
    related_type: Optional[str] = ""        # device / software / ''
    related_id: Optional[int] = None
    remark: Optional[str] = ""


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    remark: Optional[str] = None


class ContractOut(ContractBase):
    id: int
    file_name: str = ""
    file_type: str = ""
    file_size: int = 0
    uploaded_at: Optional[datetime] = None
    download_url: Optional[str] = ""

    class Config:
        from_attributes = True


# ========== 软件列表查询参数 ==========
class SoftwareListParams(BaseModel):
    page: int = 1
    page_size: int = 50
    keyword: Optional[str] = None
    folder_id: Optional[int] = None
    category: Optional[str] = None


# ========== 批量操作 ==========
class BulkIds(BaseModel):
    """批量操作的 ID 列表"""
    ids: List[int] = Field(..., min_length=1)


class DeviceBulkUpdate(BaseModel):
    """批量修改设备：只有显式传入的字段才会被写入"""
    ids: List[int] = Field(..., min_length=1)
    department: Optional[str] = None
    user: Optional[str] = None
    status_id: Optional[int] = None
    folder_id: Optional[int] = None
    asset_folder_id: Optional[int] = None
    device_type: Optional[str] = None
    brand: Optional[str] = None
    supplier: Optional[str] = None
    area: Optional[str] = None
    remark: Optional[str] = None
    snmp_enabled: Optional[bool] = None
    snmp_template: Optional[str] = None


class SoftwareBulkUpdate(BaseModel):
    """批量修改软件"""
    ids: List[int] = Field(..., min_length=1)
    folder_id: Optional[int] = None
    category: Optional[str] = None
    supplier: Optional[str] = None
    version: Optional[str] = None
    remark: Optional[str] = None


# ========== SNMP 全局配置 ==========
class SnmpSettings(BaseModel):
    simulate: bool = False              # true=使用模拟数据（无真实设备时）
    default_version: str = "v2c"
    default_port: int = 161
    default_community: str = "public"
    timeout: float = 2.0
    retries: int = 1
