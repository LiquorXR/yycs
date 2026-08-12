"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import BizError, ErrorCode
from app.core.response import ok_response
from app.routers import health, orders, products, profiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动钩子：dev 环境自动建表 + 种子产品（生产走 alembic 迁移）。"""
    if settings.APP_ENV == "dev":
        import app.models  # noqa: F401  确保模型注册到 Base.metadata
        from app.db.session import Base, SessionLocal, engine
        from app.services.seed import seed_products

        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_products(db)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    """业务异常：错误码映射到对应 HTTP 状态码。"""
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI 参数类型校验失败：统一信封返回 400 + 10001。"""
    return JSONResponse(
        status_code=400,
        content={"code": ErrorCode.PARAM_VALIDATION, "message": "参数校验失败", "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常：统一返回 50000 服务器内部错误。"""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": ErrorCode.INTERNAL_ERROR,
            "message": "服务器内部错误",
            "data": None,
        },
    )


app.include_router(health.router)
app.include_router(products.router)
app.include_router(profiles.router)
app.include_router(orders.router)
