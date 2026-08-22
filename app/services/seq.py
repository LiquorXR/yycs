"""序列号生成：订单号 / 测算信息 ID。

订单号：S + YYYYMMDD（Asia/Shanghai）+ 10 位随机HEX(40bit)，全局唯一，防枚举。
测算 ID：P + YYYYMMDD + 10 位随机HEX(40bit)。
时间字段统一 UTC，仅日期部分按业务时区 Asia/Shanghai 取。
"""

from __future__ import annotations

import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.profile import Profile

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _day_prefix() -> str:
    return datetime.now(SHANGHAI).strftime("%Y%m%d")


def next_order_no(db: Session) -> str:
    """生成不可预测订单号：S + YYYYMMDD + 10位随机HEX(40bit)，碰撞重试。"""
    prefix = "S" + _day_prefix()
    for _ in range(5):
        rand = secrets.token_hex(5).upper()  # 10 hex chars, 40bit
        candidate = f"{prefix}{rand}"
        exists = db.query(Order).filter(Order.order_no == candidate).first()
        if not exists:
            return candidate
    # 极小概率5次碰撞，兜底用更长随机
    return f"{prefix}{secrets.token_hex(6).upper()}"


def next_profile_id(db: Session) -> str:
    """生成不可预测档案ID：P + YYYYMMDD + 10位随机HEX(40bit)，碰撞重试。"""
    prefix = "P" + _day_prefix()
    for _ in range(5):
        rand = secrets.token_hex(5).upper()  # 10 hex chars
        candidate = f"{prefix}{rand}"
        exists = db.query(Profile).filter(Profile.id == candidate).first()
        if not exists:
            return candidate
    return f"{prefix}{secrets.token_hex(8).upper()}"
