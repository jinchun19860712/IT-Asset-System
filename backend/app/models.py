"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """用户表（基础账户体系 B1）。

    密码以 pbkdf2$... 格式存（hashlib.pbkdf2_hmac + 16字节 salt + 10万次迭代），
    校验见 app.utils.security.verify_password。

    role 取值：
      admin - 管理员（可管理用户、进入所有页面、所有写操作）
      user  - 普通用户（只读 + 受限写）

    进程级 session 表存内存 dict（见 app.auth），重启后所有会话失效。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), default="")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # admin / user
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Folder(Base):
    """文件夹树形结构"""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    path = Column(String(500), default="")  # 完整路径，如 /1/2/3/
    sort_order = Column(Integer, default=0)
    # 树的种类：'org' = 组织机构（按部门/机构）；'asset' = 设备资产（按资产分类）
    # 左侧导航可在两种树之间切换显示
    kind = Column(String(10), default="org", nullable=False)

    # 组织属性：标记该节点是否代表一个"部门"
    # 设备保存时会向上查找最近的 is_department=True 节点，自动填充部门字段
    is_department = Column(Boolean, default=False)
    # 可选：部门显示名（为空则用 name）
    department_name = Column(String(100), default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent")
    devices = relationship("Device", back_populates="folder", foreign_keys="Device.folder_id")


class DeviceStatus(Base):
    """设备状态定义"""
    __tablename__ = "device_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    color = Column(String(20), default="#67C23A")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class ProductType(Base):
    """产品类型定义（AssetExplorer 风格）
    
    每种产品类型有资产分类归属：
      asset_type + asset_category → 映射到 asset 树对应节点
      asset=资产: it→IT资产, non_it→非IT资产
      asset=组件: it→IT组件, non_it→非IT组件
    """
    __tablename__ = "product_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    asset_type = Column(String(20), default="asset")      # asset / component
    asset_category = Column(String(20), default="it")    # it / non_it / ''
    asset_folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)  # 自动解析到的资产树节点
    device_type = Column(String(50), default="")     # 关联的「设备类型」字典值（基础数据 → 设备类型）
    icon = Column(String(50), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    asset_folder = relationship("Folder", foreign_keys=[asset_folder_id])


class CustomField(Base):
    """自定义字段定义（增强版：支持 11 种字段类型）
    
    field_type 取值：
      text（单行文本）、textarea（多行文本）、number（数字）、decimal（小数）、
      percentage（百分比）、date（日期）、datetime（日期时间）、
      checkbox（复选框）、radio（单选按钮）、select（下拉列表）、multi_select（多选）
    
    options: JSON 数组，[{"label":"选项A","value":"a"}, ...]
      (仅 select/radio/checkbox/multi_select 使用)
    config: JSON 对象，{"required":true,"default_value":"","placeholder":"...","min":0,"max":100,"rows":3,...}
    """
    __tablename__ = "custom_fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)                   # 显示名称
    field_key = Column(String(100), default="")                  # 机器名（用于 API 传值，自动由 name 生成）
    field_type = Column(String(20), default="text")
    is_required = Column(Boolean, default=False)
    options = Column(JSON, default=list)                         # [{"label":"","value":""}]
    config = Column(JSON, default=dict)                          # {required, default_value, placeholder, ...}
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联到产品类型布局
    product_type_links = relationship("ProductTypeField", back_populates="field", cascade="all, delete-orphan")


class ProductTypeField(Base):
    """产品类型布局关联：产品类型 ↔ 自定义字段
    
    实现不同产品类型显示不同字段的核心关联表。
    """
    __tablename__ = "product_type_fields"

    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("custom_fields.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    is_required = Column(Boolean, default=False)  # 布局级别的必填覆盖

    product_type = relationship("ProductType", back_populates="field_links")
    field = relationship("CustomField", back_populates="product_type_links")


# 为 ProductType 补充反向关联
ProductType.field_links = relationship("ProductTypeField", back_populates="product_type", cascade="all, delete-orphan")


class Device(Base):
    """设备主表"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    device_type = Column(String(100), default="")
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=True, index=True)  # 关联产品类型
    brand = Column(String(100), default="")
    supplier = Column(String(100), default="")  # 供应商（来自字典，自由文本便于兼容）
    model = Column(String(100), default="")
    parent_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, index=True)

    # 网络信息
    ip_address = Column(String(50), default="")
    network_mask = Column(String(50), default="")
    mac_address = Column(String(50), default="")
    management_vlan = Column(String(20), default="")

    # 位置信息
    area = Column(String(200), default="")
    room_type = Column(String(100), default="")
    room_number = Column(String(100), default="")

    # 资产信息
    service_code = Column(String(200), default="")
    status_id = Column(Integer, ForeignKey("device_statuses.id"), nullable=True, index=True)
    disuse_date = Column(String(20), default="")
    department = Column(String(100), default="")
    user = Column(String(100), default="")

    # 支持的管理方式
    support_ssh2 = Column(Boolean, default=False)
    support_telnet = Column(Boolean, default=False)
    support_web = Column(Boolean, default=False)
    support_snmp = Column(Boolean, default=False)
    support_rdp = Column(Boolean, default=False)
    support_console = Column(Boolean, default=False)
    management_services = Column(String(200), default="")

    # BMC信息
    bmc_ip = Column(String(50), default="")
    bmc_mac = Column(String(50), default="")

    # 管理账号
    mgmt_username = Column(String(100), default="")
    mgmt_password = Column(String(100), default="")

    # 机柜上架信息
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True, index=True)
    rack_position = Column(Integer, nullable=True)  # 起始U位（从底部数，1为最底层）
    rack_units = Column(Integer, default=1)          # 占用U数
    rack_face = Column(String(10), default="front")  # front/rear

    # 其他
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)
    asset_folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)  # 设备资产分类（资产树）
    description = Column(Text, default="")
    remark = Column(Text, default="")  # 备注
    snmp_template_name = Column(String(100), default="")
    snmp_selected_metrics = Column(Text, default="")  # JSON字符串：["CPU利用率","内存利用率"]

    # 端口统计（用于快速生成端口列表与流量图）
    port_count = Column(Integer, default=0)            # 端口总数量（自动汇总 port_count_by_type）
    port_types = Column(JSON, default=list)            # 端口类型：["electric","optical",...]
    port_count_by_type = Column(JSON, default=dict)    # 按类型细分：{"electric":48,"optical":4,...}

    # SNMP 连接参数（真实采集用；留空则回退到全局默认）
    snmp_version = Column(String(10), default="v2c")        # v1 / v2c / v3
    snmp_port = Column(Integer, default=161)
    snmp_community = Column(String(100), default="")        # v1/v2c 团体名
    snmp_v3_user = Column(String(100), default="")
    snmp_v3_auth_protocol = Column(String(20), default="SHA")   # none/MD5/SHA
    snmp_v3_auth_key = Column(String(200), default="")
    snmp_v3_priv_protocol = Column(String(20), default="AES")   # none/DES/AES
    snmp_v3_priv_key = Column(String(200), default="")
    snmp_last_poll_at = Column(DateTime, nullable=True)
    snmp_last_error = Column(Text, default="")              # 上次采集失败原因，成功则置空

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    folder = relationship("Folder", back_populates="devices", foreign_keys="Device.folder_id")
    asset_folder = relationship("Folder", foreign_keys=[asset_folder_id])
    status = relationship("DeviceStatus")
    rack = relationship("Rack", back_populates="devices")
    product_type = relationship("ProductType")
    custom_values = relationship("DeviceCustomValue", back_populates="device", cascade="all, delete-orphan")
    parent_device = relationship("Device", remote_side=[id], back_populates="child_devices")
    child_devices = relationship("Device", back_populates="parent_device")
    ports = relationship("DevicePort", back_populates="device", foreign_keys="DevicePort.device_id",
                         cascade="all, delete-orphan")


class Rack(Base):
    """机柜"""
    __tablename__ = "racks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    u_height = Column(Integer, default=42)           # 机柜总U数
    location = Column(String(200), default="")       # 所在机房/位置描述
    row_label = Column(String(50), default="")       # 列/排编号
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    devices = relationship("Device", back_populates="rack")
    folder = relationship("Folder")


class DevicePort(Base):
    """设备端口（上联/下联）"""
    __tablename__ = "device_ports"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    port_name = Column(String(100), nullable=False)  # 如：GigabitEthernet1/0/1
    port_type = Column(String(20), default="downlink")  # uplink/downlink/peer
    # access/trunk/hybrid/aggregate/stack/routed
    connection_type = Column(String(20), default="access")
    peer_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    peer_port_name = Column(String(100), default="")  # 对端端口名
    lag_group = Column(String(50), default="")  # 聚合组号，如 1 / BAGG1 / Po1
    lag_mode = Column(String(20), default="")   # static/lacp
    stack_id = Column(String(20), default="")   # 堆叠成员号
    vlan_info = Column(String(200), default="")  # Access: VLAN号；Trunk: 允许VLAN列表
    port_speed = Column(String(30), default="")  # 如 1G/10G/40G
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    device = relationship("Device", foreign_keys=[device_id], back_populates="ports")
    peer_device = relationship("Device", foreign_keys=[peer_device_id])


class DeviceCustomValue(Base):
    """设备的自定义字段值"""
    __tablename__ = "device_custom_values"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("custom_fields.id"), nullable=False)
    value = Column(Text, default="")

    device = relationship("Device", back_populates="custom_values")
    field = relationship("CustomField")


class SnmpMetricValue(Base):
    """SNMP 监控指标实时值"""
    __tablename__ = "snmp_metric_values"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_oid = Column(String(200), default="")
    value = Column(String(200), default="")
    unit = Column(String(50), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NonDeviceItem(Base):
    """非设备物品（耗材等）"""
    __tablename__ = "non_device_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    item_type = Column(String(100), default="")
    brand = Column(String(100), default="")
    model = Column(String(100), default="")
    quantity = Column(Integer, default=0)
    location = Column(String(200), default="")
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)
    warning_threshold = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Dictionary(Base):
    """通用字典表：产品类型 / 品牌 / 供应商 / 软件分类 等都存这里。

    type 取值：product_type / brand / supplier / software_category
    """
    __tablename__ = "dictionaries"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(30), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sort_order = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    # 供应商(仅 type='supplier' 使用)的联系信息
    contact_person = Column(String(100), default="")   # 姓名 / 联系人
    contact_phone = Column(String(100), default="")    # 联系方式
    company_name = Column(String(200), default="")     # 公司名称
    company_address = Column(String(300), default="")  # 公司地址
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Software(Base):
    """软件资产（独立于硬件设备的资产记录）"""
    __tablename__ = "softwares"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    version = Column(String(100), default="")           # 采购版本
    category = Column(String(100), default="")          # 软件分类（来自字典 software_category）
    supplier = Column(String(100), default="")          # 供应商（来自字典 supplier，可复用）
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)  # 归属资产树节点
    remark = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    folder = relationship("Folder")


class Contract(Base):
    """合同附件：设备 / 软件采购合同等，支持 PDF / PNG / JPG。

    supplier_id 指向 dictionaries(type='supplier').id（弱引用，不建外键，便于供应商被删后保留合同）。
    related_type / related_id 表示关联到哪台设备 / 哪个软件（为空表示仅归档、未关联）。
    """
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)              # 合同名称
    supplier_id = Column(Integer, nullable=True)            # 关联供应商（dictionaries.id）
    supplier_name = Column(String(200), default="")         # 供应商名称（冗余，便于检索）
    related_type = Column(String(20), default="")           # device / software / ''
    related_id = Column(Integer, nullable=True)             # 关联对象 id
    file_path = Column(String(500), default="")             # 磁盘相对路径（相对于 uploads 根）
    file_name = Column(String(300), default="")             # 原始文件名
    file_type = Column(String(20), default="")              # pdf / png / jpg
    file_size = Column(Integer, default=0)
    remark = Column(Text, default="")
    uploaded_at = Column(DateTime, server_default=func.now())

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Alert(Base):
    """告警记录：当 SNMP 采集值超过模板阈值时自动写入。

    level:
      warning  - 超过 warning_threshold 但未到 critical
      critical - 超过 critical_threshold（通常更严重）
      ok       - 用于"恢复"事件（可选）

    metric_name / metric_oid / value / unit 来自当前采集值。
    message 是给运维人员看的一句话总结。

    acknowledged / acknowledged_by / acknowledged_at 标记是否已被人工 ack。
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    device_name = Column(String(200), default="")
    metric_name = Column(String(100), nullable=False)
    metric_oid = Column(String(200), default="")
    value = Column(String(100), default="")           # 字符串形式（避免 0/float 失真）
    unit = Column(String(20), default="")
    threshold = Column(String(50), default="")        # 触发告警的阈值（如 ">= 80.0"）
    level = Column(String(20), default="warning")     # warning / critical / ok
    message = Column(String(500), default="")
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(50), default="")
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    device = relationship("Device", foreign_keys=[device_id])


class AuditLog(Base):
    """操作审计日志（N3）：记录登录 / 增删改 等关键操作。

    - actor_id / actor_name：操作者；为空表示匿名（如登录失败时的尝试者）
    - action：login / logout / create / update / delete / import / export / ack / poll ...
    - target_type：device / software / contract / user / folder / dictionary / product_type /
                    custom_field / alert / auth / config
    - target_id：被操作对象 id（如果适用）
    - target_name：操作对象的可读名（如设备名、用户名），便于在列表里直观定位
    - message：一句简短描述
    - ip：客户端 IP（来自 X-Forwarded-For / request.client.host）
    - user_agent：浏览器标识（截断到 200 字符）
    - diff：可选的 JSON 字符串，存变更前后关键字段摘要，便于审计追责
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, nullable=True, index=True)
    actor_name = Column(String(50), default="")
    action = Column(String(30), nullable=False, index=True)
    target_type = Column(String(30), default="", index=True)
    target_id = Column(Integer, nullable=True, index=True)
    target_name = Column(String(200), default="")
    message = Column(String(500), default="")
    ip = Column(String(50), default="")
    user_agent = Column(String(200), default="")
    diff = Column(Text, default="")             # JSON 字符串
    success = Column(Boolean, default=True)     # 操作是否成功
    created_at = Column(DateTime, server_default=func.now(), index=True)
