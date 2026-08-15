"""交付任务模型（ER: DELIVERY_TASKS）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.session import Base


class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"
    __table_args__ = (Index("ix_delivery_tasks_order_no", "order_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), ForeignKey("orders.order_no"), nullable=False)
    task_state: Mapped[str | None] = mapped_column(String(16), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
