"""订单模块路由：创建订单、订单详情、关单、获取报告、开发环境模拟解锁。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import BizError, ErrorCode
from app.core.response import ok_response
from app.core.timeutil import iso_utc, utcnow
from app.db.session import get_db
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.report import Report
from app.services import order_service, pay_service
from app.services.idempotency import IDEM_SCOPE_ORDER, get_idempotent_response, hash_payload, store_idempotent_response
from app.services.report import DEFAULT_LOCKED_PREVIEW

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orders"])

# auto/h5/native 为历史兼容（默认微信通道）；wx_h5/ali_h5 为双通道显式值
PAYMENT_METHODS = ("auto", "h5", "native", "wx_h5", "ali_h5", "wx_native", "ali_qr")

# 已进入支付/交付链路的状态：关单一律拒绝（12002）；报告接口据此决定是否展示企微引导
_PAID_STATES = {
    OrderState.PAID.value,
    OrderState.UNLOCKED.value,
    OrderState.DELIVERED.value,
    OrderState.ADDED_WECOM.value,
}

_WECOM_NOTE = "点击添加企业微信后由人工为您深度解读正缘"


class AdParamsModel(BaseModel):
    """投放归因白名单：仅允许三字段，其余 forbid，防 DoS/注入。"""

    model_config = {"extra": "forbid"}

    ad_id: str | None = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    creative_id: str | None = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    campaign_id: str | None = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


class OrderCreateRequest(BaseModel):
    profileId: str
    productId: int
    paymentMethod: str = Field("auto", description="auto/h5/native/wx_h5/ali_h5/wx_native/ali_qr")
    adParams: AdParamsModel | None = None
    amount: int | None = Field(None, description="防改价校验用，非必填")


@router.post("/api/orders")
async def create_order(
    payload: OrderCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    """创建订单（async）：金额以服务端产品表为准；支付配置齐全时返回真实 payType/payUrl/codeUrl，否则 null 降级。

    DB 操作统一经 run_in_threadpool 执行，避免同步 IO 阻塞事件循环；
    收钱吧 WAP 为本地拼串，聚合码预下单 await 外呼（httpx async），不占线程池。
    """
    if not idempotency_key:
        raise BizError(ErrorCode.PARAM_VALIDATION, "参数校验失败：Idempotency-Key 必填")
    if (payload.paymentMethod or "").lower() not in PAYMENT_METHODS:
        raise BizError(ErrorCode.PARAM_VALIDATION, "参数校验失败：paymentMethod 非法")

    payload_hash = hash_payload(payload.model_dump())
    cached = await run_in_threadpool(get_idempotent_response, db, idempotency_key, IDEM_SCOPE_ORDER, payload_hash)
    if cached is not None:
        return ok_response(cached)

    # 白名单后的 AdParams 需转为普通 dict 落库
    ad_params_dict = None
    if payload.adParams is not None:
        ad_params_dict = payload.adParams.model_dump(exclude_none=True) or None

    pay_channel = pay_service.normalize_payment_method(payload.paymentMethod)
    order_no, amount = await run_in_threadpool(
        order_service.create_order,
        db,
        payload.profileId,
        payload.productId,
        pay_channel,
        ad_params_dict,
        payload.amount,
    )

    order = await run_in_threadpool(db.query(Order).filter(Order.order_no == order_no).first)
    client_ip = request.client.host if request.client else None
    pay_info = await pay_service.ensure_payment(db, order, client_ip)

    # order.pay_type 保留原始通道（wx_h5/ali_h5），展示用 payType 按 URL 归一化，不回写覆盖
    order.pay_url = pay_info["payUrl"]
    order.code_url = pay_info["codeUrl"]

    data = {
        "orderNo": order_no,
        "amount": amount,
        "payType": pay_info["payType"],
        "payChannel": pay_channel,
        "payUrl": pay_info["payUrl"],
        "codeUrl": pay_info["codeUrl"],
    }
    await run_in_threadpool(store_idempotent_response, db, idempotency_key, IDEM_SCOPE_ORDER, data, payload_hash)
    await run_in_threadpool(db.commit)
    return ok_response(data)


@router.get("/api/orders/{order_no}")
def get_order(
    order_no: str,
    profileId: str | None = Query(None, description="归属校验：传入时需与订单 profile_id 一致"),
    db: Session = Depends(get_db),
) -> dict:
    """订单详情（时间字段 ISO8601 UTC）。归属校验：若传入 profileId 则校验一致性，防随机ID外的二次防护。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    if profileId is not None and order.profile_id != profileId:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    return ok_response(
        {
            "orderNo": order.order_no,
            "profileId": order.profile_id,
            "productId": order.product_id,
            "outTradeNo": order.out_trade_no,
            "amount": order.amount,
            "state": order.state,
            "payType": pay_service.display_pay_type(order.pay_type, order.pay_url, order.code_url),
            "payChannel": order.pay_type,
            "payUrl": order.pay_url,
            "codeUrl": order.code_url,
            "openid": order.openid,
            "adParams": order.ad_params,
            "failReason": order.fail_reason,
            "createdAt": iso_utc(order.created_at),
            "paidAt": iso_utc(order.paid_at),
        }
    )


@router.post("/api/orders/{order_no}/close")
def close_order(
    order_no: str,
    profileId: str | None = Query(None, description="归属校验"),
    db: Session = Depends(get_db),
) -> dict:
    """关单：仅 CREATED 可关；已支付 12002，其余非 CREATED 12003。上游撤单 best-effort，失败不阻塞本地关单。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    if profileId is not None and order.profile_id != profileId:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    if order.state in _PAID_STATES:
        raise BizError(ErrorCode.ORDER_ALREADY_PAID, "订单已支付")
    if order.state != OrderState.CREATED.value:
        raise BizError(ErrorCode.ORDER_STATUS_INVALID, "订单状态不允许操作")

    if pay_service.sqb_ready():
        try:
            pay_service.shouqianba.client.cancel_order(order.out_trade_no, timeout=5.0)
        except Exception as e:  # noqa: BLE001 上游撤单失败不阻塞本地关单，由 paid_after_close 兜底
            logger.warning("收钱吧撤单失败：order_no=%s, %s", order.order_no, e)

    order.state = OrderState.CLOSED.value
    db.commit()
    return ok_response({"orderNo": order.order_no, "state": order.state})


@router.get("/api/orders/{order_no}/report")
def get_order_report(
    order_no: str,
    profileId: str | None = Query(None, description="归属校验"),
    db: Session = Depends(get_db),
) -> dict:
    """获取报告：无论订单状态一律只返回锁定预览（title + lockedPreview + locked=true），
    完整测算结果由人工交付；已支付订单在配置企微客服码时返回 wecom 引导。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    if profileId is not None and order.profile_id != profileId:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")

    report = (
        db.query(Report)
        .filter(Report.profile_id == order.profile_id)
        .order_by(Report.id.desc())
        .first()
    )
    contract = json.loads(report.full_report) if report and report.full_report else None

    report_view = {
        "title": contract["title"] if contract else "姻缘天书·正缘详批（预览）",
        "locked": True,
        "lockedPreview": contract["lockedPreview"] if contract else [dict(x) for x in DEFAULT_LOCKED_PREVIEW],
    }
    wecom = (
        {"qrcodeUrl": settings.WECOM_QRCODE_URL, "note": _WECOM_NOTE}
        if order.state in _PAID_STATES and settings.WECOM_QRCODE_URL
        else None
    )

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
