"""商品模型（ER: PRODUCTS）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, comment="价格（单位：分，禁止浮点）")
    type: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="0-免费档 1-付费档")
    free_flag: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="1-免费 0-付费")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="0-禁用（下架） 1-启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
