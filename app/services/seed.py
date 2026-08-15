"""开发种子数据：启动时（dev）或测试夹具调用，幂等。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.product import Product

SEED_PRODUCTS = [
    {"name": "姻缘测算完整报告", "price": 9900, "type": 1, "free_flag": 0, "status": 1},
    {"name": "姻缘测算免费版", "price": 0, "type": 0, "free_flag": 1, "status": 1},
]


def seed_products(db: Session) -> None:
    """已存在产品则跳过，否则写入付费档 + 免费档占位产品。"""
    if db.query(Product).first() is not None:
        return
    db.add_all(Product(**item) for item in SEED_PRODUCTS)
    db.commit()
