"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}
