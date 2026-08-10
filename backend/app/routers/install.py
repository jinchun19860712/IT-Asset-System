"""安装向导路由。

仅在 install 模式下注册。提供：
- GET  /api/install/status         当前状态（已安装？/ 数据库类型？）
- POST /api/install/test           测试连接（不写库）
- POST /api/install/preview        预览：建库 + 即将建的表数量
- POST /api/install/finalize       写 db_config + 触发进程重启
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import (
    APP_DATA_DIR,
    DRIVER_REGISTRY,
    db_config,
    ensure_database,
    get_engine,
    rebuild_engine,
    test_connection,
)

router = APIRouter(prefix="/api/install", tags=["install"])


# ============================================================
# Schemas
# ============================================================
class TestRequest(BaseModel):
    db_type: str = Field(..., description="sqlite / mysql / mssql")
    db_host: str = "127.0.0.1"
    db_port: int = 0
    db_user: str = ""
    db_password: str = ""
    db_name: str = "itasset"


class FinalizeRequest(TestRequest):
    # 可选：管理员初始密码（首次登录会提示修改）
    admin_username: str = "admin"
    admin_password: str = "admin123"
    # 是否保留默认 sqlite 备份（如果之前已有）
    keep_existing_data: bool = True


# ============================================================
# 状态
# ============================================================
@router.get("/status")
def status() -> dict:
    cfg = db_config.load()
    drivers = {}
    for name, meta in DRIVER_REGISTRY.items():
        ok = True
        err = ""
        if name == "mysql":
            try:
                import pymysql  # noqa: F401
            except Exception as e:  # noqa: BLE001
                ok, err = False, str(e)
        elif name == "mssql":
            try:
                import pymssql  # noqa: F401
            except Exception as e:  # noqa: BLE001
                ok, err = False, str(e)
        drivers[name] = {
            "label": meta["label"],
            "default_port": meta["default_port"],
            "available": ok,
            "error": err,
        }
    return {
        "code": 0,
        "data": {
            "initialized": cfg.get("initialized", False),
            "db_type": cfg.get("db_type", "uninitialized"),
            "initialized_at": cfg.get("initialized_at", ""),
            "app_data_dir": str(APP_DATA_DIR),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "drivers": drivers,
        },
    }


# ============================================================
# 测试连接
# ============================================================
@router.post("/test")
def test(req: TestRequest) -> dict:
    cfg = req.model_dump()
    if cfg["db_type"] == "sqlite":
        result = test_connection(cfg)
    else:
        if not cfg.get("db_port"):
            cfg["db_port"] = DRIVER_REGISTRY[cfg["db_type"]]["default_port"]
        # 不连服务器级（先连具体库）—— 库可能还不存在，所以用 server=True
        result_server = test_connection(cfg, server=True)
        if not result_server["ok"]:
            return {"code": 1, "message": "无法连接数据库服务器", "data": result_server}
        result = {
            "ok": True,
            "version": result_server.get("version", ""),
            "driver": cfg["db_type"],
            "server_reachable": True,
        }
    return {
        "code": 0 if result["ok"] else 1,
        "message": result.get("error", "连接成功") if not result["ok"] else "连接成功",
        "data": result,
    }


# ============================================================
# 预览：建库 + 即将建的表数量
# ============================================================
@router.post("/preview")
def preview(req: TestRequest) -> dict:
    cfg = req.model_dump()
    print(f"[install-preview] 收到请求: db_type={cfg.get('db_type')}, host={cfg.get('db_host')}, port={cfg.get('db_port')}, db={cfg.get('db_name')}")
    if cfg["db_type"] != "sqlite":
        cfg["db_port"] = cfg.get("db_port") or DRIVER_REGISTRY[cfg["db_type"]]["default_port"]
    test_res = test_connection(cfg, server=(cfg["db_type"] != "sqlite"))
    print(f"[install-preview] test_connection: ok={test_res.get('ok')}, version={test_res.get('version', '')[:50] if test_res.get('version') else None}")
    if not test_res["ok"]:
        return {"code": 1, "message": "连接失败：" + test_res.get("error", ""), "data": test_res}
    ensure_res = ensure_database(cfg) if cfg["db_type"] != "sqlite" else {"ok": True, "created": False}
    print(f"[install-preview] ensure_database: ok={ensure_res.get('ok')}, created={ensure_res.get('created')}, msg={ensure_res.get('message', '')}")
    if not ensure_res["ok"]:
        return {"code": 1, "message": "建库失败：" + ensure_res.get("error", ""), "data": ensure_res}
    # 列出即将创建的表（用 metadata 反射模型）
    try:
        from app import models  # noqa: F401  注册到 Base.metadata
        from app.database import Base
        tables = [t.name for t in Base.metadata.sorted_tables]
        print(f"[install-preview] 将创建 {len(tables)} 张表: {tables[:10]}...")
    except Exception as exc:  # noqa: BLE001
        print(f"[install-preview] 模型加载失败: {exc}")
        return {"code": 1, "message": f"模型加载失败: {exc}"}
    result = {
        "code": 0,
        "message": "ok",
        "data": {
            "tables": tables,
            "table_count": len(tables),
            "test": test_res,
            "ensure": ensure_res,
        },
    }
    print(f"[install-preview] 返回成功: code=0, table_count={len(tables)}")
    return result


# ============================================================
# 真正写入配置 + 建表 + 触发重启
# ============================================================
@router.post("/finalize")
def finalize(req: FinalizeRequest) -> dict:
    cfg = {k: v for k, v in req.model_dump().items()
           if k not in ("admin_username", "admin_password", "keep_existing_data")}
    if cfg["db_type"] != "sqlite":
        cfg["db_port"] = cfg.get("db_port") or DRIVER_REGISTRY[cfg["db_type"]]["default_port"]

    # 1. 测试 + 建库
    test_res = test_connection(cfg, server=(cfg["db_type"] != "sqlite"))
    if not test_res["ok"]:
        return {"code": 1, "message": "连接失败：" + test_res.get("error", "")}
    if cfg["db_type"] != "sqlite":
        ensure_res = ensure_database(cfg)
        if not ensure_res["ok"]:
            return {"code": 1, "message": "建库失败：" + ensure_res.get("error", "")}

    # 2. 写 db_config.yaml（这一步即使后面建表失败也能保留，让用户重试）
    cfg_to_save = {
        "db_type": cfg["db_type"],
        "db_host": cfg.get("db_host", "127.0.0.1"),
        "db_port": cfg.get("db_port", 0),
        "db_user": cfg.get("db_user", ""),
        "db_password": cfg.get("db_password", ""),
        "db_name": cfg.get("db_name", "itasset"),
        "initialized": True,
        "initialized_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    db_config.save(cfg_to_save)

    # 3. 重建 engine 到新数据库，建表
    try:
        engine = rebuild_engine()
        from app import models  # noqa: F401
        from app.database import Base
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001
        # 回滚配置
        db_config.update(initialized=False, initialized_at="")
        return {"code": 1, "message": f"建表失败: {exc}（已回滚配置，请重试）"}

    # 4. 创建管理员
    try:
        from app import models
        from app.auth import hash_password
        from app.database import get_sessionmaker
        with get_sessionmaker()() as db:
            if db.query(models.User).count() == 0:
                admin = models.User(
                    username=req.admin_username,
                    display_name="系统管理员",
                    password_hash=hash_password(req.admin_password),
                    role="admin",
                    is_active=True,
                )
                db.add(admin)
                db.commit()
    except Exception as exc:  # noqa: BLE001
        return {"code": 1, "message": f"创建管理员失败: {exc}"}

    # 5. 触发进程重启（ping 一下 3 秒后用新进程替换当前进程）
    schedule_restart(delay_seconds=3)

    return {
        "code": 0,
        "message": "安装完成，服务即将重启（约 3 秒）…",
        "data": {
            "db_type": cfg["db_type"],
            "next_url": "/",
        },
    }


@router.post("/restart")
def restart_now() -> dict:
    """用户点击「立即重启」时调用：异步退出旧进程 + 启动新进程。

    PyInstaller 单 exe 模式下，_MEIPASS 临时目录被旧进程持锁。
    新进程无法复用同名 _MEIPASS。所以采用 bat 中转：
    1. 立即返回响应（前端展示倒计时）
    2. bat sleep 3 秒（让旧进程完全退出，释放 _MEIPASS 句柄）
    3. 启动新进程
    """
    import threading
    def _do():
        time.sleep(1)  # 等响应返回
        try:
            if getattr(sys, "frozen", False):
                exe_path = sys.executable
                if os.name == "nt":
                    bat = os.path.join(os.path.dirname(exe_path), "_restart.bat")
                    bat_content = (
                        "@echo off\r\n"
                        f"timeout /t 5 /nobreak >nul\r\n"
                        f'start "" "{exe_path}"\r\n'
                        f"del /f /q \"%~f0\"\r\n"
                    )
                    Path(bat).write_text(bat_content, encoding="utf-8")
                    subprocess.Popen(
                        ["cmd", "/c", bat],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        close_fds=True,
                    )
            else:
                uvicorn_cmd = [
                    sys.executable, "-m", "uvicorn",
                    "app.main:app",
                    "--host", "0.0.0.0",
                    "--port", str(int(os.environ.get("ITASSET_PORT", "8000"))),
                ]
                if os.name == "nt":
                    subprocess.Popen(["cmd", "/c", "start", "", *uvicorn_cmd], close_fds=True)
                else:
                    subprocess.Popen(uvicorn_cmd, close_fds=True)
        except Exception as exc:
            print(f"[install] 重启失败: {exc}")
            return
        time.sleep(0.5)
        import logging
        logging.shutdown()
        os._exit(0)
    threading.Thread(target=_do, daemon=True).start()
    return {"code": 0, "message": "服务正在重启…（约 6 秒）", "data": {"next_url": "/"}}


def schedule_restart(delay_seconds: int = 3) -> None:
    """install 完成后的重启方案：写一个「等待旧进程退出 → 启动新进程」的 bat。

    解决时序问题：
    - 直接 Popen 新 exe 会在端口被旧进程占用时立即撞端口失败
    - 让新 exe 等几秒再启动（旧进程 schedule_restart 后会立即 os._exit(0)）
    """
    import threading
    try:
        def _do_restart():
            # 1. 等前端拿到响应
            time.sleep(delay_seconds)
            # 2. 退出旧进程，立即释放端口
            print(f"[install] 安装完成，正在重启服务...")
            print(f"[install] 等待旧进程退出后启动新进程")
            # 3. 启动一个独立批处理：等几秒 → 启动新 exe
            try:
                if getattr(sys, "frozen", False):
                    exe_path = sys.executable
                    if os.name == "nt":
                        # 写一个临时 bat，延迟启动新 exe
                        bat_dir = os.path.dirname(exe_path)
                        bat = os.path.join(bat_dir, "_restart.bat")
                        bat_content = (
                            "@echo off\r\n"
                            f"timeout /t 4 /nobreak >nul\r\n"
                            f'start "" "{exe_path}"\r\n'
                            f"del /f /q \"%~f0\"\r\n"
                        )
                        Path(bat).write_text(bat_content, encoding="utf-8")
                        print(f"[install] 写入重启脚本: {bat}")
                        subprocess.Popen(
                            ["cmd", "/c", bat],
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            close_fds=True,
                        )
                        print(f"[install] 已调度重启脚本")
                else:
                    uvicorn_cmd = [
                        sys.executable, "-m", "uvicorn",
                        "app.main:app",
                        "--host", "0.0.0.0",
                        "--port", str(int(os.environ.get("ITASSET_PORT", "8000"))),
                    ]
                    if os.name == "nt":
                        subprocess.Popen(
                            ["cmd", "/c", "start", "", *uvicorn_cmd],
                            close_fds=True,
                        )
                    else:
                        subprocess.Popen(uvicorn_cmd, close_fds=True)
            except Exception as exc:
                print(f"[install] 调度重启失败: {exc}")
                return
            # 4. 退出旧进程（释放端口，新进程会接管）
            time.sleep(0.5)
            print(f"[install] 旧进程退出")
            # 关闭所有 logging 句柄，让新进程能覆盖 server.log
            import logging
            logging.shutdown()
            os._exit(0)

        threading.Thread(target=_do_restart, daemon=True).start()
    except Exception as exc:  # noqa: BLE001
        print(f"[install] 自动重启调度失败: {exc}")
