"""服务端幂等：Idempotency-Key（24 小时同键返回首次结果）。

记录存 DB（IdempotencyRecord），主键 key = scope:Idempotency-Key，避免跨接口复用冲突。
幂等键现绑定 payload hash，防同 Key 复用不同参数导致计费错乱。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.models.idempotency import IdempotencyRecord

IDEMPOTENCY_TTL = timedelta(hours=24)

# 接口作用域，隔离 profile 与 order 两类幂等键
IDEM_SCOPE_PROFILE = "profile:create"
IDEM_SCOPE_ORDER = "order:create"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _pk(key: str | None, scope: str) -> str | None:
    if not key:
        return None
    return f"{scope}:{key}"


def hash_payload(payload: dict | None) -> str | None:
    """对 payload 做规范化 hash，用于幂等键绑定；None 返回 None。"""
    if payload is None:
        return None
    try:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        canonical = str(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _unwrap_response(raw: str) -> tuple[dict, str | None]:
    """兼容旧格式：若存储为 wrapper {"__data":..., "__hash":...} 则拆包，否则视为旧数据无 hash。"""
    try:
        obj = json.loads(raw)
    except Exception:
        return {}, None
    if isinstance(obj, dict) and "__data" in obj and "__hash" in obj:
        return obj["__data"], obj["__hash"]
    return obj, None


def _wrap_response(response: dict, payload_hash: str | None) -> str:
    if payload_hash is None:
        return json.dumps(response, ensure_ascii=False)
    return json.dumps({"__data": response, "__hash": payload_hash}, ensure_ascii=False)


def get_idempotent_response(
    db: Session, key: str | None, scope: str, payload_hash: str | None = None
):
    """命中 24 小时内同 scope 键返回首次结果 data，否则 None。

    若传入 payload_hash 且与存储不一致，抛 409 冲突（防同 Key 不同参数复用）。
    """
    pk = _pk(key, scope)
    if pk is None:
        return None
    rec = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == pk).first()
    if rec is None:
        return None
    if _now() - rec.created_at > IDEMPOTENCY_TTL:
        return None
    data, stored_hash = _unwrap_response(rec.response)
    if payload_hash is not None and stored_hash is not None and payload_hash != stored_hash:
        raise BizError(ErrorCode.CONFLICT, "Idempotency-Key 已使用但请求参数不一致")
    return data


def store_idempotent_response(
    db: Session, key: str | None, scope: str, response: dict, payload_hash: str | None = None
) -> None:
    """记录首次结果 data（调用方负责 commit）。若提供 payload_hash 则一并绑定。"""
    pk = _pk(key, scope)
    if pk is None:
        return
    wrapped = _wrap_response(response, payload_hash)
    rec = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == pk).first()
    if rec is None:
        db.add(IdempotencyRecord(key=pk, scope=scope, response=wrapped))
    else:
        rec.response = wrapped
        rec.created_at = _now()
