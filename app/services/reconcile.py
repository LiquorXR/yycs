"""对账/补偿：扫描超时未回调订单调用微信查单，按结果推进状态。

- 每 5 分钟扫描创建超过 30 分钟仍为 CREATED 的订单（阈值可配）。
- 查单结果 SUCCESS → 走支付结果推进（CAS 解锁报告，恰好一次）。
- 微信侧已关单/支付错误 → 本地订单置 CLOSED 并记录原因。
- 仍待支付（NOTPAY 等）→ 保持 CREATED，下轮再查。
- 后台线程在 lifespan 中启动（RECONCILE_ENABLED 开启时）；dev 默认关闭。
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutil import utcnow
from app.db.session import SessionLocal
from app.models.order import Order, OrderState
from app.services import pay_service
from app.services.wechatpay import WechatPayError

logger = logging.getLogger(__name__)

# 微信查单结果中应落 CLOSED 的状态（用户未支付且已过期/异常）
_CLOSED_TRADE_STATES = {"CLOSED", "PAYERROR", "REVOKED"}


def reconcile_once(db: Session) -> dict:
    """单次对账：返回 {checked, success, closed, pending, error} 汇总。"""
    cutoff = utcnow() - timedelta(minutes=settings.RECONCILE_STALE_MINUTES)
    orders = (
        db.query(Order)
        .filter(Order.state == OrderState.CREATED.value, Order.created_at < cutoff)
        .order_by(Order.created_at.asc())
        .limit(200)
        .all()
    )
    summary = {"checked": 0, "success": 0, "closed": 0, "pending": 0, "error": 0}
    for order in orders:
        try:
            result = pay_service.wechatpay.client.query_order(order.out_trade_no)
        except WechatPayError as e:
            logger.warning("查单失败：order_no=%s, %s", order.order_no, e)
            summary["error"] += 1
            continue

        summary["checked"] += 1
        trade_state = result.get("trade_state", "")
        if trade_state == "SUCCESS":
            status, message = pay_service.apply_payment_result(db, order.out_trade_no, result, raw_callback=None)
            if status == "ok":
                summary["success"] += 1
            elif status == "already":
                summary["success"] += 1
            else:
                logger.error("查单推进失败：order_no=%s, %s", order.order_no, message)
                summary["error"] += 1
        elif trade_state in _CLOSED_TRADE_STATES:
            order.state = OrderState.CLOSED.value
            order.fail_reason = f"微信查单: {trade_state}"
            summary["closed"] += 1
        else:
            summary["pending"] += 1
        db.commit()

    if summary["checked"]:
        logger.info("对账完成：%s", summary)
    return summary


def _loop() -> None:
    """后台线程主循环：休眠周期后执行一次对账。"""
    interval = max(10, settings.RECONCILE_INTERVAL_SECONDS)
    while True:
        time.sleep(interval)
        try:
            with SessionLocal() as db:
                reconcile_once(db)
        except Exception:  # noqa: BLE001
            logger.exception("对账任务异常，下轮重试")


def start_reconcile_loop() -> threading.Thread | None:
    """启动对账后台线程（daemon）；开关关闭或支付未配置时不启动。"""
    if not settings.RECONCILE_ENABLED:
        logger.info("对账任务未开启（RECONCILE_ENABLED=false）")
        return None
    if not pay_service.wx_ready():
        logger.warning("微信支付未配置，对账任务不启动")
        return None
    thread = threading.Thread(target=_loop, name="pay-reconcile", daemon=True)
    thread.start()
    logger.info("对账任务已启动（周期 %ss，阈值 %s 分钟）", settings.RECONCILE_INTERVAL_SECONDS, settings.RECONCILE_STALE_MINUTES)
    return thread