"""支付流水模型（ER: PAY_TRANSACTIONS）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PayTransaction(Base):
    __tablename__ = "pay_transactions"
    __table_args__ = (Index("ix_pay_transactions_order_no", "order_no"),)

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), ForeignKey("orders.order_no"), nullable=False)
    pay_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    pay_state: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_callback: Mapped[str | None] = mapped_column(Text, nullable=True)
    callback_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
