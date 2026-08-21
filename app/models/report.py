"""报告模型（ER: REPORTS）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(String(32), ForeignKey("profiles.id"), nullable=False, index=True)
    order_no: Mapped[str | None] = mapped_column(String(32), ForeignKey("orders.order_no"), nullable=True)
    full_report: Mapped[str | None] = mapped_column(Text, nullable=True, comment="完整报告内容/URL")
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="locked", comment="locked/unlocked")
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
