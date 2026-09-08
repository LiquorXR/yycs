"""对账/补偿：扫描超时未推送订单调用微信小店查单，按结果推进状态。

- 每 5 分钟扫描创建超过 30 分钟仍为 CREATED 的订单（阈值可配）。
- 查单结果已完成（state=1）→ 走支付结果推进（CAS 解锁报告，恰好一次）。
- 微信小店侧已取消（state=2）→ 本地订单置 CLOSED 并记录原因。
- 仍待支付（state=0/空）→ 保持 CREATED，下轮再查。
- 后台线程在 lifespan 中启动（RECONCILE_ENABLED 开启时）；dev 默认关闭。
- 多 worker（uvicorn --workers N）下用文件锁保证仅一个进程跑对账。
- 每日顺带清理 24h 前幂等记录，防 idempotency_records 无限增长。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutil import iso_utc, utcnow
from app.db.session import SessionLocal
from app.models.idempotency import IdempotencyRecord
from app.models.order import Order, OrderState
from app.services import pay_service
from app.services.idempotency import IDEMPOTENCY_TTL
from app.services.wxstore import (
    PREORDER_CANCELED,
    PREORDER_DONE,
    PREORDER_PENDING,
    WxstoreError,
)

logger = logging.getLogger(__name__)

# 单次对账扫描上限：200×10s 最坏 33min 会超过 5min 周期，收紧到 60 单 + 5s 单订单超时
_RECONCILE_BATCH_LIMIT = 60
_RECONCILE_QUERY_TIMEOUT_S = 5.0

# 幂等记录清理：每日一次，删除超过 TTL(24h) 的过期键
_IDEM_CLEANUP_INTERVAL = 86400

# 对账指标落库键（复用 idempotency_records 表，多 worker 下 health 读库取一致值）
_METRICS_KEY = "reconcile:metrics"
_METRICS_SCOPE = "reconcile:metrics"

try:
    import fcntl
except ImportError:  # Windows 本地开发无 fcntl，单进程运行无需锁
    fcntl = None  # type: ignore[assignment]

_last_idem_cleanup: float = 0.0
_lock_file: object | None = None


def reconcile_once(db: Session) -> dict:
    """单次对账：返回 {checked, success, closed, pending, error, dead, paid_after_close} 汇总。"""
    cutoff = utcnow() - timedelta(minutes=settings.RECONCILE_STALE_MINUTES)
    orders = (
        db.query(Order)
        .filter(
            Order.state == OrderState.CREATED.value,
            Order.created_at < cutoff,
            # 死信排除：金额异常/缺字段已转人工，不再每轮重查（NULL 需显式保留）
            or_(Order.fail_reason.is_(None), ~Order.fail_reason.like("reconcile_dead%")),
        )
        .order_by(Order.created_at.asc())
        .limit(_RECONCILE_BATCH_LIMIT)
        .all()
    )
    summary = {"checked": 0, "success": 0, "closed": 0, "pending": 0, "error": 0, "dead": 0, "paid_after_close": 0}
    for order in orders:
        if not order.pre_order_id:
            # 微信小店未配置下降级建单（无预订单号）：跳过本轮，不计 checked
            continue
        try:
            result = pay_service.wxstore.client.query_pre_order(order.pre_order_id, timeout=_RECONCILE_QUERY_TIMEOUT_S)
        except WxstoreError as e:
            logger.warning("查单失败：order_no=%s, %s", order.order_no, e)
            summary["error"] += 1
            continue

        summary["checked"] += 1
        order_state = result.get("state", "")
        if order_state == PREORDER_DONE:
            payload = {
                "order_sn": result.get("order_sn"),
                "order_signature": None,
                "amount": result.get("amount"),
                "pre_order_id": order.pre_order_id,
            }
            status, message = pay_service.apply_payment_result(db, str(order.pre_order_id), payload, raw_callback=None)
            if status == "ok":
                summary["success"] += 1
            elif status == "already":
                summary["success"] += 1
            elif message == "amount mismatch" or result.get("amount") is None:
                # 金额异常转死信人工核账，不再重查
                pay_service._append_fail_reason(order, f"reconcile_dead:{message}")
                logger.error("查单金额异常转死信：order_no=%s, %s", order.order_no, message)
                summary["dead"] += 1
            else:
                logger.error("查单推进失败：order_no=%s, %s", order.order_no, message)
                summary["error"] += 1
        elif order_state == PREORDER_CANCELED:
            order.state = OrderState.CLOSED.value
            pay_service._append_fail_reason(order, "微信小店查单: 已取消")
            summary["closed"] += 1
        elif order_state == PREORDER_PENDING or not order_state:
            summary["pending"] += 1
        else:
            # 未知状态记原因+计数告警，转死信避免无限查单
            pay_service._append_fail_reason(order, f"reconcile_dead:unknown={order_state}")
            logger.error("查单未知状态转死信：order_no=%s, %s", order.order_no, order_state)
            summary["dead"] += 1
        db.commit()

    try:
        summary["paid_after_close"] = (
            db.query(Order)
            .filter(Order.state == OrderState.CLOSED.value, Order.fail_reason.like("paid_after_close%"))
            .count()
        )
    except Exception:  # noqa: BLE001 指标缺失不影响主流程
        logger.warning("paid_after_close 计数失败", exc_info=True)

    if summary["checked"] or summary["paid_after_close"]:
        logger.info("对账完成：%s", summary)
    return summary


def _persist_reconcile_metrics(db: Session, summary: dict) -> None:
    """对账指标写入 idempotency_records（key 唯一，覆盖更新），供 /api/health 跨 worker 读取。"""
    record = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == _METRICS_KEY).first()
    now = utcnow()
    response = json.dumps({"at": iso_utc(now), "summary": summary}, ensure_ascii=False)
    if record is not None:
        record.response = response
        record.created_at = now
    else:
        db.add(IdempotencyRecord(key=_METRICS_KEY, scope=_METRICS_SCOPE, response=response, created_at=now))
    db.commit()


def _cleanup_idempotency(db: Session) -> None:
    """清理超过 TTL 的幂等记录（24h），防表无限增长。"""
    global _last_idem_cleanup
    now = time.monotonic()
    if now - _last_idem_cleanup < _IDEM_CLEANUP_INTERVAL:
        return
    _last_idem_cleanup = now
    cutoff = utcnow() - IDEMPOTENCY_TTL
    result = db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.created_at < cutoff))
    db.commit()
    if result.rowcount:
        logger.info("清理过期幂等记录 %s 条", result.rowcount)


_loop_running = False


def _loop() -> None:
    """后台线程主循环：休眠周期后执行一次对账 + 每日幂等清理 + 指标落库（防重叠执行）。"""
    global _loop_running
    interval = max(10, settings.RECONCILE_INTERVAL_SECONDS)
    while True:
        time.sleep(interval)
        if _loop_running:
            logger.warning("上一轮对账仍在执行，跳过本轮")
            continue
        _loop_running = True
        try:
            with SessionLocal() as db:
                summary = reconcile_once(db)
                _persist_reconcile_metrics(db, summary)
                _cleanup_idempotency(db)
        except Exception:  # noqa: BLE001
            logger.exception("对账任务异常，下轮重试")
        finally:
            _loop_running = False


def _reconcile_lock_path() -> Path:
    """锁文件与 DB 同目录，多 worker 共享同一数据卷时互斥生效。"""
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        db_path = url[len("sqlite:///"):]
    else:
        db_path = "app.db"
    return Path(db_path).resolve().parent / "reconcile.lock"


def _acquire_reconcile_lock() -> bool:
    """尝试获取进程级文件锁；失败说明其他 worker 已在跑对账。"""
    global _lock_file
    if fcntl is None:
        return True
    lock_path = _reconcile_lock_path()
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _lock_file = open(lock_path, "a+")
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        logger.info("其他 worker 已持有对账锁，本进程不启动对账")
        return False


def start_reconcile_loop() -> threading.Thread | None:
    """启动对账后台线程（daemon）；开关关闭或支付未配置时不启动。"""
    if not settings.RECONCILE_ENABLED:
        logger.info("对账任务未开启（RECONCILE_ENABLED=false）")
        return None
    if not pay_service.wxs_ready():
        logger.warning("微信小店未配置，对账任务不启动")
        return None
    if not _acquire_reconcile_lock():
        return None
    thread = threading.Thread(target=_loop, name="pay-reconcile", daemon=True)
    thread.start()
    logger.info("对账任务已启动（周期 %ss，阈值 %s 分钟）", settings.RECONCILE_INTERVAL_SECONDS, settings.RECONCILE_STALE_MINUTES)
    return thread
