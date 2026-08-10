"""配置管理路由"""
from fastapi import APIRouter
import os
import yaml
import json
from pathlib import Path

router = APIRouter(prefix="/config", tags=["配置管理"])

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _ensure_config_files():
    """确保配置文件存在，不存在则创建默认模板"""
    CONFIG_DIR.mkdir(exist_ok=True)

    # 默认状态配置
    status_file = CONFIG_DIR / "status_config.json"
    if not status_file.exists():
        default_status = {
            "statuses": [
                {"name": "在用", "color": "#67C23A", "sort_order": 1},
                {"name": "维修", "color": "#E6A23C", "sort_order": 2},
                {"name": "淘汰", "color": "#909399", "sort_order": 3},
                {"name": "闲置", "color": "#409EFF", "sort_order": 4}
            ]
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(default_status, f, ensure_ascii=False, indent=2)

    # 默认OID配置
    oid_file = CONFIG_DIR / "oid_config.yaml"
    if not oid_file.exists():
        default_oid = {
            "templates": [
                {
                    "name": "通用打印机模板",
                    "vendor": "通用",
                    "metrics": [
                        {"name": "设备状态", "oid": "1.3.6.1.2.1.25.3.2.1.5.1", "type": "integer", "description": "1=正常, 2=警告, 3=错误"},
                        {"name": "缺纸状态", "oid": "1.3.6.1.2.1.43.8.2.1.10.1", "type": "boolean", "warning_value": True, "description": "True=缺纸"},
                        {"name": "黑色墨粉余量", "oid": "1.3.6.1.2.1.43.11.1.1.9.1.1", "type": "percentage", "warning_threshold": 20, "critical_threshold": 5},
                        {"name": "A4总打印页数", "oid": "1.3.6.1.2.1.43.10.2.1.4.1.1", "type": "counter"}
                    ]
                }
            ]
        }
        with open(oid_file, "w", encoding="utf-8") as f:
            yaml.dump(default_oid, f, allow_unicode=True, sort_keys=False)

    # 默认LDAP配置
    ldap_file = CONFIG_DIR / "ldap_config.json"
    if not ldap_file.exists():
        default_ldap = {
            "server": "ldap://192.168.1.100",
            "port": 389,
            "use_ssl": False,
            "base_dn": "dc=company,dc=com",
            "admin_dn": "cn=admin,dc=company,dc=com",
            "admin_password": "",
            "user_filter": "(objectClass=person)",
            "ou_filter": "(objectClass=organizationalUnit)",
            "sync_enabled": False,
            "sync_interval": "0 2 * * *"
        }
        with open(ldap_file, "w", encoding="utf-8") as f:
            json.dump(default_ldap, f, ensure_ascii=False, indent=2)


@router.get("/status")
def get_status_config():
    _ensure_config_files()
    with open(CONFIG_DIR / "status_config.json", "r", encoding="utf-8") as f:
        return {"code": 0, "data": json.load(f)}


@router.post("/status")
def update_status_config(config: dict):
    _ensure_config_files()
    with open(CONFIG_DIR / "status_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return {"code": 0, "message": "保存成功"}


@router.get("/oid")
def get_oid_config():
    _ensure_config_files()
    with open(CONFIG_DIR / "oid_config.yaml", "r", encoding="utf-8") as f:
        return {"code": 0, "data": yaml.safe_load(f)}


@router.post("/oid")
def update_oid_config(config: dict):
    _ensure_config_files()
    with open(CONFIG_DIR / "oid_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)
    return {"code": 0, "message": "保存成功"}


@router.get("/ldap")
def get_ldap_config():
    _ensure_config_files()
    with open(CONFIG_DIR / "ldap_config.json", "r", encoding="utf-8") as f:
        return {"code": 0, "data": json.load(f)}


@router.post("/ldap")
def update_ldap_config(config: dict):
    _ensure_config_files()
    with open(CONFIG_DIR / "ldap_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return {"code": 0, "message": "保存成功"}


@router.post("/ldap/test")
def test_ldap_connection(config: dict):
    """测试LDAP连接"""
    try:
        from ldap3 import Server, Connection, ALL
        server = Server(config.get("server"), port=config.get("port", 389), get_info=ALL)
        conn = Connection(
            server,
            user=config.get("admin_dn"),
            password=config.get("admin_password"),
            auto_bind=True
        )
        conn.unbind()
        return {"code": 0, "message": "连接成功"}
    except Exception as e:
        return {"code": 1, "message": f"连接失败: {str(e)}"}
