"""SNMP 采集客户端（基于 pysnmp 7.x）

封装真实 SNMP GET 采集，支持 v1 / v2c（community）与 v3（USM 认证加密）。
FastAPI 的同步路由通过 `snmp_get_many()` 调用，内部用 asyncio 事件循环执行。

全局默认参数存放于 backend/config/snmp_config.json，
设备未单独配置时回退到全局默认；simulate=true 时整体走模拟值（无真实设备的演示模式）。
"""
import asyncio
import json
import random
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "snmp_config.json"

DEFAULT_SETTINGS = {
    "simulate": True,          # 默认演示模式，接入真实设备后在"系统设置"里关闭
    "default_version": "v2c",
    "default_port": 161,
    "default_community": "public",
    "timeout": 2.0,
    "retries": 1,
}


# ---------------- 配置读写 ----------------

def load_settings() -> dict:
    """读取 SNMP 全局配置，文件不存在时自动创建默认配置"""
    if not CONFIG_PATH.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    return merged


def save_settings(settings: dict) -> dict:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in (settings or {}).items() if k in DEFAULT_SETTINGS})
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


# ---------------- 模拟值 ----------------

def simulate_value(metric: dict) -> str:
    """演示模式下按指标类型生成合理的假数据"""
    mtype = (metric or {}).get("type", "integer")
    if mtype == "boolean":
        return random.choice(["正常", "正常", "异常"])
    if mtype == "percentage":
        return str(random.randint(5, 95))
    if mtype == "counter":
        return str(random.randint(1000, 50000))
    if mtype == "string":
        return "OK"
    return str(random.randint(0, 100))


# ---------------- 真实采集 ----------------

def _auth_protocol(name: str):
    from pysnmp.hlapi.v3arch.asyncio import (
        usmNoAuthProtocol, usmHMACMD5AuthProtocol, usmHMACSHAAuthProtocol,
        usmHMAC192SHA256AuthProtocol, usmHMAC384SHA512AuthProtocol,
    )
    return {
        "": usmNoAuthProtocol,
        "none": usmNoAuthProtocol,
        "md5": usmHMACMD5AuthProtocol,
        "sha": usmHMACSHAAuthProtocol,
        "sha256": usmHMAC192SHA256AuthProtocol,
        "sha512": usmHMAC384SHA512AuthProtocol,
    }.get((name or "").strip().lower(), usmHMACSHAAuthProtocol)


def _priv_protocol(name: str):
    from pysnmp.hlapi.v3arch.asyncio import (
        usmNoPrivProtocol, usmDESPrivProtocol, usmAesCfb128Protocol,
        usmAesCfb192Protocol, usmAesCfb256Protocol,
    )
    return {
        "": usmNoPrivProtocol,
        "none": usmNoPrivProtocol,
        "des": usmDESPrivProtocol,
        "aes": usmAesCfb128Protocol,
        "aes128": usmAesCfb128Protocol,
        "aes192": usmAesCfb192Protocol,
        "aes256": usmAesCfb256Protocol,
    }.get((name or "").strip().lower(), usmAesCfb128Protocol)


def _build_auth_data(conn: dict):
    """根据连接参数构造 CommunityData 或 UsmUserData"""
    from pysnmp.hlapi.v3arch.asyncio import CommunityData, UsmUserData

    version = (conn.get("version") or "v2c").lower()
    if version == "v3":
        user = conn.get("v3_user") or ""
        if not user:
            raise ValueError("SNMPv3 缺少用户名")
        auth_key = conn.get("v3_auth_key") or None
        priv_key = conn.get("v3_priv_key") or None
        kwargs = {}
        if auth_key:
            kwargs["authKey"] = auth_key
            kwargs["authProtocol"] = _auth_protocol(conn.get("v3_auth_protocol"))
        if priv_key:
            kwargs["privKey"] = priv_key
            kwargs["privProtocol"] = _priv_protocol(conn.get("v3_priv_protocol"))
        return UsmUserData(user, **kwargs)

    community = conn.get("community") or "public"
    # mpModel: 0=v1, 1=v2c
    return CommunityData(community, mpModel=0 if version == "v1" else 1)


async def _async_get(conn: dict, oids: List[str]) -> Dict[str, Tuple[bool, str]]:
    """异步执行一批 OID 的 SNMP GET，返回 {oid: (成功?, 值或错误信息)}"""
    from pysnmp.hlapi.v3arch.asyncio import (
        SnmpEngine, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, get_cmd,
    )

    host = conn.get("host") or ""
    port = int(conn.get("port") or 161)
    timeout = float(conn.get("timeout") or 2.0)
    retries = int(conn.get("retries") or 1)

    result: Dict[str, Tuple[bool, str]] = {}
    engine = SnmpEngine()
    try:
        auth_data = _build_auth_data(conn)
        target = await UdpTransportTarget.create((host, port), timeout=timeout, retries=retries)
        context = ContextData()

        for oid in oids:
            try:
                error_indication, error_status, error_index, var_binds = await get_cmd(
                    engine, auth_data, target, context,
                    ObjectType(ObjectIdentity(oid)),
                )
                if error_indication:
                    result[oid] = (False, str(error_indication))
                elif error_status:
                    result[oid] = (False, f"{error_status.prettyPrint()} at {error_index}")
                elif var_binds:
                    name, val = var_binds[0]
                    text = val.prettyPrint()
                    if text in ("No Such Object currently exists at this OID",
                                "No Such Instance currently exists at this OID"):
                        result[oid] = (False, text)
                    else:
                        result[oid] = (True, text)
                else:
                    result[oid] = (False, "空响应")
            except Exception as exc:  # 单个 OID 失败不影响其它 OID
                result[oid] = (False, f"{type(exc).__name__}: {exc}")
    finally:
        try:
            engine.close_dispatcher()
        except Exception:
            pass
    return result


def _run_async(coro):
    """在同步上下文中运行协程；若当前线程已有运行中的事件循环则另起线程执行"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    box = {}

    def _worker():
        try:
            box["result"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001
            box["error"] = exc

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]
    return box.get("result", {})


def snmp_get_many(conn: dict, oids: List[str]) -> Dict[str, Tuple[bool, str]]:
    """同步入口：批量 SNMP GET。

    conn: {host, port, version, community, v3_user, v3_auth_protocol, v3_auth_key,
           v3_priv_protocol, v3_priv_key, timeout, retries}
    返回 {oid: (成功?, 值或错误信息)}；整体失败时所有 OID 都标记为失败。
    """
    oids = [o for o in (oids or []) if o]
    if not oids:
        return {}
    if not conn.get("host"):
        return {oid: (False, "设备未填写 IP 地址") for oid in oids}
    try:
        return _run_async(_async_get(conn, oids))
    except Exception as exc:  # noqa: BLE001
        msg = f"{type(exc).__name__}: {exc}"
        return {oid: (False, msg) for oid in oids}


def build_conn_from_device(device, settings: Optional[dict] = None) -> dict:
    """把设备对象上的 SNMP 参数与全局默认合并成连接参数"""
    s = settings or load_settings()
    return {
        "host": (getattr(device, "ip_address", "") or "").strip(),
        "port": getattr(device, "snmp_port", None) or s["default_port"],
        "version": (getattr(device, "snmp_version", "") or s["default_version"]),
        "community": (getattr(device, "snmp_community", "") or s["default_community"]),
        "v3_user": getattr(device, "snmp_v3_user", "") or "",
        "v3_auth_protocol": getattr(device, "snmp_v3_auth_protocol", "") or "SHA",
        "v3_auth_key": getattr(device, "snmp_v3_auth_key", "") or "",
        "v3_priv_protocol": getattr(device, "snmp_v3_priv_protocol", "") or "AES",
        "v3_priv_key": getattr(device, "snmp_v3_priv_key", "") or "",
        "timeout": s["timeout"],
        "retries": s["retries"],
    }
