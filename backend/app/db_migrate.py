"""轻量级自动迁移：比对 SQLAlchemy 模型与 SQLite 实际表结构，自动补齐缺失的列。

SQLite 的 ALTER TABLE 只支持 ADD COLUMN，这里也只做加列这一件事：
模型里新增字段后重启服务即可生效，不需要每次手写 migrate 脚本。
删列/改类型仍需手动迁移。
"""
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError


def _sqlite_type(column) -> str:
    """把 SQLAlchemy 列类型转成 SQLite DDL 类型"""
    try:
        return column.type.compile(dialect=None) if column.type else "TEXT"
    except Exception:
        name = column.type.__class__.__name__.upper()
        return {
            "INTEGER": "INTEGER", "BIGINTEGER": "INTEGER", "SMALLINTEGER": "INTEGER",
            "BOOLEAN": "BOOLEAN", "FLOAT": "REAL", "NUMERIC": "NUMERIC",
            "DATETIME": "DATETIME", "DATE": "DATE", "TEXT": "TEXT",
        }.get(name, "TEXT")


def _default_clause(column) -> str:
    """生成 DEFAULT 子句；只处理标量默认值，可调用默认值（如 now()）交给应用层"""
    default = column.default
    if default is None or getattr(default, "is_callable", False):
        return ""
    arg = getattr(default, "arg", None)
    if arg is None or callable(arg):
        return ""
    if isinstance(arg, bool):
        return f" DEFAULT {1 if arg else 0}"
    if isinstance(arg, (int, float)):
        return f" DEFAULT {arg}"
    escaped = str(arg).replace("'", "''")
    return f" DEFAULT '{escaped}'"


def auto_add_missing_columns(engine, base) -> list:
    """扫描所有模型表，给已存在的表补上模型里新增的列。返回新增列的描述列表。"""
    added = []
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        for table in base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # 新表由 create_all 负责
            current = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in current:
                    continue
                if column.primary_key:
                    continue  # 主键无法后加
                ddl_type = _sqlite_type(column)
                # SQLite 加列不允许 NOT NULL 且无默认值
                nullable = "" if column.nullable else " NOT NULL"
                default = _default_clause(column)
                if nullable and not default:
                    nullable = ""
                sql = (f'ALTER TABLE "{table.name}" '
                       f'ADD COLUMN "{column.name}" {ddl_type}{nullable}{default}')
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    added.append(f"{table.name}.{column.name}")
                except SQLAlchemyError as exc:
                    print(f"[migrate] 加列失败 {table.name}.{column.name}: {exc}")
    return added


def migrate_device_types_to_dict(engine, SessionLocal) -> list:
    """把 devices.device_type 已使用的去重值导入到 dictionaries(type='device_type')，
    方便在「基础数据 → 设备类型」里增删改。
    返回新增的字典项列表（已存在的跳过）。
    """
    from app import models
    added = []
    with SessionLocal() as db:
        try:
            # 取出所有非空 device_type 去重
            rows = db.query(models.Device.device_type).filter(
                models.Device.device_type.isnot(None),
                models.Device.device_type != ''
            ).distinct().all()
            used_types = sorted({r[0] for r in rows if r[0]})
            # 已有字典值
            existing = {
                d.name for d in db.query(models.Dictionary).filter(
                    models.Dictionary.type == 'device_type'
                ).all()
            }
            # 计算 sort_order
            max_sort = db.query(models.Dictionary).filter(
                models.Dictionary.type == 'device_type'
            ).count()
            for name in used_types:
                if name in existing:
                    continue
                d = models.Dictionary(
                    type='device_type', name=name,
                    sort_order=max_sort, enabled=True
                )
                db.add(d)
                max_sort += 1
                added.append(name)
            if added:
                db.commit()
        except SQLAlchemyError as exc:
            print(f"[migrate] 设备类型字典导入失败: {exc}")
            db.rollback()
    return added


def migrate_preset_device_types_to_dict(engine, SessionLocal) -> list:
    """把前端硬编码兜底的 PRESET_TYPES 导入到字典「设备类型」，
    让用户能在「基础数据 → 设备类型」里统一管理所有类型选项。
    """
    from app import models
    PRESET = ['交换机', '路由器', '防火墙', '服务器', '存储', '打印机',
              '复印机', '电脑', 'UPS', '摄像头', '无线AP']
    added = []
    with SessionLocal() as db:
        try:
            existing = {
                d.name for d in db.query(models.Dictionary).filter(
                    models.Dictionary.type == 'device_type'
                ).all()
            }
            max_sort = db.query(models.Dictionary).filter(
                models.Dictionary.type == 'device_type'
            ).count()
            for name in PRESET:
                if name in existing:
                    continue
                d = models.Dictionary(
                    type='device_type', name=name,
                    sort_order=max_sort, enabled=True
                )
                db.add(d)
                max_sort += 1
                added.append(name)
            if added:
                db.commit()
        except SQLAlchemyError as exc:
            print(f"[migrate] PRESET 设备类型导入失败: {exc}")
            db.rollback()
    return added


def auto_add_indexes(engine) -> list:
    """SQLite 创建表后 ALTER TABLE 不支持加索引，只能手动 CREATE INDEX IF NOT EXISTS。

    对于已存在的设备表，重建关键索引。模型里加 index=True 只对未来新建表生效，
    所以这里补充运行时索引创建。
    """
    from sqlalchemy import text
    added = []
    target_indexes = [
        ("devices", "ix_devices_folder_id", "folder_id"),
        ("devices", "ix_devices_asset_folder_id", "asset_folder_id"),
        ("devices", "ix_devices_status_id", "status_id"),
        ("devices", "ix_devices_parent_device_id", "parent_device_id"),
        ("devices", "ix_devices_rack_id", "rack_id"),
        ("devices", "ix_devices_ip_address", "ip_address"),
        ("devices", "ix_devices_product_type_id", "product_type_id"),
    ]
    try:
        with engine.connect() as conn:
            for table, name, col in target_indexes:
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})"))
                    conn.commit()
                    added.append(name)
                except Exception as ie:
                    print(f"[migrate] 跳过索引 {name}: {ie}")
    except Exception as exc:
        print(f"[migrate] 索引迁移失败: {exc}")
    return added
