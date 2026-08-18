"""支付回调路由。

协议例外：不遵循统一响应信封，按微信支付回调协议返回
`{"code":"SUCCESS"}` / `{"code":"FAIL","message":"..."}`（见 API 规范 §2.10）。
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import pay_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pay"])


@router.post("/api/pay/notify", response_model=None)
async def pay_notify(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """微信支付结果回调：验签 + AES-GCM 解密 + 幂等 + 事务内恰好一次解锁报告。"""
    raw_body = await request.body()
    result, message = pay_service.handle_pay_notify(db, request.headers, raw_body)
    if result == "SUCCESS":
        return JSONResponse({"code": "SUCCESS"})
    logger.warning("支付回调返回 FAIL：%s", message)
    return JSONResponse({"code": "FAIL", "message": message})