"""支付服务：统一下单、回调处理（验签/解密/幂等/恰好一次解锁）、退款、查单推进。

核心不变量：
- 金额一律整数分，回调金额与订单精确比对，不一致拒绝（防改价/防串单）。
- 恰好一次：订单状态 CAS `UPDATE ... WHERE state='CREATED'`，并发回调仅一个获胜者；
  已进入支付链的状态重复回调直接返回成功（幂等，不重复解锁）。
- 未配置微信支付时优雅降级：ensure_payment 返回全 null，订单仍可创建。
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.core.timeutil import utcnow
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.product import Product
from app.models.refund import Refund
from app.models.report import Report
from app.services import wechatpay
from app.services.wechatpay import WechatPayError

logger = logging.getLogger(__name__)

# 已进入支付/交付链路的订单状态：重复回调视为已处理（幂等成功）
_PAID_CHAIN_STATES = {
    OrderState.PAID.value,
    OrderState.UNLOCKED.value,
    OrderState.DELIVERED.value,
    OrderState.ADDED_WECOM.value,
    OrderState.REFUNDING.value,
    OrderState.REFUNDED.value,
}

_PAYMENT_DESC = "振凡命理·测算服务"


def wx_ready() -> bool:
    return wechatpay.client.is_ready


def ensure_payment(db: Session, order: Order, client_ip: str | None) -> dict:
    """统一下单，返回 {payType, payUrl, codeUrl}。

    支付配置缺失或上游失败时优雅降级返回全 null（订单仍可创建）；
    auto/h5 拉起失败自动降级 Native 扫码。
    """
    if not wx_ready():
        return {"payType": None, "payUrl": None, "codeUrl": None}

    product = db.query(Product).filter(Product.id == order.product_id).first()
    description = product.name if product else _PAYMENT_DESC
    method = order.pay_type or "h5"

    if method in ("auto", "h5"):
        try:
            pay_url = wechatpay.client.create_h5_payment(
                order.out_trade_no, order.amount, description, client_ip or "127.0.0.1"
            )
            if pay_url:
                return {"payType": "h5", "payUrl": pay_url, "codeUrl": None}
        except WechatPayError as e:
            logger.warning("H5 下单失败（%s），降级 Native：order_no=%s", e, order.order_no)

    try:
        code_url = wechatpay.client.create_native_payment(order.out_trade_no, order.amount, description)
        if code_url:
            return {"payType": "native", "payUrl": None, "codeUrl": code_url}
    except WechatPayError as e:
        logger.error("Native 下单失败：order_no=%s, %s", order.order_no, e)

    return {"payType": None, "payUrl": None, "codeUrl": None}


def is_paid_state(state: str) -> bool:
    return state in _PAID_CHAIN_STATES


def apply_payment_result(db: Session, out_trade_no: str, payload: dict, raw_callback: str | None) -> tuple[str, str]:
    """处理微信支付结果（回调与查单共用），返回 (status, message)。

    status: "ok"=本调用完成解锁；"already"=此前已处理（幂等）；"fail"=校验/状态不满足。
    """
    if payload.get("trade_state") != "SUCCESS":
        return "fail", f"trade_state={payload.get('trade_state')}"

    order = db.query(Order).filter(Order.out_trade_no == out_trade_no).first()
    if order is None:
        return "fail", "order not found"

    total = (payload.get("amount") or {}).get("total")
    if total is None or total != order.amount:
        logger.error("回调金额与订单不符：order_no=%s, wx=%s, order=%s", order.order_no, total, order.amount)
        return "fail", "amount mismatch"

    if order.state == OrderState.CREATED.value:
        now = utcnow()
        result = db.execute(
            sa_update(Order)
            .where(Order.order_no == order.order_no, Order.state == OrderState.CREATED.value)
            .values(state=OrderState.PAID.value, paid_at=now)
        )
        if result.rowcount == 0:
            db.refresh(order)
        else:
            db.refresh(order)
            _unlock_and_record(db, order, payload, now, raw_callback)
            return "ok", ""

    if is_paid_state(order.state):
        return "already", "already processed"

    logger.error("订单状态不允许支付推进：order_no=%s, state=%s", order.order_no, order.state)
    return "fail", f"state={order.state} not payable"


def _unlock_and_record(db: Session, order: Order, payload: dict, now, raw_callback: str | None) -> None:
    """事务内解锁完整报告并落支付流水（仅在 CAS 获胜后调用，保证恰好一次）。"""
    order.state = OrderState.UNLOCKED.value
    order.openid = ((payload.get("payer") or {}).get("openid")) or order.openid

    report = (
        db.query(Report)
        .filter(Report.profile_id == order.profile_id)
        .order_by(Report.id.desc())
        .first()
    )
    if report is not None:
        report.order_no = order.order_no
        report.state = "unlocked"
        report.unlocked_at = now

    transaction_id = payload.get("transaction_id") or f"WX-{order.order_no}-{now:%Y%m%d%H%M%S}"
    db.add(
        PayTransaction(
            transaction_id=transaction_id,
            order_no=order.order_no,
            pay_type=order.pay_type or "h5",
            amount=order.amount,
            pay_state="SUCCESS",
            raw_callback=raw_callback,
            callback_at=now,
        )
    )


def handle_pay_notify(db: Session, headers, raw_body: bytes) -> tuple[str, str]:
    """微信支付结果回调处理，返回 (应答码, 说明)，应答码为 "SUCCESS"/"FAIL"。"""
    client = wechatpay.client
    if not client.platform_ready:
        logger.error("微信支付未配置或平台证书缺失，拒绝处理回调")
        return "FAIL", "wxpay not configured"

    signature = headers.get("Wechatpay-Signature") or headers.get("wechatpay-signature")
    timestamp = headers.get("Wechatpay-Timestamp") or headers.get("wechatpay-timestamp")
    nonce = headers.get("Wechatpay-Nonce") or headers.get("wechatpay-nonce")
    if not (signature and timestamp and nonce):
        return "FAIL", "missing signature headers"
    if not client.verify_signature(timestamp, nonce, raw_body, signature):
        logger.error("微信支付回调验签失败")
        return "FAIL", "signature verification failed"

    try:
        envelope = json.loads(raw_body)
        payload = json.loads(client.decrypt_resource(envelope["resource"]))
    except Exception as e:  # noqa: BLE001
        logger.error("回调报文解密失败：%s", e)
        return "FAIL", f"decrypt failed: {e}"

    try:
        status, message = apply_payment_result(db, payload.get("out_trade_no") or "", payload, raw_body.decode("utf-8", errors="replace"))
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.exception("回调落库失败：%s", e)
        return "FAIL", "apply failed"

    if status in ("ok", "already"):
        return "SUCCESS", ""
    logger.error("回调业务校验不通过：%s", message)
    return "FAIL", message


def create_refund(db: Session, order: Order, reason: str | None) -> dict:
    """人工审核后发起退款：订单进入 REFUNDING，返回退款单信息。"""
    if not wx_ready():
        raise BizError(ErrorCode.PAYMENT_RAISE_FAILED, "微信支付未配置")

    existing = db.query(Refund).filter(Refund.order_no == order.order_no).first()
    if existing is not None:
        raise BizError(ErrorCode.CONFLICT, "该订单已存在退款申请")

    refund_no = f"R{order.order_no}"
    db.add(Refund(order_no=order.order_no, refund_no=refund_no, amount=order.amount, state="PROCESSING", reason=reason))
    try:
        wechatpay.client.create_refund(
            out_trade_no=order.out_trade_no,
            out_refund_no=refund_no,
            total=order.amount,
            refund_amount=order.amount,
            reason=reason,
        )
    except WechatPayError as e:
        db.rollback()
        raise BizError(ErrorCode.PAYMENT_RAISE_FAILED, f"退款发起失败：{e}") from None

    order.state = OrderState.REFUNDING.value
    db.commit()
    return {"orderNo": order.order_no, "refundNo": refund_no, "state": order.state}