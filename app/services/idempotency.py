"""服务端幂等：Idempotency-Key（24 小时同键返回首次结果）。

记录存 DB（IdempotencyRecord），主键 key = scope:Idempotency-Key，避免跨接口复用冲突。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

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


def get_idempotent_response(db: Session, key: str | None, scope: str):
    """命中 24 小时内同 scope 键返回首次结果 data，否则 None。"""
    pk = _pk(key, scope)
    if pk is None:
        return None
    rec = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == pk).first()
    if rec is None:
        return None
    if _now() - rec.created_at > IDEMPOTENCY_TTL:
        return None
    return json.loads(rec.response)


def store_idempotent_response(db: Session, key: str | None, scope: str, response: dict) -> None:
    """记录首次结果 data（调用方负责 commit）。"""
    pk = _pk(key, scope)
    if pk is None:
        return
    rec = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == pk).first()
    if rec is None:
        db.add(IdempotencyRecord(key=pk, scope=scope, response=json.dumps(response, ensure_ascii=False)))
    else:
        rec.response = json.dumps(response, ensure_ascii=False)
        rec.created_at = _now()
