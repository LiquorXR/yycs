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
    """微信支付结果回调：验签 + AES-GCM 解密 + 幂等 + 事务内恰好一次解锁报告。

    官方排错：日志需携带回调 Request-ID，便于向微信侧提供定位。
    """
    raw_body = await request.body()
    # 提取回调 Request-ID 用于链路追踪（大小写不敏感）
    request_id = request.headers.get("Request-ID") or request.headers.get("request-id") or request.headers.get("Wechatpay-Request-Id") or request.headers.get("wechatpay-request-id")
    if request_id:
        logger.info("收到微信支付回调 request-id=%s", request_id)
    result, message = pay_service.handle_pay_notify(db, request.headers, raw_body)
    if result == "SUCCESS":
        if request_id:
            logger.info("支付回调返回 SUCCESS request-id=%s", request_id)
        return JSONResponse({"code": "SUCCESS"})
    logger.warning("支付回调返回 FAIL：%s request-id=%s", message, request_id)
    return JSONResponse({"code": "FAIL", "message": message})