"""订单服务：创建订单（校验、序列号、状态）。

金额一律以服务端产品表为准，杜绝前端改价；请求携带 amount 且不一致返回 12001。
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.models.order import Order, OrderState
from app.models.product import Product
from app.models.profile import Profile
from app.services.promo import get_effective_price
from app.services.seq import next_order_no


def create_order(
    db: Session,
    profile_id: str,
    product_id: int,
    payment_method: str = "auto",
    ad_params: dict | None = None,
    amount_from_request: int | None = None,
) -> tuple[str, int]:
    """创建订单，返回 (order_no, amount)。profile/product 不存在或金额不符抛业务异常。"""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if profile is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")

    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None or product.status != 1:
        raise BizError(ErrorCode.PRODUCT_NOT_FOUND, "产品不存在或已下架")

    # 限时0元促销：有效价运行时覆盖，DB 原价不动（关闭即恢复）；
    # 促销期请求可带 0 或原价，皆视为合法，防旧缓存金额误杀。
    effective_price = get_effective_price(product)
    if amount_from_request is not None and amount_from_request not in (effective_price, product.price):
        raise BizError(ErrorCode.AMOUNT_INVALID, "金额校验失败")

    for _ in range(5):
        order_no = next_order_no(db)
        order = Order(
            order_no=order_no,
            profile_id=profile_id,
            product_id=product.id,
            out_trade_no=order_no,
            openid="",
            amount=effective_price,
            state=OrderState.CREATED.value,
            pay_type=payment_method,
            ad_params=ad_params,
        )
        db.add(order)
        try:
            db.commit()
            return order_no, effective_price
        except IntegrityError:
            # 序列号并发冲突，重试
            db.rollback()
    raise BizError(ErrorCode.INTERNAL_ERROR, "订单号生成冲突，请重试")
