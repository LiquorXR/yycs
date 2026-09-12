"""支付服务：收钱吧微信小店·代客下单（H5 单路径）。

核心不变量：
- 金额一律整数分，推送/查单金额与订单精确比对，不一致拒绝（防改价/防串单）。
- 恰好一次：订单状态 CAS `UPDATE ... WHERE state='CREATED'`，并发推送仅一个获胜者；
  已进入支付链的状态重复推送直接返回成功（幂等，不重复解锁）。
- 未配置微信小店时优雅降级：ensure_payment 返回 null，订单仍可创建。
- 推送幂等：eventId 经 idempotency_records（scope=wxs-push）判重 24h。
- 退款仅记录：退款推送落 REFUNDED 流水 + 打标，不改订单主状态，人工核账。
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.timeutil import utcnow
from app.models.idempotency import IdempotencyRecord
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.product import Product
from app.models.report import Report
from app.services import wxstore
from app.services.wxstore import (
    PREORDER_CANCELED,
    PREORDER_DONE,
    PREORDER_PENDING,
)

logger = logging.getLogger(__name__)

# 已进入支付/交付链路的订单状态：重复推送视为已处理（幂等成功）
_PAID_CHAIN_STATES = {
    OrderState.PAID.value,
    OrderState.UNLOCKED.value,
    OrderState.DELIVERED.value,
    OrderState.ADDED_WECOM.value,
}

_PAYMENT_DESC = "振凡命理·测算服务"

# 推送幂等作用域（idempotency_records 复用，key=eventId）
IDEM_SCOPE_WXS_PUSH = "wxs-push"


def wxs_ready() -> bool:
    return wxstore.client.is_ready


def normalize_payment_method(payment_method: str | None) -> str:
    """入库归一化：单 H5 路径下一律 wx_h5（历史值兼容）。"""
    return "wx_h5"


def display_pay_type(original: str | None, pay_url: str | None, code_url: str | None) -> str | None:
    """展示用 payType：0元促销为 free；有 H5 短链为 h5，否则 null（建单/详情降级一致）。"""
    if (original or "").lower() == "free":
        return "free"
    if pay_url:
        return "h5"
    return None


async def ensure_payment(db: Session, order: Order, client_ip: str | None = None) -> dict:
    """微信小店下单（async），返回 {payType, payUrl, codeUrl, jumpUrl, wxJumpUrl}。

    0元订单直接返回 payType='free'，跳过预订单/H5 短链（无需外呼）。
    建预订单 savePreOrder → 取 H5 短链 generatePreOrderH5Link → best-effort 解析
    直达收银台地址；pre_order_id 与 h5_jump_url 写回 order（由调用方 commit）。
    配置缺失或任何异常均优雅降级返回 null（订单仍可创建）。
    本期只留 H5 单路径，codeUrl 恒为 None。
    """
    _ = client_ip
    if int(order.amount or 0) == 0:
        return {"payType": "free", "payUrl": None, "codeUrl": None, "jumpUrl": None,
                "wxJumpUrl": None}
    if not wxs_ready():
        return {"payType": None, "payUrl": None, "codeUrl": None, "jumpUrl": None,
                "wxJumpUrl": None}

    try:
        product = await run_in_threadpool(db.query(Product).filter(Product.id == order.product_id).first)
        description = (product.name if product else _PAYMENT_DESC)[:64]
        _ = description
        pre_order_id = await wxstore.client.save_pre_order(order.amount, request_id=order.order_no)
        order.pre_order_id = pre_order_id
        logger.info("微信小店预订单创建成功 order_no=%s", order.order_no)
        try:
            pay_url = await wxstore.client.generate_h5_link(pre_order_id)
        except Exception as e:  # noqa: BLE001 H5 短链失败降级（预订单已建，对账可查）
            logger.warning("微信小店 H5 短链失败：order_no=%s %s", order.order_no, type(e).__name__)
            return {"payType": None, "payUrl": None, "codeUrl": None, "jumpUrl": None,
                    "wxJumpUrl": None}
        try:
            order.h5_jump_url = await wxstore.client.resolve_h5_jump_url(pay_url)
        except Exception as e:  # noqa: BLE001 直达地址解析失败不阻塞（前端回落短链）
            logger.warning("微信小店直达地址解析失败：order_no=%s %s", order.order_no, type(e).__name__)
            order.h5_jump_url = None
        wx_jump_url = await run_in_threadpool(get_wechat_jump_url, order.pre_order_id)
        return {"payType": "h5", "payUrl": pay_url, "codeUrl": None, "jumpUrl": order.h5_jump_url,
                "wxJumpUrl": wx_jump_url}
    except Exception as e:  # noqa: BLE001 下单兜底：任何意外均降级 null，不抛 500
        logger.exception("微信小店下单兜底降级：order_no=%s %s", getattr(order, "order_no", "?"), type(e).__name__)
        return {"payType": None, "payUrl": None, "codeUrl": None, "jumpUrl": None,
                "wxJumpUrl": None}


def is_paid_state(state: str) -> bool:
    return state in _PAID_CHAIN_STATES


def get_wechat_jump_url(pre_order_id: str | None) -> str | None:
    """微信直跳 URL best-effort 获取；失败返回 None，前端回落 H5 短链，绝不抛异常。"""
    if not pre_order_id or not wxs_ready():
        return None
    try:
        return wxstore.client.build_wechat_jump(str(pre_order_id))
    except Exception as e:  # noqa: BLE001
        logger.warning("微信直跳 URL 构造失败，已回落短链：%r", e)
        return None


def _append_fail_reason(order: Order, reason: str) -> None:
    """fail_reason 追加不覆盖，保留历史原因链。"""
    if order.fail_reason and reason not in order.fail_reason:
        order.fail_reason = f"{order.fail_reason};{reason}"[:255]
    elif not order.fail_reason:
        order.fail_reason = reason[:255]


# 确定性失败（重试无意义，记 DB+告警后回 success 止血，避免推送重试风暴）
_DETERMINISTIC_FAILS = {"amount mismatch", "order not found", "paid_after_close"}


def apply_payment_result(db: Session, pre_order_id: str, payload: dict, raw_callback: str | None) -> tuple[str, str]:
    """处理微信小店支付结果（推送与查单共用），返回 (status, message)。

    status: "ok"=本调用完成解锁；"already"=此前已处理（幂等）；"fail"=校验/状态不满足。
    payload 为归一化结果 {order_sn, order_signature, amount(int), pre_order_id}。
    """
    order = db.query(Order).filter(Order.pre_order_id == pre_order_id).first()
    if order is None:
        return "fail", "order not found"

    total_int = payload.get("amount")
    if not isinstance(total_int, int) or total_int != order.amount:
        logger.error("推送金额与订单不符：order_no=%s, wxs=%s, order=%s", order.order_no, payload.get("amount"), order.amount)
        return "fail", "amount mismatch"

    # 关单后仍支付成功：记人工核账标记并告警（调用方回 success 止血，重试无意义）
    if order.state == OrderState.CLOSED.value:
        _append_fail_reason(order, f"paid_after_close sn={payload.get('order_sn')}")
        logger.error(
            "关单后支付成功需人工核账：order_no=%s, sn=%s, amount=%s",
            order.order_no, payload.get("order_sn"), total_int,
        )
        return "fail", "paid_after_close"

    if order.state == OrderState.CREATED.value:
        now = utcnow()
        # CAS 自旋：失败方 refresh 可能读到获胜方提交前的 CREATED 快照，重试等待终态；
        # 仍为 CREATED 则视为获胜方在途，回 already（重复投递确认成功，避免重试风暴）
        for _ in range(10):
            result = db.execute(
                sa_update(Order)
                .where(Order.order_no == order.order_no, Order.state == OrderState.CREATED.value)
                .values(
                    state=OrderState.PAID.value,
                    paid_at=now,
                    order_sn=str(payload.get("order_sn") or order.order_sn or "") or None,
                    order_signature=str(payload.get("order_signature") or order.order_signature or "") or None,
                )
            )
            if result.rowcount:
                db.refresh(order)
                _unlock_and_record(db, order, payload, now, raw_callback)
                return "ok", ""
            db.refresh(order)
            if order.state != OrderState.CREATED.value:
                break
            time.sleep(0.02)
        db.refresh(order)
        if order.state == OrderState.CREATED.value:
            logger.warning("CAS 竞争：order_no=%s 获胜方在途，本次确认已处理", order.order_no)
            return "already", "contention, winner in flight"

    if is_paid_state(order.state):
        return "already", "already processed"

    logger.error("订单状态不允许支付推进：order_no=%s, state=%s", order.order_no, order.state)
    return "fail", f"state={order.state} not payable"


def _unlock_and_record(db: Session, order: Order, payload: dict, now, raw_callback: str | None) -> None:
    """事务内解锁完整报告并落支付流水（仅在 CAS 获胜后调用，保证恰好一次）。"""
    order.state = OrderState.UNLOCKED.value

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

    sn = payload.get("order_sn") or f"WXS-{order.order_no}-{uuid.uuid4().hex[:8].upper()}-{now:%Y%m%d%H%M%S}"
    db.add(
        PayTransaction(
            transaction_id=str(sn)[:64],
            order_no=order.order_no,
            pay_type=order.pay_type or "h5",
            amount=order.amount,
            pay_state="SUCCESS",
            raw_callback=raw_callback,
            callback_at=now,
        )
    )


def _push_seen(db: Session, event_id: str) -> bool:
    """eventId 是否已处理（24h 内）。"""
    rec = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == f"{IDEM_SCOPE_WXS_PUSH}:{event_id}").first()
    return rec is not None


def _mark_push_seen(db: Session, event_id: str) -> None:
    db.add(
        IdempotencyRecord(
            key=f"{IDEM_SCOPE_WXS_PUSH}:{event_id}",
            scope=IDEM_SCOPE_WXS_PUSH,
            response=json.dumps({"result": "success"}, ensure_ascii=False),
        )
    )


def _find_order_by_push(db: Session, content: dict) -> Order | None:
    """经推送 preOrderList 回关联本地订单（取首个可匹配项）。"""
    pre_orders = content.get("preOrderList") or []
    for item in pre_orders:
        pid = (item or {}).get("preOrderId")
        if not pid:
            continue
        order = db.query(Order).filter(Order.pre_order_id == str(pid)).first()
        if order is not None:
            return order
    return None


def handle_pay_notify(db: Session, raw_body: bytes) -> tuple[str, str]:
    """微信小店订单支付成功推送处理，返回 (应答, 说明)，应答为 "success"/"fail"。

    验签→eventId 判重→preOrderList 关联订单→金额比对→CAS 推进。
    止重试策略：确定性失败（金额不符/订单不存在/非终态）记 DB+告警后回
    "success" 止血；可重试（验签/解析/落库异常）回 "fail"。
    """
    try:
        event_id, content = wxstore.client.verify_push(raw_body)
    except Exception as e:  # noqa: BLE001
        logger.error("微信小店支付推送验签/解析失败: %s", e)
        return "fail", str(e)

    if _push_seen(db, event_id):
        logger.info("支付推送重复投递已处理 event=%s", event_id)
        return "success", "already processed"
    if not isinstance(content, dict):
        logger.error("支付推送 content 非对象 event=%s", event_id)
        return "success", "invalid content"

    order = _find_order_by_push(db, content)
    if order is None:
        logger.error("支付推送无关联订单 event=%s", event_id)
        try:
            _mark_push_seen(db, event_id)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        return "success", "order not found"

    total_raw = content.get("orderAmount")
    try:
        total_int = int(total_raw) if total_raw is not None else None
    except (TypeError, ValueError):
        total_int = None
    payload = {
        "order_sn": content.get("orderSn"),
        "order_signature": content.get("orderSignature"),
        "amount": total_int,
        "pre_order_id": order.pre_order_id,
    }

    try:
        status_ret, message = apply_payment_result(
            db, str(order.pre_order_id or ""), payload, raw_body.decode("utf-8", errors="replace")
        )
        _mark_push_seen(db, event_id)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.exception("支付推送落库失败: %s", e)
        return "fail", "apply failed"

    if status_ret in ("ok", "already"):
        logger.info("支付推送处理成功 status=%s order_no=%s", status_ret, order.order_no)
        return "success", ""
    if message in _DETERMINISTIC_FAILS or message.startswith("state="):
        # 确定性失败：已记 DB+日志，回 success 止血
        logger.error("支付推送确定性失败止血: %s order_no=%s", message, order.order_no)
        return "success", message
    logger.error("支付推送业务校验不通过: %s", message)
    return "fail", message


# 退款完成/失败目标态（queryTicket ticketStateCode 语义对齐：20 完成/30 失败）
_REFUND_DONE_STATES = {20, "20"}
_REFUND_FAIL_STATES = {30, "30"}


def handle_refund_notify(db: Session, raw_body: bytes) -> tuple[str, str]:
    """微信小店退款状态变更推送处理（只记录可查），返回 (应答, 说明)。

    语义：验签通过后落一条 pay_state=REFUNDED 流水 + order.fail_reason 打标，
    不改 order.state，后续人工核账。以 ticketSn 为流水主键去重。
    """
    try:
        event_id, content = wxstore.client.verify_push(raw_body)
    except Exception as e:  # noqa: BLE001
        logger.error("微信小店退款推送验签/解析失败: %s", e)
        return "fail", str(e)

    if _push_seen(db, event_id):
        logger.info("退款推送重复投递已处理 event=%s", event_id)
        return "success", "already processed"
    if not isinstance(content, dict):
        logger.error("退款推送 content 非对象 event=%s", event_id)
        return "success", "invalid content"

    target = content.get("targetState")
    if target not in _REFUND_DONE_STATES | _REFUND_FAIL_STATES:
        logger.info("退款推送非终态无需记录 event=%s target=%s", event_id, target)
        try:
            _mark_push_seen(db, event_id)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        return "success", f"not final: {target}"

    order_sn = str(content.get("orderSn") or "")
    order = db.query(Order).filter(Order.order_sn == order_sn).first() if order_sn else None
    if order is None:
        # 回退：经 preOrderList 关联（部分退款推送可能携带）
        order = _find_order_by_push(db, content)
    if order is None:
        logger.error("退款推送订单不存在 event=%s orderSn=%s", event_id, order_sn)
        try:
            _mark_push_seen(db, event_id)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        return "success", "order not found"

    ticket_sn = str(content.get("ticketSn") or "")
    txn_id = (ticket_sn or f"REFUND-{order.order_no}-{target}")[:64]
    try:
        existing = db.query(PayTransaction).filter(PayTransaction.transaction_id == txn_id).first()
        if existing is None:
            now = utcnow()
            _append_fail_reason(order, f"refund:{target} sn={ticket_sn}" if ticket_sn else f"refund:{target}")
            db.add(
                PayTransaction(
                    transaction_id=txn_id,
                    order_no=order.order_no,
                    pay_type=order.pay_type or "h5",
                    amount=order.amount,
                    pay_state="REFUNDED",
                    raw_callback=raw_body.decode("utf-8", errors="replace"),
                    callback_at=now,
                )
            )
        else:
            logger.info("退款推送重复票据已记录 txn=%s", txn_id)
        _mark_push_seen(db, event_id)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.exception("退款推送落库失败: %s", e)
        return "fail", "apply failed"

    logger.info("退款推送已记录 order_no=%s target=%s txn=%s", order.order_no, target, txn_id)
    return "success", ""


__all__ = [
    "IDEM_SCOPE_WXS_PUSH",
    "apply_payment_result",
    "display_pay_type",
    "ensure_payment",
    "get_wechat_jump_url",
    "handle_pay_notify",
    "handle_refund_notify",
    "is_paid_state",
    "normalize_payment_method",
    "wxs_ready",
]
