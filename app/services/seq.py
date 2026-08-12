"""序列号生成：订单号 / 测算信息 ID。

订单号：S + YYYYMMDD（Asia/Shanghai）+ 3 位当日递增序列，全局唯一。
测算 ID：P + YYYYMMDD + 5 位当日递增序列。
时间字段统一 UTC，仅日期部分按业务时区 Asia/Shanghai 取。
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.profile import Profile

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _day_prefix() -> str:
    return datetime.now(SHANGHAI).strftime("%Y%m%d")


def next_order_no(db: Session) -> str:
    prefix = "S" + _day_prefix()
    count = db.query(func.count(Order.order_no)).filter(Order.order_no.like(prefix + "%")).scalar() or 0
    return f"{prefix}{count + 1:03d}"


def next_profile_id(db: Session) -> str:
    prefix = "P" + _day_prefix()
    count = db.query(func.count(Profile.id)).filter(Profile.id.like(prefix + "%")).scalar() or 0
    return f"{prefix}{count + 1:05d}"
