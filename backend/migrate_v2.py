"""迁移 v2：双树（组织机构 / 设备资产）+ 字典 + 软件模块

- folders   : 新增 kind 列（org / asset）；删除机构树下的设备类型三级文件夹（电脑/打印机/交换机/其他设备）
- devices   : 新增 asset_folder_id、supplier
- 新建表     : dictionaries（通用字典）、softwares（软件资产）
- 种入数据   : “设备资产”树（资产/组件/软件 -> IT/非IT…），并据现有设备类型/品牌填充默认字典

幂等，可重复执行。
"""
import os
import sqlite3

from sqlalchemy import text
from app.database import engine, SessionLocal, Base
from app import models, crud

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "it_asset.db")


def table_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [c[1] for c in cursor.fetchall()]


def add_column(cursor, table, column, ddl):
    if column not in table_columns(cursor, table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        print(f"  + {table}.{column}")
        return True
    return False


# ---------------- 1. 加列 ----------------
def migrate_columns():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print("[1] 加列")
    add_column(cur, "folders", "kind", "VARCHAR(10) NOT NULL DEFAULT 'org'")
    add_column(cur, "devices", "asset_folder_id", "INTEGER")
    add_column(cur, "devices", "supplier", "VARCHAR(100) DEFAULT ''")
    # 供应商联系信息（仅 type='supplier' 使用）
    add_column(cur, "dictionaries", "contact_person", "VARCHAR(100) DEFAULT ''")
    add_column(cur, "dictionaries", "contact_phone", "VARCHAR(100) DEFAULT ''")
    add_column(cur, "dictionaries", "company_name", "VARCHAR(200) DEFAULT ''")
    add_column(cur, "dictionaries", "company_address", "VARCHAR(300) DEFAULT ''")
    conn.commit()
    conn.close()
    # 旧文件夹默认归为组织机构
    db = SessionLocal()
    try:
        db.execute(text("UPDATE folders SET kind='org' WHERE kind IS NULL OR kind=''"))
        db.commit()
        print("  = 旧文件夹 kind 置为 org")
    finally:
        db.close()


# ---------------- 2. 建新表 ----------------
def migrate_tables():
    print("[2] 建新表")
    Base.metadata.create_all(bind=engine)
    print("  = dictionaries / softwares 表已就绪")


# ---------------- 3. 种入“设备资产”树 ----------------
ASSET_TREE = {
    "设备资产": {
        "资产": {"IT资产": {}, "非IT资产": {}},
        "组件": {"IT组件": {}, "非IT组件": {}},
        "软件": {},
    }
}


def seed_asset_tree():
    print("[3] 种入“设备资产”树")
    db = SessionLocal()
    try:
        def find_or_create(parent_id, name, kind, sort_order):
            existing = db.query(models.Folder).filter(
                models.Folder.parent_id == parent_id,
                models.Folder.name == name,
                models.Folder.kind == kind,
            ).first()
            if existing:
                return existing
            return crud.create_folder(db, schemas_FolderCreate(name=name, parent_id=parent_id,
                                                              kind=kind, sort_order=sort_order))

        def walk(node, name, parent_id, sort=0):
            f = find_or_create(parent_id, name, "asset", sort)
            for i, (child_name, children) in enumerate(node.items()):
                walk(children, child_name, f.id, i)
            return f

        for i, (name, children) in enumerate(ASSET_TREE.items()):
            walk(children, name, None, i)
        print("  = 设备资产树已就绪")
    finally:
        db.close()


# ---------------- 4. 种入默认字典 ----------------
def seed_dictionaries():
    print("[4] 种入默认字典（产品类型 / 品牌）")
    db = SessionLocal()
    try:
        types = [t[0] for t in db.query(models.Device.device_type).distinct().all() if t[0]]
        brands = [b[0] for b in db.query(models.Device.brand).distinct().all() if b[0]]
        for t in sorted(set(types)):
            crud.create_dict(db, schemas_DictionaryCreate(type="product_type", name=t))
        for b in sorted(set(brands)):
            crud.create_dict(db, schemas_DictionaryCreate(type="brand", name=b))
        print(f"  = 产品类型 {len(set(types))} 项，品牌 {len(set(brands))} 项")
    finally:
        db.close()


# ---------------- 5. 清理机构树下的设备类型三级文件夹 ----------------
DEVICE_TYPE_LEAVES = {"电脑", "打印机", "交换机", "其他设备"}


def clean_org_tree():
    print("[5] 清理机构树下的设备类型三级文件夹")
    db = SessionLocal()
    try:
        depts = {d.id: d for d in db.query(models.Folder).filter(models.Folder.is_department == True).all()}
        leaves = db.query(models.Folder).filter(
            models.Folder.parent_id.isnot(None),
            models.Folder.kind == "org",
            models.Folder.name.in_(DEVICE_TYPE_LEAVES),
        ).all()
        moved = 0
        deleted = 0
        for leaf in leaves:
            parent = depts.get(leaf.parent_id)
            if not parent:
                # 父不是部门才可能出现（理论上不会），直接上提一层
                parent_id = leaf.parent_id
            else:
                parent_id = parent.id
            # 把该分类下的设备挂到其部门节点
            n = db.query(models.Device).filter(models.Device.folder_id == leaf.id).update(
                {"folder_id": parent_id}, synchronize_session=False)
            moved += n
            # 叶子无子文件夹，直接删除
            db.query(models.Folder).filter(models.Folder.id == leaf.id).delete()
            deleted += 1
        db.commit()
        print(f"  = 上提设备 {moved} 台，删除三级文件夹 {deleted} 个")
    finally:
        db.close()


# ---------------- 入口 ----------------
def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在：{DB_PATH}")
        return
    # 延迟导入 schema，避免循环
    global schemas_FolderCreate, schemas_DictionaryCreate
    from app import schemas as _s
    schemas_FolderCreate = _s.FolderCreate
    schemas_DictionaryCreate = _s.DictionaryCreate

    migrate_columns()
    migrate_tables()
    seed_asset_tree()
    seed_dictionaries()
    clean_org_tree()
    print("\n迁移 v2 完成。")


if __name__ == "__main__":
    main()
