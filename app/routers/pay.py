"""支付回调路由。

协议例外：不遵循统一响应信封，按收钱吧回调协议返回纯文本
`"success"` / `"fail"`（失败触发收钱吧 1s/5s/30s/600s 重试）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import pay_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pay"])


@router.post("/api/pay/notify", response_model=None)
async def pay_notify(request: Request, db: Session = Depends(get_db)) -> PlainTextResponse:
    """收钱吧支付结果回调：RSA 验签 + 幂等 + 事务内恰好一次解锁报告。"""
    raw_body = await request.body()
    logger.info("收到收钱吧支付回调 bytes=%s", len(raw_body))
    result, message = pay_service.handle_pay_notify(db, request.headers, raw_body)
    if result == "success":
        logger.info("支付回调返回 success")
        return PlainTextResponse("success")
    logger.warning("支付回调返回 fail：%s", message)
    return PlainTextResponse("fail")
