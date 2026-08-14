"""健康检查。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)) -> dict:
    """存活 + 数据库连通性探测。"""
    db.execute(text("SELECT 1"))
    return ok({"status": "ok", "db": "up"}, request)
