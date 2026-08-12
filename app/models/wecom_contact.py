"""企业微信联系人模型（ER: WECOM_CONTACTS）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WecomContact(Base):
    __tablename__ = "wecom_contacts"
    __table_args__ = (Index("ix_wecom_contacts_order_no", "order_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), ForeignKey("orders.order_no"), nullable=False)
    external_userid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="活码 state 关联订单/渠道")
    add_flag: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
