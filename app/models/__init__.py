"""数据模型注册入口：导入即注册全部表到 Base.metadata。"""

from __future__ import annotations

from app.models.delivery_task import DeliveryTask
from app.models.idempotency import IdempotencyRecord
from app.models.order import Order, OrderState
from app.models.pay_transaction import PayTransaction
from app.models.product import Product
from app.models.profile import Profile
from app.models.refund import Refund
from app.models.report import Report
from app.models.wecom_contact import WecomContact

__all__ = [
    "DeliveryTask",
    "IdempotencyRecord",
    "Order",
    "OrderState",
    "PayTransaction",
    "Product",
    "Profile",
    "Refund",
    "Report",
    "WecomContact",
]
