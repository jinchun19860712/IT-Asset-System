"""FastAPI 主入口（开发模式）。

运行方式：
- 后端：uvicorn app.main:app --reload  （或 python app.py）
- 前端：在 frontend/ 目录 npm run dev（vite 开发服务器，代理 /api 到 8000）

前端构建产物 frontend/dist 存在时，本服务也会一并托管（便于脱离 vite 直接访问）。
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import APP_DATA_DIR, init_engine


# ============================================================
# 启动期初始化
# ============================================================
init_engine()
from app.database import engine, Base, SessionLocal  # noqa: F401

Base.metadata.create_all(bind=engine)

try:
    from app.db_migrate import auto_add_missing_columns, auto_add_indexes
    _added = auto_add_missing_columns(engine, Base)
    if _added:
        print(f"[migrate] 自动新增列: {', '.join(_added)}")
    _indexed = auto_add_indexes(engine)
    if _indexed:
        print(f"[migrate] 新增索引: {', '.join(_indexed)}")
except Exception as _e:
    print(f"[migrate] 自动加列/索引失败: {_e}")

try:
    from app.db_migrate import (
        migrate_device_types_to_dict,
        migrate_preset_device_types_to_dict,
    )
    _imported = migrate_device_types_to_dict(engine, SessionLocal)
    if _imported:
        print(f"[migrate] 已将 {len(_imported)} 个设备类型导入字典: {_imported}")
    _imported_preset = migrate_preset_device_types_to_dict(engine, SessionLocal)
    if _imported_preset:
        print(f"[migrate] 已将 {len(_imported_preset)} 个预置设备类型导入字典: {_imported_preset}")
except Exception as _e:
    print(f"[migrate] 设备类型字典导入失败: {_e}")

try:
    from app.utils.secret_box import secret_box
    secret_box.bootstrap()
except Exception as _e:
    print(f"[secret] 初始化失败：{_e}")


# ============================================================
# 应用对象
# ============================================================
app = FastAPI(
    title="IT资产管理系统",
    description="黄山健康职业学院IT资产管理",
    version="1.0.0",
)

# ============================================================
# CORS
# ============================================================
_ALLOWED_ORIGINS = os.environ.get(
    'ITASSET_CORS_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,'
    'http://localhost:8000,http://127.0.0.1:8000'
).split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# Auth 中间件
# ============================================================
PUBLIC_PATH_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/logout",
    "/health",
    "/static",
    "/favicon.ico",
)
PUBLIC_EXACT_PATHS = {"/", ""}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path in PUBLIC_EXACT_PATHS or any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES):
            return await call_next(request)
        from app.auth import SESSION_COOKIE, get_session
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "未登录或登录已过期"},
            )
        sess = get_session(token)
        if not sess:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "登录已过期，请重新登录"},
            )
        return await call_next(request)


app.add_middleware(AuthMiddleware)


# ============================================================
# 路由注册
# ============================================================
from app.routers import (
    folders, devices, custom_fields, status, config,
    non_device_items, snmp, racks, import_export,
    dictionaries, softwares, contracts, product_types,
    auth, alerts, audit_logs,
)

app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(import_export.router)
app.include_router(devices.router)
app.include_router(custom_fields.router)
app.include_router(status.router)
app.include_router(config.router)
app.include_router(non_device_items.router)
app.include_router(snmp.router)
app.include_router(racks.router)
app.include_router(racks.topology_router)
app.include_router(dictionaries.router)
app.include_router(softwares.router)
app.include_router(contracts.router)
app.include_router(product_types.router)
app.include_router(alerts.router)
app.include_router(audit_logs.router)


# ============================================================
# 静态前端托管（frontend/dist 存在时）
# ============================================================
frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    print(f"[startup] serving frontend from {frontend_dir}")

    @app.get("/")
    def serve_index():
        return FileResponse(frontend_dir / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api"):
            return JSONResponse({"code": 404, "message": "Not Found"}, status_code=404)
        target = frontend_dir / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dir / "index.html")

    assets_dir = frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
else:
    print(f"[startup] frontend dist 未找到（{frontend_dir}），进入 API-only 模式。"
          f"前端请用 vite dev server: cd frontend && npm run dev")


@app.get("/health")
def health_check():
    return {"code": 0, "status": "healthy"}


# ============================================================
# 启动事件：初始化默认管理员 + 修复文件夹路径
# ============================================================
@app.on_event("startup")
def _startup_init():
    from app import crud, models
    from app.auth import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, hash_password
    from app.database import get_sessionmaker
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            admin = models.User(
                username=DEFAULT_ADMIN_USERNAME,
                display_name="系统管理员",
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"[startup] 已创建默认管理员账号 {DEFAULT_ADMIN_USERNAME!r}，"
                  f"初始密码 {DEFAULT_ADMIN_PASSWORD!r}")
        try:
            fixed = crud.rebuild_all_folder_paths(db)
            if fixed:
                print(f"[startup] 已修复 {fixed} 个文件夹路径")
        except Exception as e:
            print(f"[startup] 修复文件夹路径失败: {e}")
    except Exception as e:
        print(f"[startup] 启动初始化失败: {e}")
    finally:
        db.close()


@app.get("/api-root")
def root():
    return {
        "code": 0,
        "message": "IT资产管理系统API运行中",
        "docs": "/docs",
    }
