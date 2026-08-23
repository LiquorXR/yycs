"""条件限流：仅对 IP:8000 直连请求生效，域名经 NPM 不限流保峰值。"""

from __future__ import annotations

import ipaddress
import logging
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.errors import ErrorCode

logger = logging.getLogger(__name__)

# Docker/内网信任网段：来自这些段的 remote_addr 视为经 NPM 转发（可信代理）
_TRUSTED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

# 直连不作限流的路径（健康检查/静态探测等）
_EXEMPT_PATHS = {"/api/health"}

# 16KB 请求体上限（仅直连场景）
_MAX_BODY_BYTES = 16 * 1024


def _is_trusted_proxy_ip(ip_str: str) -> bool:
    if ip_str in ("testclient", "testserver"):
        return True
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in _TRUSTED_NETWORKS)


def _get_allowed_hosts() -> set[str]:
    hosts: set[str] = {"www.sxzfcm.top", "sxzfcm.top", "127.0.0.1", "localhost", "testserver"}
    for origin in settings.CORS_ORIGINS:
        try:
            from urllib.parse import urlparse

            h = urlparse(origin).hostname
            if h:
                hosts.add(h.lower())
        except Exception:
            continue
    return hosts


_ALLOWED_HOSTS = _get_allowed_hosts()


def _is_direct_ip(request: Request) -> bool:
    """判直连 IP：Host 为 IP/未知 且非可信代理的域名回环则视为直连。"""
    host_header = (request.headers.get("host") or "").split(":")[0].strip().lower()
    client_ip = request.client.host if request.client else ""
    # 测试/本地回环探活放行
    if host_header in ("testserver",):
        return False
    if host_header in ("127.0.0.1", "localhost") and _is_trusted_proxy_ip(client_ip):
        return False
    # 域名经可信代理（NPM docker 网段）→ 不算直连
    if host_header in _ALLOWED_HOSTS:
        return not _is_trusted_proxy_ip(client_ip)
    # 其余：Host 为公网 IP 或未知 → 直连
    return True


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        # 粗粒度锁：限流路径为轻量内存操作，不走 DB
        import threading

        self._lock = threading.Lock()

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        with self._lock:
            dq = self._buckets[key]
            while dq and dq[0] <= now - window:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append(now)
            # 惰性清理空桶由后续命中触发
            return True


limiter = SlidingWindowLimiter()


def _limit_for(request: Request) -> tuple[int, int] | None:
    """返回 (limit, window_seconds)；None 表示不限流。"""
    path = request.url.path
    method = request.method
    if path in _EXEMPT_PATHS:
        return None
    # 仅 API 前缀参与限流，静态 SPA 不限
    if not path.startswith("/api/"):
        return None
    if method == "POST" and path == "/api/profiles":
        return (settings.RATE_LIMIT_IP_PROFILE, 60)
    if method == "POST" and path == "/api/orders":
        return (settings.RATE_LIMIT_IP_ORDERS, 60)
    if path.startswith("/api/profiles/") or path.startswith("/api/orders/") or path.startswith("/api/pay/"):
        return (settings.RATE_LIMIT_IP_QUERY, 60)
    return None


class ConditionalRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # 直连请求体上限（防 JSON 炸弹），在限流前拦截
        if _is_direct_ip(request):
            clen = request.headers.get("content-length")
            if clen is not None:
                try:
                    if int(clen) > _MAX_BODY_BYTES:
                        return JSONResponse(
                            status_code=413,
                            content={"code": ErrorCode.PARAM_VALIDATION, "message": "请求体过大", "data": None},
                        )
                except ValueError:
                    pass
            limit_cfg = _limit_for(request)
            if limit_cfg is not None:
                limit, window = limit_cfg
                # 直连场景忽略 X-Forwarded-For（可被伪造分散桶），以 TCP 源 IP 为准
                client_ip = request.client.host if request.client else "unknown"
                key = f"{client_ip}:{request.method}:{request.url.path.split('?')[0][:64]}"
                # 细化：GET 带参按桶前缀聚合，避免每个 order_no 单独桶
                if request.method == "GET" and request.url.path.startswith("/api/"):
                    # 按 /api/orders /api/profiles /api/pay 前缀聚合
                    prefix = request.url.path.split("/")[2] if len(request.url.path.split("/")) > 2 else "other"
                    key = f"{client_ip}:GET:/api/{prefix}"
                if not limiter.is_allowed(key, limit, window):
                    logger.warning("直连限流触发 ip=%s %s %s", client_ip, request.method, request.url.path)
                    return JSONResponse(
                        status_code=429,
                        content={"code": ErrorCode.RATE_LIMITED, "message": "请求过于频繁，请稍后重试", "data": None},
                    )
        return await call_next(request)
