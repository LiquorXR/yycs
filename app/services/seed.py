"""开发种子数据：启动时（dev）或测试夹具调用，幂等。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.product import Product

SEED_PRODUCTS = [
    {"name": "姻缘测算·正缘完整报告", "price": 990, "type": 1, "free_flag": 0, "status": 1},
    {"name": "姻缘测算·正缘预览（免费版）", "price": 0, "type": 0, "free_flag": 1, "status": 1},
]


def seed_products(db: Session) -> None:
    """已存在产品则跳过，否则写入付费档 + 免费档占位产品；旧库自动更名/改价兼容。"""
    existing = db.query(Product).all()
    if existing:
        # 兼容旧数据：名称 -> 姻缘测算·正缘完整报告；价格 9900(99元) -> 990(9.9元)
        updated = False
        for prod in existing:
            if prod.name == "单人测算报告":
                prod.name = "姻缘测算·正缘完整报告"
                updated = True
            elif prod.name == "单人测算报告（免费版）":
                prod.name = "姻缘测算·正缘预览（免费版）"
                updated = True
            elif prod.name == "姻缘测算完整报告":
                prod.name = "姻缘测算·正缘完整报告"
                updated = True
            elif prod.name == "姻缘测算免费版":
                prod.name = "姻缘测算·正缘预览（免费版）"
                updated = True
            elif "单人测算" in prod.name:
                prod.name = prod.name.replace("单人测算报告", "姻缘测算·正缘完整报告").replace("单人测算", "姻缘测算")
                updated = True
            # 价格兼容：旧 99 元档统一降为 9.9 元
            if prod.price == 9900:
                prod.price = 990
                updated = True
        if updated:
            db.commit()
        return
    db.add_all(Product(**item) for item in SEED_PRODUCTS)
    db.commit()
