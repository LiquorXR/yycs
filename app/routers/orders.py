"""订单模块路由：创建订单、订单详情、关单、获取报告、开发环境模拟解锁。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BizError, ErrorCode
from app.core.response import ok_response
from app.core.timeutil import iso_utc, utcnow
from app.db.session import get_db
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.report import Report
from app.services import order_service
from app.services.idempotency import IDEM_SCOPE_ORDER, get_idempotent_response, store_idempotent_response
from app.services.report import DEFAULT_LOCKED_PREVIEW

router = APIRouter(tags=["orders"])

PAYMENT_METHODS = ("auto", "h5", "native")

# 已进入支付/交付链路的状态，关单一律拒绝（12002）
_PAID_STATES = {
    OrderState.PAID.value,
    OrderState.UNLOCKED.value,
    OrderState.DELIVERED.value,
    OrderState.ADDED_WECOM.value,
    OrderState.REFUNDING.value,
    OrderState.REFUNDED.value,
}

# 已解锁报告可返回完整契约的状态
_UNLOCKED_STATES = {
    OrderState.UNLOCKED.value,
    OrderState.DELIVERED.value,
    OrderState.ADDED_WECOM.value,
}

_WECOM_NOTE = "已生成专属客服码,扫码添加后由人工为您深度测算"


class OrderCreateRequest(BaseModel):
    profileId: str
    productId: int
    paymentMethod: str = Field("auto", description="auto/h5/native")
    adParams: dict | None = None
    amount: int | None = Field(None, description="防改价校验用，非必填")


@router.post("/api/orders")
def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    """创建订单：金额以服务端产品表为准，响应 payType/payUrl/codeUrl 待 B 阶段支付模块填充（本期返回 null）。"""
    if not idempotency_key:
        raise BizError(ErrorCode.PARAM_VALIDATION, "参数校验失败：Idempotency-Key 必填")
    if payload.paymentMethod not in PAYMENT_METHODS:
        raise BizError(ErrorCode.PARAM_VALIDATION, "参数校验失败：paymentMethod 需为 auto/h5/native")

    cached = get_idempotent_response(db, idempotency_key, IDEM_SCOPE_ORDER)
    if cached is not None:
        return ok_response(cached)

    order_no, amount = order_service.create_order(
        db,
        payload.profileId,
        payload.productId,
        payload.paymentMethod,
        payload.adParams,
        payload.amount,
    )

    # B 阶段：支付模块统一下单后填充 payType/payUrl/codeUrl
    data = {"orderNo": order_no, "amount": amount, "payType": None, "payUrl": None, "codeUrl": None}
    store_idempotent_response(db, idempotency_key, IDEM_SCOPE_ORDER, data)
    db.commit()
    return ok_response(data)


@router.get("/api/orders/{order_no}")
def get_order(order_no: str, db: Session = Depends(get_db)) -> dict:
    """订单详情（时间字段 ISO8601 UTC）。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    return ok_response(
        {
            "orderNo": order.order_no,
            "profileId": order.profile_id,
            "productId": order.product_id,
            "outTradeNo": order.out_trade_no,
            "amount": order.amount,
            "state": order.state,
            "payType": order.pay_type,
            "openid": order.openid,
            "adParams": order.ad_params,
            "failReason": order.fail_reason,
            "createdAt": iso_utc(order.created_at),
            "paidAt": iso_utc(order.paid_at),
        }
    )


@router.post("/api/orders/{order_no}/close")
def close_order(order_no: str, db: Session = Depends(get_db)) -> dict:
    """关单：仅 CREATED 可关；已支付 12002，其余非 CREATED 12003。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    if order.state in _PAID_STATES:
        raise BizError(ErrorCode.ORDER_ALREADY_PAID, "订单已支付")
    if order.state != OrderState.CREATED.value:
        raise BizError(ErrorCode.ORDER_STATUS_INVALID, "订单状态不允许操作")
    order.state = OrderState.CLOSED.value
    db.commit()
    return ok_response({"orderNo": order.order_no, "state": order.state})


@router.get("/api/orders/{order_no}/report")
def get_order_report(order_no: str, db: Session = Depends(get_db)) -> dict:
    """获取报告：未解锁返回锁定预览（lockedPreview），已解锁返回完整契约与企微活码。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")

    report = (
        db.query(Report)
        .filter(Report.profile_id == order.profile_id)
        .order_by(Report.id.desc())
        .first()
    )
    contract = json.loads(report.full_report) if report and report.full_report else None

    unlocked = order.state in _UNLOCKED_STATES
    if unlocked and (report is None or report.state != "unlocked" or contract is None):
        raise BizError(ErrorCode.REPORT_NOT_UNLOCKED, "报告未解锁")

    if unlocked:
        report_view = dict(contract)
        report_view["locked"] = False
        wecom = (
            {"qrcodeUrl": settings.WECOM_QRCODE_URL, "note": _WECOM_NOTE}
            if settings.WECOM_QRCODE_URL
            else None
        )
    else:
        report_view = {
            "title": contract["title"] if contract else "八字合婚详批",
            "locked": True,
            "lockedPreview": contract["lockedPreview"] if contract else [dict(x) for x in DEFAULT_LOCKED_PREVIEW],
        }
        wecom = None

    return ok_response({"orderNo": order.order_no, "state": order.state, "report": report_view, "wecom": wecom})


if settings.APP_ENV == "dev":

    @router.post("/api/orders/{order_no}/pay-success-mock")
    def pay_success_mock(order_no: str, db: Session = Depends(get_db)) -> dict:
        """开发环境模拟支付成功解锁：订单 CREATED→UNLOCKED、报告解锁、落 mock 支付流水。"""
        order = db.query(Order).filter(Order.order_no == order_no).first()
        if order is None:
            raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
        if order.state != OrderState.CREATED.value:
            if order.state in _PAID_STATES:
                raise BizError(ErrorCode.ORDER_ALREADY_PAID, "订单已支付")
            raise BizError(ErrorCode.ORDER_STATUS_INVALID, "订单状态不允许操作")

        order.state = OrderState.UNLOCKED.value
        order.paid_at = utcnow()

        report = (
            db.query(Report)
            .filter(Report.profile_id == order.profile_id)
            .order_by(Report.id.desc())
            .first()
        )
        if report is not None:
            report.order_no = order.order_no
            report.state = "unlocked"
            report.unlocked_at = utcnow()

        db.add(
            PayTransaction(
                transaction_id=f"MOCK-{order.order_no}",
                order_no=order.order_no,
                pay_type="mock",
                amount=order.amount,
                pay_state="SUCCESS",
                raw_callback="mock",
            )
        )
        db.commit()
        return ok_response({"orderNo": order.order_no, "state": order.state})
