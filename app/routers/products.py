"""商品模块路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.core.response import ok_response
from app.db.session import get_db
from app.models.product import Product

router = APIRouter(tags=["products"])

MAX_PAGE_SIZE = 100


def _serialize(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "type": product.type,
        "freeFlag": product.free_flag,
        "status": product.status,
    }


@router.get("/api/products")
def list_products(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    type: int | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """产品列表：仅返回 status=1 启用产品，支持 type 过滤与分页。"""
    query = db.query(Product).filter(Product.status == 1)
    if type is not None:
        query = query.filter(Product.type == type)
    total = query.count()
    items = query.order_by(Product.id.asc()).offset((page - 1) * pageSize).limit(pageSize).all()
    return ok_response(
        {
            "list": [_serialize(p) for p in items],
            "total": total,
            "page": page,
            "pageSize": pageSize,
        }
    )


@router.get("/api/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)) -> dict:
    """产品详情：不存在或已下架返回 13001（HTTP 404）。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None or product.status != 1:
        raise BizError(ErrorCode.PRODUCT_NOT_FOUND, "产品不存在或已下架")
    return ok_response(_serialize(product))
