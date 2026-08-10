"""数据库连接层（SQLite 单库，开发/演示模式）。

零配置：数据存放在 backend/data/it_asset.db。
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ============================================================
# 路径
# ============================================================
# 运行时数据目录：默认 backend/data/
APP_DATA_DIR = Path(
    os.environ.get("ITASSET_DATA_DIR")
    or str(Path(__file__).resolve().parents[1] / "data")
)
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DATA_DIR / "it_asset.db"
UPLOADS_DIR = APP_DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
SECRETS_DIR = APP_DATA_DIR / "secrets"
SECRETS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Engine / Session
# ============================================================
Base = declarative_base()

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sessionmaker() -> sessionmaker:
    return SessionLocal


def init_engine():
    """兼容旧调用：返回已创建的 engine。"""
    return engine


def rebuild_engine():
    """兼容旧调用：返回已创建的 engine。"""
    return engine
