"""测算信息模型（ER: PROFILES）。

生辰类字段一律加密存储（AES-256-GCM 密文，VARCHAR/Text），接口层负责脱敏，严禁明文落库。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.session import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="P+YYYYMMDD+5位序列")
    name_a: Mapped[str] = mapped_column(String(64), nullable=False)
    birth_a: Mapped[str] = mapped_column(Text, nullable=False, comment="甲方生辰密文")
    birth_hour_a: Mapped[str | None] = mapped_column(Text, nullable=True, comment="甲方时辰密文")
    name_b: Mapped[str] = mapped_column(String(64), nullable=False)
    birth_b: Mapped[str] = mapped_column(Text, nullable=False, comment="乙方生辰密文")
    birth_hour_b: Mapped[str | None] = mapped_column(Text, nullable=True, comment="乙方时辰密文")
    is_lunar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    combo_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="测算因子密文（JSON）")
    preview_report: Mapped[str | None] = mapped_column(Text, nullable=True, comment="预览报告 JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
