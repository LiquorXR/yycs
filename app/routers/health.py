"""健康检查路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings
from app.core.response import ok_response
from app.services import reconcile as reconcile_service

router = APIRouter(tags=["health"])


def _db_size_bytes() -> int | None:
    """SQLite 数据库文件大小（字节）；非 SQLite 或读取失败返回 None。"""
    url = settings.DATABASE_URL
    if not url.startswith("sqlite:///"):
        return None
    try:
        return Path(url[len("sqlite:///"):]).resolve().stat().st_size
    except OSError:
        return None


@router.get("/api/health")
def health_check() -> dict:
    return ok_response(
        {
            "status": "ok",
            "dbSizeBytes": _db_size_bytes(),
            "lastReconcileAt": reconcile_service.last_reconcile_at,
            "lastReconcileSummary": reconcile_service.last_reconcile_summary,
        }
    )
