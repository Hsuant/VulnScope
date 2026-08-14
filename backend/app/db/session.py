"""数据库会话工厂与 FastAPI 依赖。

通过配置切换 SQLite / MySQL 后端，引擎在模块导入时创建。
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_connect_args: dict = {}
if settings.DB_BACKEND == "sqlite":
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url(),
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 请求级依赖注入。

    每个请求独立获取会话，请求结束时自动关闭。
    异常时自动回滚，确保数据库连接回到池中。

    Yields:
        SQLAlchemy Session 实例。
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
