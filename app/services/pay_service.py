"""支付服务：收钱吧聚合支付（微信+支付宝）下单、回调处理、查单推进。

核心不变量：
- 金额一律整数分，回调/查单金额与订单精确比对，不一致拒绝（防改价/防串单）。
- 恰好一次：订单状态 CAS `UPDATE ... WHERE state='CREATED'`，并发回调仅一个获胜者；
  已进入支付链的状态重复回调直接返回成功（幂等，不重复解锁）。
- 未配置收钱吧时优雅降级：ensure_payment 返回全 null，订单仍可创建。
- WAP 跳转为本地拼串（无网络）；聚合码预下单为 async（httpx 外呼不占线程池）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.timeutil import utcnow
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.product import Product
from app.models.report import Report
from app.core.config import settings
from app.services import shouqianba
from app.services.shouqianba import PAID_STATUS, normalize_amount

logger = logging.getLogger(__name__)

# 已进入支付/交付链路的订单状态：重复回调视为已处理（幂等成功）
_PAID_CHAIN_STATES = {
    OrderState.PAID.value,
    OrderState.UNLOCKED.value,
    OrderState.DELIVERED.value,
    OrderState.ADDED_WECOM.value,
}

_PAYMENT_DESC = "振凡命理·测算服务"

# 收钱吧预下单并发上限（每 worker 独立）：防突发流量触发风控
_SQB_SEM = asyncio.Semaphore(8)
# H5 备选码独立信号量 + 短超时：备选 best-effort，不得阻塞主路径、不得挤占主下单并发
_SQB_FALLBACK_SEM = asyncio.Semaphore(4)
_FALLBACK_TIMEOUT_S = 3.0


def sqb_ready() -> bool:
    return shouqianba.client.is_ready


def _channel_of(payment_method: str | None) -> tuple[str, bool]:
    """解析 (payway, want_h5)。auto/h5 沿用微信；native 沿用微信聚合码。"""
    pm = (payment_method or "auto").lower()
    if pm == "ali_h5":
        return shouqianba.PAYWAY_ALIPAY, True
    if pm == "ali_qr":
        return shouqianba.PAYWAY_ALIPAY, False
    if pm in ("wx_native", "native"):
        return shouqianba.PAYWAY_WECHAT, False
    # auto / h5 / wx_h5 及未知值默认微信 H5
    return shouqianba.PAYWAY_WECHAT, True


def normalize_payment_method(payment_method: str | None) -> str:
    """入库归一化：auto/h5→wx_h5，native→wx_native，其余小写原样（wx_h5/ali_h5/wx_native/ali_qr）。"""
    pm = (payment_method or "auto").lower()
    if pm in ("auto", "h5"):
        return "wx_h5"
    if pm == "native":
        return "wx_native"
    return pm


def display_pay_type(original: str | None, pay_url: str | None, code_url: str | None) -> str | None:
    """展示用 payType（h5/native）：有 URL 按 URL 归一化，无 URL 统一 null（建单/详情降级一致）。"""
    if pay_url:
        return "h5"
    if code_url:
        return "native"
    return None


async def ensure_payment(db: Session, order: Order, client_ip: str | None = None) -> dict:
    """收钱吧下单（async），返回 {payType, payUrl, codeUrl}。

    支付配置缺失时优雅降级返回全 null（订单仍可创建）；
    H5（WAP 跳转）为主，聚合码预下单为降级/备选（快手 WebView 拦截时用）。
    client_ip 保留参数兼容（收钱吧 WAP 不需要该字段）。
    """
    _ = client_ip
    if not sqb_ready():
        return {"payType": None, "payUrl": None, "codeUrl": None}

    try:
        product = await run_in_threadpool(db.query(Product).filter(Product.id == order.product_id).first)
        description = (product.name if product else _PAYMENT_DESC)[:64]
        payway, want_h5 = _channel_of(order.pay_type)

        pay_url: str | None = None
        code_url: str | None = None

        if want_h5:
            try:
                pay_url = shouqianba.client.build_wap_url(
                    order.out_trade_no, order.amount, description, payway=payway
                )
                logger.info("收钱吧 WAP 下单成功 order_no=%s payway=%s", order.order_no, payway)
            except Exception as e:  # noqa: BLE001 拼串失败降级，不抛 500
                logger.warning("收钱吧 WAP 拼串失败：order_no=%s %s", order.order_no, e)
                pay_url = None

            # 备选聚合码（best-effort，短超时+独立信号量，失败不阻塞 H5 主路径）
            try:
                async with _SQB_FALLBACK_SEM:
                    code_url = await asyncio.wait_for(
                        shouqianba.client.precreate_qr(
                            order.out_trade_no, order.amount, description, payway=payway,
                            timeout=_FALLBACK_TIMEOUT_S,
                        ),
                        timeout=_FALLBACK_TIMEOUT_S + 0.5,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("收钱吧预下单失败（仅影响备选码）：order_no=%s %s", order.order_no, e)
                code_url = None

            if pay_url:
                return {"payType": "h5", "payUrl": pay_url, "codeUrl": code_url}
            if code_url:
                return {"payType": "native", "payUrl": None, "codeUrl": code_url}
            return {"payType": None, "payUrl": None, "codeUrl": None}

        # 仅要聚合码（5s 短超时）：失败时回退零成本的 WAP（不对称降级补齐）
        async with _SQB_SEM:
            try:
                code_url = await asyncio.wait_for(
                    shouqianba.client.precreate_qr(
                        order.out_trade_no, order.amount, description, payway=payway, timeout=5.0
                    ),
                    timeout=5.5,
                )
                logger.info("收钱吧预下单成功 order_no=%s payway=%s", order.order_no, payway)
                return {"payType": "native", "payUrl": None, "codeUrl": code_url}
            except Exception as e:  # noqa: BLE001
                logger.error("收钱吧预下单失败：order_no=%s %s", order.order_no, e)
        try:
            pay_url = shouqianba.client.build_wap_url(
                order.out_trade_no, order.amount, description, payway=payway
            )
            logger.info("收钱吧聚合码失败回退 WAP：order_no=%s payway=%s", order.order_no, payway)
            return {"payType": "h5", "payUrl": pay_url, "codeUrl": None}
        except Exception as e:  # noqa: BLE001
            logger.error("收钱吧 WAP 回退失败：order_no=%s %s", order.order_no, e)
        return {"payType": None, "payUrl": None, "codeUrl": None}
    except Exception as e:  # noqa: BLE001 下单兜底：任何意外均降级 null，不抛 500
        logger.exception("收钱吧下单兜底降级：order_no=%s %s", getattr(order, "order_no", "?"), e)
        return {"payType": None, "payUrl": None, "codeUrl": None}


def is_paid_state(state: str) -> bool:
    return state in _PAID_CHAIN_STATES


def _append_fail_reason(order: Order, reason: str) -> None:
    """fail_reason 追加不覆盖，保留历史原因链。"""
    if order.fail_reason and reason not in order.fail_reason:
        order.fail_reason = f"{order.fail_reason};{reason}"[:255]
    elif not order.fail_reason:
        order.fail_reason = reason[:255]


# 确定性失败（重试无意义，记 DB+告警后回 success 止血，避免 1s/5s/30s/600s 重试风暴）
_DETERMINISTIC_FAILS = {"amount mismatch", "order not found", "paid_after_close"}


def apply_payment_result(db: Session, client_sn: str, payload: dict, raw_callback: str | None) -> tuple[str, str]:
    """处理收钱吧支付结果（回调与查单共用），返回 (status, message)。

    status: "ok"=本调用完成解锁；"already"=此前已处理（幂等）；"fail"=校验/状态不满足。
    payload 为归一化结果 {order_status, total_amount, sn, client_sn}。
    """
    if payload.get("order_status") != PAID_STATUS:
        return "fail", f"order_status={payload.get('order_status')}"

    order = db.query(Order).filter(Order.out_trade_no == client_sn).first()
    if order is None:
        return "fail", "order not found"

    total_int = normalize_amount(payload.get("total_amount"))
    if total_int is None or total_int != order.amount:
        logger.error("回调金额与订单不符：order_no=%s, sqb=%s, order=%s", order.order_no, payload.get("total_amount"), order.amount)
        return "fail", "amount mismatch"

    # 关单后仍支付成功：无退款路径，记人工核账标记并告警（调用方回 success 止血，重试无意义）
    if order.state == OrderState.CLOSED.value:
        _append_fail_reason(order, f"paid_after_close sn={payload.get('sn')}")
        logger.error(
            "关单后支付成功需人工核账：order_no=%s, sn=%s, amount=%s",
            order.order_no, payload.get("sn"), total_int,
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
                .values(state=OrderState.PAID.value, paid_at=now)
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

    sn = payload.get("sn") or f"SQB-{order.order_no}-{uuid.uuid4().hex[:8].upper()}-{now:%Y%m%d%H%M%S}"
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


def _get_header(headers, name: str) -> str | None:
    try:
        v = headers.get(name)
        if v:
            return v
    except Exception:  # noqa: BLE001
        pass
    try:
        v = headers.get(name.lower())
        if v:
            return v
    except Exception:  # noqa: BLE001
        pass
    if hasattr(headers, "items"):
        try:
            lc = {str(k).lower(): v for k, v in headers.items()}
            return lc.get(name.lower())
        except Exception:  # noqa: BLE001
            return None
    return None


def handle_pay_notify(db: Session, headers, raw_body: bytes) -> tuple[str, str]:
    """收钱吧支付结果回调处理，返回 (应答, 说明)，应答为 "success"/"fail"。

    验签：Authorization 头 RSA-SHA256 验签正文；成功后按 client_sn 推进订单。
    商户收到后回纯文本 "success"，收钱吧重试间隔 1s/5s/30s/600s。
    止重试策略：确定性失败（金额不符/订单不存在/terminal 不一致/state 非法/关单后到账）
    记 DB+告警后回 "success" 止血；可重试（验签/解析/落库异常）回 "fail"。
    """
    client = shouqianba.client
    if not client.verify_ready:
        logger.error("收钱吧未配置或公钥缺失，拒绝处理回调")
        return "fail", "sqb not configured"

    signature = _get_header(headers, "Authorization")
    if not signature or not signature.strip():
        logger.warning("回调缺少 Authorization 签名头")
        return "fail", "missing signature header"
    parts = signature.strip().split()
    if len(parts) != 2:
        logger.warning("回调 Authorization 格式非法（须为“{sn} {sign}”两段）：%s", (signature or "")[:80])
        return "fail", "invalid signature header"
    sn_part, sig_value = parts
    if not sig_value or sn_part.strip() != str(settings.SQB_TERMINAL_SN or "").strip():
        logger.warning("回调 terminal_sn 不一致 header=%s expected=%s", sn_part, settings.SQB_TERMINAL_SN)
        return "success", "terminal mismatch"
    if not client.verify_callback(raw_body, sig_value):
        logger.error("收钱吧回调验签失败")
        return "fail", "signature verification failed"

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.error("回调正文解析失败: %s", e)
        return "fail", f"invalid body: {e}"

    # 兼容新老字段：client_sn / total_amount / order_status|status
    data = body.get("biz_response", {}).get("data", {}) if isinstance(body.get("biz_response"), dict) else {}
    src = data if isinstance(data, dict) and data else body
    body_terminal = src.get("terminal_sn") or body.get("terminal_sn")
    if not body_terminal or str(body_terminal).strip() != str(settings.SQB_TERMINAL_SN or "").strip():
        logger.warning("回调正文 terminal_sn 缺失或不一致 body=%s expected=%s", body_terminal, settings.SQB_TERMINAL_SN)
        return "success", "terminal mismatch"
    client_sn = src.get("client_sn") or body.get("client_sn") or ""
    total_raw = src.get("total_amount", body.get("total_amount"))
    status = src.get("order_status") or src.get("status") or body.get("order_status") or body.get("status") or ""
    payload = {
        "order_status": str(status),
        "total_amount": normalize_amount(total_raw),
        "sn": src.get("sn") or body.get("sn"),
        "client_sn": client_sn,
        "terminal_sn": body_terminal,
    }

    # 非 PAID 通知：失败态关单（CREATED→CLOSED）、待定态记日志，均回 success（无需重试）
    if payload["order_status"] in shouqianba.FAILED_STATUSES:
        order = db.query(Order).filter(Order.out_trade_no == str(client_sn or "")).first()
        if order is not None and order.state == OrderState.CREATED.value:
            order.state = OrderState.CLOSED.value
            _append_fail_reason(order, f"sqb_notify:{payload['order_status']}")
            db.commit()
            logger.info("回调失败态关单 order_no=%s status=%s", order.order_no, payload["order_status"])
        else:
            logger.info("回调失败态无需处理 client_sn=%s status=%s", client_sn, payload["order_status"])
        return "success", ""
    if payload["order_status"] != PAID_STATUS:
        logger.info("回调非终态无需处理 client_sn=%s status=%s", client_sn, payload["order_status"])
        return "success", ""

    try:
        status_ret, message = apply_payment_result(
            db, str(client_sn or ""), payload, raw_body.decode("utf-8", errors="replace")
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.exception("回调落库失败: %s", e)
        return "fail", "apply failed"

    if status_ret in ("ok", "already"):
        logger.info("回调处理成功 status=%s client_sn=%s", status_ret, client_sn)
        return "success", ""
    if message in _DETERMINISTIC_FAILS or message.startswith("state="):
        # 确定性失败：已记 DB+日志，回 success 止血
        logger.error("回调确定性失败止血: %s client_sn=%s", message, client_sn)
        return "success", message
    logger.error("回调业务校验不通过: %s", message)
    return "fail", message


# 退款回调可识别的退款态（终态/处理中/失败）：命中即记录，不推进订单主状态（只记录可查，人工核账）
_REFUND_STATUSES = (
    shouqianba.REFUND_FINAL_STATUSES
    | shouqianba.REFUND_PENDING_STATUSES
    | shouqianba.REFUND_FAILED_STATUSES
)


def handle_refund_notify(db: Session, headers, raw_body: bytes) -> tuple[str, str]:
    """收钱吧退款结果回调处理，返回 (应答, 说明)，应答为 "success"/"fail"。

    语义（只记录可查）：验签通过后落一条 pay_state=REFUNDED 流水 + order.fail_reason 打标，
    不改 order.state，不解锁/不关单，后续人工核账。
    止重试策略：确定性失败（订单不存在/金额不符/terminal 不一致/非退款态）记日志后回
    "success" 止血；可重试（未配置公钥/缺签名/验签失败/正文解析失败/落库异常）回 "fail"。
    幂等：以收钱吧 sn 为 transaction_id，重复投递直接回 success。
    """
    client = shouqianba.client
    if not client.verify_ready:
        logger.error("收钱吧未配置或公钥缺失，拒绝处理退款回调")
        return "fail", "sqb not configured"

    signature = _get_header(headers, "Authorization")
    if not signature or not signature.strip():
        logger.warning("退款回调缺少 Authorization 签名头")
        return "fail", "missing signature header"
    parts = signature.strip().split()
    if len(parts) != 2:
        logger.warning("退款回调 Authorization 格式非法（须为“{sn} {sign}”两段）：%s", (signature or "")[:80])
        return "fail", "invalid signature header"
    sn_part, sig_value = parts
    if not sig_value or sn_part.strip() != str(settings.SQB_TERMINAL_SN or "").strip():
        logger.warning("退款回调 terminal_sn 不一致 header=%s expected=%s", sn_part, settings.SQB_TERMINAL_SN)
        return "success", "terminal mismatch"
    if not client.verify_callback(raw_body, sig_value):
        logger.error("收钱吧退款回调验签失败")
        return "fail", "signature verification failed"

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.error("退款回调正文解析失败: %s", e)
        return "fail", f"invalid body: {e}"

    # 兼容新老字段：client_sn / total_amount / order_status|status
    data = body.get("biz_response", {}).get("data", {}) if isinstance(body.get("biz_response"), dict) else {}
    src = data if isinstance(data, dict) and data else body
    body_terminal = src.get("terminal_sn") or body.get("terminal_sn")
    if not body_terminal or str(body_terminal).strip() != str(settings.SQB_TERMINAL_SN or "").strip():
        logger.warning("退款回调正文 terminal_sn 缺失或不一致 body=%s expected=%s", body_terminal, settings.SQB_TERMINAL_SN)
        return "success", "terminal mismatch"
    client_sn = str(src.get("client_sn") or body.get("client_sn") or "")
    total_raw = src.get("total_amount", body.get("total_amount"))
    status = str(src.get("order_status") or src.get("status") or body.get("order_status") or body.get("status") or "")
    sn = str(src.get("sn") or body.get("sn") or "")

    if status not in _REFUND_STATUSES:
        logger.info("退款回调非退款态无需记录 client_sn=%s status=%s", client_sn, status)
        return "success", f"not refund status: {status}"

    order = db.query(Order).filter(Order.out_trade_no == client_sn).first() if client_sn else None
    if order is None:
        logger.error("退款回调订单不存在 client_sn=%s status=%s", client_sn, status)
        return "success", "order not found"

    total_int = normalize_amount(total_raw)
    if total_int is not None and total_int != order.amount:
        logger.error("退款回调金额与订单不符：order_no=%s, sqb=%s, order=%s", order.order_no, total_raw, order.amount)
        _append_fail_reason(order, f"refund_amount_mismatch:{total_raw}")
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        return "success", "amount mismatch"

    txn_id = (sn or f"REFUND-{order.order_no}-{status}")[:64]
    try:
        existing = db.query(PayTransaction).filter(PayTransaction.transaction_id == txn_id).first()
        if existing is not None:
            logger.info("退款回调重复投递已记录 txn=%s client_sn=%s", txn_id, client_sn)
            return "success", "already processed"
        now = utcnow()
        _append_fail_reason(order, f"refund:{status} sn={sn}" if sn else f"refund:{status}")
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
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.exception("退款回调落库失败: %s", e)
        return "fail", "apply failed"

    logger.info("退款回调已记录 order_no=%s status=%s txn=%s", order.order_no, status, txn_id)
    return "success", ""
