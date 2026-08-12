"""订单模型（ER: ORDERS）。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.session import Base


class OrderState(str, Enum):
    """订单状态机（见开发文档 §4.3）。"""

    CREATED = "CREATED"  # 下单成功
    PAID = "PAID"  # 回调验签成功
    UNLOCKED = "UNLOCKED"  # 完整报告解锁成功
    DELIVERED = "DELIVERED"  # 企微活码生成/展示
    ADDED_WECOM = "ADDED_WECOM"  # 用户扫码加企微
    CLOSED = "CLOSED"  # 超时关单/用户取消
    REFUNDING = "REFUNDING"  # 人工发起退款
    REFUNDED = "REFUNDED"  # 微信退款成功


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_profile_id", "profile_id"),
        Index("ix_orders_state", "state"),
    )

    order_no: Mapped[str] = mapped_column(String(32), primary_key=True, comment="S+YYYYMMDD+3位序列")
    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("profiles.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    out_trade_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="微信商户订单号=order_no")
    openid: Mapped[str | None] = mapped_column(String(64), nullable=True, default="")
    amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="金额（分）")
    state: Mapped[str] = mapped_column(String(16), nullable=False, default=OrderState.CREATED.value)
    pay_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="h5/native/jsapi")
    ad_params: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="磁力投放归因 JSON")
    fail_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
