"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import BizError, ErrorCode
from app.routers import health, orders, pay, products, profiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动钩子：dev 环境自动建表 + 种子产品（生产走 alembic 迁移）；启动对账后台任务。"""
    if settings.APP_ENV == "dev":
        import app.models  # noqa: F401  确保模型注册到 Base.metadata
        from app.db.session import Base, SessionLocal, engine
        from app.services.seed import seed_products

        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_products(db)

    from app.services.reconcile import start_reconcile_loop

    start_reconcile_loop()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "Wechatpay-*", "X-Requested-With"],
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
app.include_router(pay.router)

# 生产静态托管：backend 容器内直接托管前端构建产物，nginx 仅反代 127.0.0.1:8000。
# 必须在全部 API 路由注册之后追加 catch-all；dev/测试用 Vite，目录不存在时静默跳过。
_DIST_DIR = Path(settings.FRONTEND_DIST_DIR)
# 防御环境变量注入劫持为 "/" 导致任意文件读取
try:
    _dist_resolved = _DIST_DIR.resolve()
    if _dist_resolved == Path("/").resolve():
        logger.warning("FRONTEND_DIST_DIR 非法为根路径，已禁用静态托管")
        _DIST_DIR = Path("/nonexistent_dist_disabled")
    else:
        # 仅允许 /app 或当前工作目录下的路径
        _allowed_roots = {Path("/app").resolve(), Path.cwd().resolve()}
        if not any(
            _dist_resolved == r or _dist_resolved.is_relative_to(r)  # type: ignore[attr-defined]
            for r in _allowed_roots
        ):
            logger.warning("FRONTEND_DIST_DIR 非法路径 %s，已禁用静态托管", _DIST_DIR)
            _DIST_DIR = Path("/nonexistent_dist_disabled")
except Exception:
    pass


def _json_404() -> JSONResponse:
    """API/文档前缀命中 catch-all 时返回 JSON 404，保留 API 语义。"""
    return JSONResponse(
        status_code=404,
        content={"code": ErrorCode.NOT_FOUND, "message": "资源不存在", "data": None},
    )


if _DIST_DIR.is_dir():
    _assets_dir = _DIST_DIR / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}", response_model=None, include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 保 API 语义：/api、/docs 精确路径及 api/、docs/、openapi.json 前缀不得回退 index.html
        if full_path in ("api", "docs") or full_path.startswith(("api/", "docs/", "openapi.json")):
            return _json_404()

        # 命中 dist 下真实文件（favicon.svg、icons.svg 等）直接返回
        target = (_DIST_DIR / full_path).resolve()
        if target.is_file() and target.is_relative_to(_DIST_DIR.resolve()):
            return FileResponse(target)

        # SPA fallback：/、/calc、/order、/pay/:orderNo、/report/:orderNo 等
        index_file = _DIST_DIR / "index.html"
        if index_file.is_file():
            return FileResponse(index_file, media_type="text/html")

        return _json_404()
