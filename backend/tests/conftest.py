"""测试基础设施：测试客户端 + 临时文件 SQLite 数据库 + 种子数据。"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# 在导入 app 之前设置测试环境变量
os.environ["VULNSCOPE_APP_ENV"] = "test"
os.environ["VULNSCOPE_SECRET_KEY"] = "test-secret-key-32-bytes-long-for-hs256"
os.environ["VULNSCOPE_SEED_ADMIN_USERNAME"] = "admin"
os.environ["VULNSCOPE_SEED_ADMIN_PASSWORD"] = "admin123"

# 用临时文件 SQLite，避免多引擎连接不一致
_db_fd, _db_path = tempfile.mkstemp(suffix=".test.db")
os.environ["VULNSCOPE_DB_BACKEND"] = "sqlite"
os.environ["VULNSCOPE_DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.auth_service import seed_admin, seed_roles


@pytest.fixture(autouse=True)
def _test_db() -> Generator[Session, None, None]:
    """每个测试用例：建表 → 种子数据 → 提供会话 → 清库。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_admin(db)
        db.commit()
        yield db
    finally:
        db.close()
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


@pytest.fixture
def db(_test_db: Session) -> Session:
    """基于 SessionLocal 的 DB 会话（已含种子数据）。"""
    return _test_db


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI 测试客户端，DB 依赖注入覆盖为测试会话。"""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db

    from app.api import deps

    app.dependency_overrides[deps.get_db] = _override_get_db
    with TestClient(app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client: TestClient) -> str:
    """登录 admin 获取 access token。"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["data"]["access_token"]


@pytest.fixture
def auth_header(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
