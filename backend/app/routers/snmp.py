"""SNMP 监控路由"""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.database import get_db
from app import models, schemas
from app import snmp_client
import json

router = APIRouter(prefix="/snmp", tags=["SNMP监控"])


def _get_config_path() -> Path:
    """获取 OID 配置文件路径"""
    return Path(__file__).resolve().parents[2] / "config" / "oid_config.yaml"


def _load_config() -> dict:
    import yaml
    config_file = _get_config_path()
    if not config_file.exists():
        return {"templates": []}
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"templates": []}


def _metric_unit(metric: dict) -> str:
    """指标单位：优先取配置里的 unit，否则按类型/名称推断"""
    if metric.get("unit"):
        return metric["unit"]
    mtype = metric.get("type", "")
    # 状态类指标没有单位，必须先于名称推断判断，
    # 否则"打印机状态"会被名称里的"打印"二字误判成"页"
    if mtype in ("boolean", "string"):
        return ""
    if mtype == "percentage":
        return "%"
    name = metric.get("name", "")
    if "温度" in name:
        return "℃"
    if "页" in name or "张" in name or "打印" in name:
        return "页"
    return ""


def _normalize_value(raw: str, metric: dict) -> str:
    """把 SNMP 原始返回值转成前端友好的展示值"""
    text = (raw or "").strip()
    mtype = metric.get("type", "integer")

    if mtype == "boolean":
        # 常见状态量：1=up/正常，2=down/异常（RFC1213 ifOperStatus 等）
        mapping = {"1": "正常", "2": "异常", "3": "测试中",
                   "true": "正常", "false": "异常", "up": "正常", "down": "异常"}
        return mapping.get(text.lower(), text)

    if mtype == "percentage":
        try:
            return str(max(0, min(100, int(float(text)))))
        except ValueError:
            return text

    if mtype in ("integer", "counter", "gauge"):
        # TimeTicks 形如 "12 days, 3:04:05.00"，原样保留可读文本
        try:
            return str(int(float(text)))
        except ValueError:
            return text

    return text


def _detect_and_record_alerts(
    db: Session,
    device,
    metrics: list,
    polled_values: dict,
) -> list:
    """SNMP 阈值告警检测（N1）。

    逻辑：
    - 仅对类型为 percentage/number 的指标做数值阈值检测
    - metric 配 warning_threshold / critical_threshold + alert_direction 时触发
    - alert_direction 可选 high（默认）/ low：
        high → value >= threshold 触发（如 CPU/内存使用率）
        low  → value <= threshold 触发（如碳粉余量、电池电量）
    - 超 critical → level='critical'；仅超 warning → level='warning'
    - 同 metric 同方向的上一条未确认告警会被自动 ack（标记为已恢复），避免堆积
    - 返回本次新写入的 Alert 列表

    polled_values: {metric_name: (oid, numeric_value|None, metric_dict)}
    """
    new_alerts = []
    for metric in metrics:
        name = metric.get("name", "")
        oid, num_value, _ = polled_values.get(name, (metric.get("oid", ""), None, metric))
        if num_value is None:
            continue  # 本轮采集值不是数字，跳过阈值判断

        # boolean 类型特殊：直接以 warning_value 比对
        if metric.get("type") == "boolean":
            warn_v = metric.get("warning_value")
            if warn_v is None:
                continue
            if bool(num_value) == bool(warn_v):
                level = "warning"
                threshold_str = f"== {warn_v}"
                _check_and_record(db, device, name, oid, num_value, metric, level, threshold_str, new_alerts)
            continue

        # 数值类型：按 alert_direction 决定比较方向
        warn_t = metric.get("warning_threshold")
        crit_t = metric.get("critical_threshold")
        direction = (metric.get("alert_direction") or "high").lower()
        unit = _metric_unit(metric) or ""

        level = None
        threshold_str = ""
        try:
            if direction == "low":
                # 越低越差：value <= threshold 触发
                if crit_t is not None and num_value <= float(crit_t):
                    level = "critical"
                    threshold_str = f"<= {crit_t}"
                elif warn_t is not None and num_value <= float(warn_t):
                    level = "warning"
                    threshold_str = f"<= {warn_t}"
            else:
                # 越高兴差（默认）：value >= threshold 触发
                if crit_t is not None and num_value >= float(crit_t):
                    level = "critical"
                    threshold_str = f">= {crit_t}"
                elif warn_t is not None and num_value >= float(warn_t):
                    level = "warning"
                    threshold_str = f">= {warn_t}"
        except (TypeError, ValueError):
            continue

        if not level:
            continue

        _check_and_record(db, device, name, oid, num_value, metric, level, threshold_str, new_alerts)

    if new_alerts:
        db.commit()
    return new_alerts


def _check_and_record(
    db: Session,
    device,
    name: str,
    oid: str,
    num_value: float,
    metric: dict,
    level: str,
    threshold_str: str,
    new_alerts: list,
) -> None:
    """_detect_and_record_alerts 内部助手：写单条告警 + 关闭之前的开放告警。"""
    # 同 metric 同方向的旧告警标记为已恢复（acknowledged + auto-recovered）
    old_open = db.query(models.Alert).filter(
        models.Alert.device_id == device.id,
        models.Alert.metric_name == name,
        models.Alert.acknowledged == False,
    ).all()
    for old in old_open:
        old.acknowledged = True
        old.acknowledged_by = "auto-recovered"
        old.acknowledged_at = func.now()

    unit = _metric_unit(metric) or ""
    msg = f"{device.name or f'设备#{device.id}'} 的「{name}」={num_value}{unit} {threshold_str}"
    alert = models.Alert(
        device_id=device.id,
        device_name=device.name or f"#{device.id}",
        metric_name=name,
        metric_oid=oid or "",
        value=str(num_value),
        unit=unit,
        threshold=threshold_str,
        level=level,
        message=msg,
        acknowledged=False,
    )
    db.add(alert)
    new_alerts.append(alert)


@router.get("/templates")
def get_snmp_templates(device_type: str = None):
    """获取 SNMP 模板列表。

    传入 device_type 时，只返回适用于该设备类型的模板
    （模板未声明 device_types 视为通用模板，始终返回）。
    """
    config = _load_config()
    templates = config.get("templates", [])
    result = []
    for t in templates:
        applicable = t.get("device_types") or []
        if device_type and applicable and device_type not in applicable:
            continue
        result.append({
            "name": t["name"],
            "vendor": t.get("vendor", ""),
            "device_types": applicable,
            "metric_count": len(t.get("metrics", [])),
        })
    return {"code": 0, "data": result}


@router.get("/templates/{template_name}/metrics")
def get_template_metrics(template_name: str):
    """获取指定模板的 OID 指标列表"""
    config = _load_config()
    for t in config.get("templates", []):
        if t["name"] == template_name:
            metrics = []
            for m in t.get("metrics", []):
                metrics.append({
                    "name": m.get("name", ""),
                    "oid": m.get("oid", ""),
                    "type": m.get("type", "integer"),
                    "unit": _metric_unit(m),
                    "description": m.get("description", ""),
                })
            return {"code": 0, "data": metrics}
    return {"code": 0, "data": []}


@router.get("/metric-columns")
def get_metric_columns(db: Session = Depends(get_db)):
    """返回所有设备已勾选指标的并集，用于驱动设备列表的动态列。

    列来源是"用户勾选了什么"，而不是"已经采到了什么值"，
    因此设备刚建好还没轮询时，列也会出现（值显示为 -）。
    """
    config = _load_config()
    # 指标名 -> 单位（跨模板同名指标取首个定义）
    unit_map = {}
    for t in config.get("templates", []):
        for m in t.get("metrics", []):
            name = m.get("name", "")
            if name and name not in unit_map:
                unit_map[name] = _metric_unit(m)

    devices = db.query(models.Device).filter(
        models.Device.snmp_selected_metrics != ""
    ).all()

    ordered = []
    seen = set()
    for d in devices:
        try:
            selected = json.loads(d.snmp_selected_metrics or "[]")
        except json.JSONDecodeError:
            continue
        for name in selected:
            if name in seen:
                continue
            seen.add(name)
            ordered.append({
                "key": f"snmp_{name}",
                "metric_name": name,
                "label": name,
                "unit": unit_map.get(name, ""),
            })
    return {"code": 0, "data": ordered}


@router.get("/devices/{device_id}/metrics")
def get_device_metrics(device_id: int, db: Session = Depends(get_db)):
    """获取设备的 SNMP 监控值"""
    values = db.query(models.SnmpMetricValue).filter(models.SnmpMetricValue.device_id == device_id).all()
    return {"code": 0, "data": [
        {"id": v.id, "metric_name": v.metric_name, "metric_oid": v.metric_oid,
         "value": v.value, "unit": v.unit, "updated_at": v.updated_at.isoformat() if v.updated_at else None}
        for v in values
    ]}


@router.get("/settings")
def get_snmp_settings():
    """读取 SNMP 全局配置（默认团体名/端口/超时/是否模拟）"""
    return {"code": 0, "data": snmp_client.load_settings()}


@router.put("/settings")
def update_snmp_settings(settings: schemas.SnmpSettings):
    """更新 SNMP 全局配置"""
    data = snmp_client.save_settings(settings.model_dump())
    return {"code": 0, "message": "保存成功", "data": data}


@router.post("/devices/{device_id}/test")
def test_device_snmp(device_id: int, db: Session = Depends(get_db)):
    """连通性测试：读取 sysDescr / sysName / sysUpTime"""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        return {"code": 1, "message": "设备不存在"}
    if not (device.ip_address or "").strip():
        return {"code": 1, "message": "设备未填写 IP 地址"}

    probe = {
        "1.3.6.1.2.1.1.1.0": "系统描述",
        "1.3.6.1.2.1.1.5.0": "设备名称",
        "1.3.6.1.2.1.1.3.0": "运行时长",
    }
    conn = snmp_client.build_conn_from_device(device)
    results = snmp_client.snmp_get_many(conn, list(probe.keys()))

    items, errors = [], []
    for oid, label in probe.items():
        ok, val = results.get(oid, (False, "未返回"))
        items.append({"oid": oid, "label": label, "ok": ok, "value": val})
        if not ok:
            errors.append(f"{label}: {val}")

    success = any(i["ok"] for i in items)
    device.snmp_last_poll_at = datetime.now()
    device.snmp_last_error = "" if success else "; ".join(errors)[:500]
    db.commit()

    return {
        "code": 0 if success else 1,
        "message": "连接成功" if success else f"连接失败：{errors[0] if errors else '未知错误'}",
        "data": {"host": conn["host"], "port": conn["port"], "version": conn["version"], "items": items},
    }


@router.post("/devices/{device_id}/poll")
def poll_device_snmp(device_id: int, db: Session = Depends(get_db)):
    """手动轮询设备的 SNMP 值（只轮询用户选中的指标）"""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device or not device.snmp_template_name:
        return {"code": 1, "message": "设备未配置 SNMP 模板"}

    config = _load_config()
    template = None
    for t in config.get("templates", []):
        if t["name"] == device.snmp_template_name:
            template = t
            break

    if not template:
        return {"code": 1, "message": "模板不存在"}

    # 读取用户选中的指标。未勾选 = 不采集（不再默认打包全部）
    selected = []
    if device.snmp_selected_metrics:
        try:
            selected = json.loads(device.snmp_selected_metrics)
        except json.JSONDecodeError:
            selected = []

    if not selected:
        return {"code": 1, "message": "该设备未勾选任何监控指标，请先在设备编辑页勾选"}

    metrics_to_poll = [m for m in template.get("metrics", []) if m["name"] in selected]
    if not metrics_to_poll:
        return {"code": 1, "message": "勾选的指标不在当前模板中，请重新勾选"}

    # 清掉该设备所有旧值，避免取消勾选后残留的列一直挂在列表里
    db.query(models.SnmpMetricValue).filter(
        models.SnmpMetricValue.device_id == device_id
    ).delete(synchronize_session=False)

    settings = snmp_client.load_settings()
    simulate = bool(settings.get("simulate"))

    results = {}
    if not simulate:
        conn = snmp_client.build_conn_from_device(device, settings)
        oids = [m.get("oid", "") for m in metrics_to_poll if m.get("oid")]
        results = snmp_client.snmp_get_many(conn, oids)

    ok_count, fail_count = 0, 0
    errors = []
    polled_values = {}  # metric_name -> (value_str, is_numeric_value, numeric_value)
    for metric in metrics_to_poll:
        oid = metric.get("oid", "")
        if simulate:
            value = snmp_client.simulate_value(metric)
            ok_count += 1
        else:
            success, raw = results.get(oid, (False, "未配置 OID" if not oid else "未返回"))
            if success:
                value = _normalize_value(raw, metric)
                ok_count += 1
            else:
                value = "-"
                fail_count += 1
                errors.append(f"{metric['name']}: {raw}")

        db.add(models.SnmpMetricValue(
            device_id=device_id,
            metric_name=metric["name"],
            metric_oid=oid,
            value=value,
            unit=_metric_unit(metric),
        ))
        # 阈值告警检测：能解析为数字 + 模板设了 warning_threshold/critical_threshold 时触发
        try:
            num_value = float(value)
            polled_values[metric["name"]] = (oid, num_value, metric)
        except (TypeError, ValueError):
            polled_values[metric["name"]] = (oid, None, metric)

    device.snmp_last_poll_at = datetime.now()
    device.snmp_last_error = "" if fail_count == 0 else "; ".join(errors)[:500]
    db.commit()

    # 阈值告警检测（N1）：写 alerts 表 + 关闭已恢复的未确认告警
    try:
        new_alerts = _detect_and_record_alerts(db, device, metrics_to_poll, polled_values)
        if new_alerts:
            print(f"[snmp] device {device_id} 新增 {len(new_alerts)} 条告警")
    except Exception as _e:
        print(f"[snmp] 告警检测失败: {_e}")

    if simulate:
        return {"code": 0, "message": "轮询完成（模拟模式）",
                "data": f"已更新 {ok_count} 个指标（模拟数据）"}
    if ok_count == 0:
        return {"code": 1, "message": f"采集失败：{errors[0] if errors else '无响应'}",
                "data": {"ok": 0, "fail": fail_count}}
    if fail_count:
        return {"code": 0, "message": f"部分成功：{ok_count} 项成功，{fail_count} 项失败",
                "data": {"ok": ok_count, "fail": fail_count, "errors": errors[:5]}}
    return {"code": 0, "message": "轮询完成", "data": f"已更新 {ok_count} 个指标"}


@router.post("/poll-all")
def poll_all_devices(db: Session = Depends(get_db)):
    """批量轮询所有已配置模板且已勾选指标的设备"""
    devices = db.query(models.Device).filter(
        models.Device.snmp_template_name != "",
        models.Device.snmp_selected_metrics != ""
    ).all()
    ok = 0
    for d in devices:
        res = poll_device_snmp(d.id, db)
        if res.get("code") == 0:
            ok += 1
    return {"code": 0, "message": f"已轮询 {ok}/{len(devices)} 台设备"}


@router.get("/all-device-metrics")
def get_all_device_metrics(db: Session = Depends(get_db)):
    """获取所有设备的 SNMP 监控值（用于列表展示）"""
    values = db.query(models.SnmpMetricValue).all()
    result = {}
    for v in values:
        if v.device_id not in result:
            result[v.device_id] = []
        result[v.device_id].append({
            "metric_name": v.metric_name,
            "value": v.value,
            "unit": v.unit
        })
    return {"code": 0, "data": result}
