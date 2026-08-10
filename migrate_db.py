"""数据库迁移脚本（幂等，可重复执行）

修复 / 新增内容：
1. folders   : is_department、department_name 字段
2. folders   : 回填空的 path 字段（历史数据由 init_db.py 直接写库，未生成 path，
               导致「按文件夹筛选子孙设备」退化为返回全部设备）
3. devices   : snmp_selected_metrics、机柜上架字段
4. racks     : 新建机柜表
5. device_ports : 新建 / 补齐端口扩展字段
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backend", "data", "it_asset.db")


def table_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [c[1] for c in cursor.fetchall()]


def table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def add_column(cursor, table, column, ddl):
    if column not in table_columns(cursor, table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        print(f"  + {table}.{column}")
        return True
    return False


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在：{DB_PATH}")
        print("请先运行：cd backend && python init_db.py")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    changed = 0

    print("[1/5] folders 表字段")
    changed += add_column(cur, "folders", "is_department", "BOOLEAN DEFAULT 0")
    changed += add_column(cur, "folders", "department_name", "VARCHAR(100) DEFAULT ''")

    print("[2/5] devices 表字段")
    for col, ddl in [
        ("snmp_selected_metrics", "TEXT DEFAULT ''"),
        ("rack_id", "INTEGER"),
        ("rack_position", "INTEGER"),
        ("rack_units", "INTEGER DEFAULT 1"),
        ("rack_face", "VARCHAR(10) DEFAULT 'front'"),
        ("remark", "TEXT DEFAULT ''"),
    ]:
        changed += add_column(cur, "devices", col, ddl)

    print("[3/5] racks 表")
    if not table_exists(cur, "racks"):
        cur.execute("""
            CREATE TABLE racks (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                u_height INTEGER DEFAULT 42,
                location VARCHAR(200) DEFAULT '',
                row_label VARCHAR(50) DEFAULT '',
                folder_id INTEGER,
                description TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(folder_id) REFERENCES folders (id)
            )
        """)
        print("  + 创建 racks 表")
        changed += 1
    else:
        print("  = racks 表已存在")

    print("[4/5] device_ports 表")
    if not table_exists(cur, "device_ports"):
        cur.execute("""
            CREATE TABLE device_ports (
                id INTEGER PRIMARY KEY,
                device_id INTEGER NOT NULL,
                port_name VARCHAR(100) NOT NULL,
                port_type VARCHAR(20) DEFAULT 'downlink',
                connection_type VARCHAR(20) DEFAULT 'access',
                peer_device_id INTEGER,
                peer_port_name VARCHAR(100) DEFAULT '',
                lag_group VARCHAR(50) DEFAULT '',
                lag_mode VARCHAR(20) DEFAULT '',
                stack_id VARCHAR(20) DEFAULT '',
                vlan_info VARCHAR(200) DEFAULT '',
                port_speed VARCHAR(30) DEFAULT '',
                description TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(device_id) REFERENCES devices (id),
                FOREIGN KEY(peer_device_id) REFERENCES devices (id)
            )
        """)
        print("  + 创建 device_ports 表")
        changed += 1
    else:
        for col, ddl in [
            ("lag_mode", "VARCHAR(20) DEFAULT ''"),
            ("stack_id", "VARCHAR(20) DEFAULT ''"),
            ("vlan_info", "VARCHAR(200) DEFAULT ''"),
            ("port_speed", "VARCHAR(30) DEFAULT ''"),
            ("sort_order", "INTEGER DEFAULT 0"),
        ]:
            changed += add_column(cur, "device_ports", col, ddl)

    conn.commit()

    print("[5/5] 回填 folders.path")
    cur.execute("SELECT id, parent_id, path FROM folders")
    rows = cur.fetchall()
    parent_of = {r[0]: r[1] for r in rows}
    current_path = {r[0]: r[2] for r in rows}

    def build_path(fid, depth=0):
        if depth > 50:
            return f"/{fid}/"
        pid = parent_of.get(fid)
        if pid and pid in parent_of:
            return f"{build_path(pid, depth + 1)}{fid}/"
        return f"/{fid}/"

    fixed = 0
    for fid in parent_of:
        correct = build_path(fid)
        if current_path.get(fid) != correct:
            cur.execute("UPDATE folders SET path=? WHERE id=?", (correct, fid))
            fixed += 1
    conn.commit()
    print(f"  = 修复 {fixed} 个文件夹路径（共 {len(rows)} 个）")

    # 把二级目录标记为部门（仅在完全没有任何部门标记时执行一次）
    cur.execute("SELECT COUNT(*) FROM folders WHERE is_department=1")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM folders WHERE parent_id IS NULL")
        roots = [r[0] for r in cur.fetchall()]
        if roots:
            placeholders = ",".join("?" * len(roots))
            cur.execute(
                f"UPDATE folders SET is_department=1 WHERE parent_id IN ({placeholders})",
                roots)
            print(f"  = 已将 {cur.rowcount} 个二级目录标记为部门")
            conn.commit()

    conn.close()
    print(f"\n迁移完成，共变更 {changed} 处结构。")


if __name__ == "__main__":
    main()
