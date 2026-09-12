"""限时0元促销：运行时有效价覆盖（不改 DB 原价，关闭即恢复）。

开启条件：FREE_PROMO_ENABLED=true + product.id 在名单内 + 未超过 END_AT。
END_AT 为 UTC ISO8601 字符串（为空则不限时）；解析失败视为不过期（fail-open 偏向促销？
否——解析失败视为已过期，偏向收费，避免误免费）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings


def _parse_end_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        text = raw.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def is_free_promo_active(product_id: int, now: datetime | None = None) -> bool:
    """名单内产品在促销窗口内是否 0 元。"""
    if not settings.FREE_PROMO_ENABLED:
        return False
    if product_id not in (settings.FREE_PROMO_PRODUCT_IDS or []):
        return False
    end_at = _parse_end_at(settings.FREE_PROMO_END_AT)
    if end_at is None:
        # 无截止时间：只要开关开即生效；END_AT 非空但解析失败 → _parse_end_at 返回 None
        # 无法区分两者，此处以开关为准（配置错误时测试与日志可发现）
        if settings.FREE_PROMO_END_AT:
            return False
        return True
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current <= end_at


def get_effective_price(product) -> int:
    """促销命中返回 0，否则返回 DB 原价。"""
    try:
        if is_free_promo_active(int(product.id)):
            return 0
    except (AttributeError, TypeError, ValueError):
        pass
    return int(product.price)
