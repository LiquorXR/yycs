"""健康检查路由：探活 + 配置态（wxpayReady/reconcileEnabled）+ 对账运行态（读 DB，多 worker 一致）。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.response import ok_response
from app.db.session import get_db
from app.models.idempotency import IdempotencyRecord
from app.services import pay_service
from app.services.reconcile import _METRICS_KEY

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
def health_check(db: Session = Depends(get_db)) -> dict:
    """健康检查。

    配置态：reconcileEnabled/wxpayReady 反映 .env 配置（真实 wx_ready() 六项齐全判断）；
    运行态：lastReconcileAt/Summary 由持锁 worker 写入 DB，任何 worker 读取一致；
    两者均 null 时说明商户未配置或未到首轮，可一次 curl 定位。
    """
    metrics: dict | None = None
    try:
        record = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == _METRICS_KEY).first()
        if record is not None:
            metrics = json.loads(record.response)
    except Exception:  # noqa: BLE001  探活接口永不 5xx
        metrics = None

    return ok_response(
        {
            "status": "ok",
            "dbSizeBytes": _db_size_bytes(),
            "reconcileEnabled": settings.RECONCILE_ENABLED,
            "wxpayReady": pay_service.wx_ready(),
            "lastReconcileAt": metrics.get("at") if metrics else None,
            "lastReconcileSummary": metrics.get("summary") if metrics else None,
        }
    )