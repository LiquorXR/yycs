"""支付回调路由。

协议例外：不遵循统一响应信封，按收钱吧推送语义返回纯文本
`"success"` / `"fail"`（失败触发上游重试）。
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
    """微信小店订单支付成功推送：RSA 验签 + eventId 幂等 + 事务内恰好一次解锁报告。"""
    raw_body = await request.body()
    logger.info("收到微信小店支付推送 bytes=%s", len(raw_body))
    result, message = pay_service.handle_pay_notify(db, raw_body)
    if result == "success":
        logger.info("支付推送返回 success")
        return PlainTextResponse("success")
    logger.warning("支付推送返回 fail：%s", message)
    return PlainTextResponse("fail")


@router.post("/api/pay/refund-notify", response_model=None)
async def refund_notify(request: Request, db: Session = Depends(get_db)) -> PlainTextResponse:
    """微信小店退款状态变更推送：RSA 验签 + 只记录可查（不改订单主状态，人工核账）。"""
    raw_body = await request.body()
    logger.info("收到微信小店退款推送 bytes=%s", len(raw_body))
    result, message = pay_service.handle_refund_notify(db, raw_body)
    if result == "success":
        logger.info("退款推送返回 success")
        return PlainTextResponse("success")
    logger.warning("退款推送返回 fail：%s", message)
    return PlainTextResponse("fail")
