"""测算模块路由：提交测算信息、重新获取预览报告。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.core.errors import BizError, ErrorCode
from app.core.response import ok_response
from app.db.session import get_db
from app.models.profile import Profile
from app.models.report import Report
from app.services.divination import generate_factors, generate_preview_report, validate_profile_input
from app.services.idempotency import IDEM_SCOPE_PROFILE, get_idempotent_response, store_idempotent_response
from app.services.report import generate_single_report
from app.services.seq import next_profile_id

router = APIRouter(tags=["profiles"])

_PREVIEW_FIELDS = ("title", "locked", "lockedNote")


class ProfileCreateRequest(BaseModel):
    name: str
    birth: str
    birthHour: str | None = None
    isLunar: bool = False
    focusTags: list[str] | None = Field(default=None, description="正缘桃花期/婚后财运旺衰/性格解析/事业运势/避坑锦囊")


def _preview_view(preview: dict) -> dict:
    """对外预览视图：仅暴露 title/locked/lockedNote（不含 summary）。"""
    return {k: preview.get(k) for k in _PREVIEW_FIELDS}


@router.post("/api/profiles")
def create_profile(
    payload: ProfileCreateRequest,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    """提交测算信息：校验 → 生辰加密落库 → 生成预览报告（免费，掩码）。"""
    cached = get_idempotent_response(db, idempotency_key, IDEM_SCOPE_PROFILE)
    if cached is not None:
        return ok_response(cached)

    validate_profile_input(payload.name, payload.birth, payload.birthHour, payload.isLunar)

    profile_id = next_profile_id(db)
    factors = generate_factors(payload.name, payload.birth, payload.birthHour, payload.isLunar)
    preview = generate_preview_report(factors)
    report_contract = generate_single_report(factors, payload.focusTags)

    profile = Profile(
        id=profile_id,
        name_a=payload.name,
        birth_a=encrypt_text(payload.birth),
        birth_hour_a=encrypt_text(payload.birthHour) if payload.birthHour else None,
        name_b=None,
        birth_b=None,
        birth_hour_b=None,
        is_lunar=payload.isLunar,
        combo_data=encrypt_text(json.dumps(factors, ensure_ascii=False)),
        preview_report=json.dumps(preview, ensure_ascii=False),
    )
    db.add(profile)
    db.add(
        Report(
            profile_id=profile_id,
            order_no=None,
            state="locked",
            full_report=json.dumps(report_contract, ensure_ascii=False),
        )
    )
    db.commit()

    data = {"profileId": profile_id, "previewReport": _preview_view(preview)}
    store_idempotent_response(db, idempotency_key, IDEM_SCOPE_PROFILE, data)
    db.commit()
    return ok_response(data)


@router.get("/api/profiles/{profile_id}/preview")
def get_preview(profile_id: str, db: Session = Depends(get_db)) -> dict:
    """重新获取预览报告（脱敏：返回姓名/生辰明文，不返回密文，不含完整内容）。"""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if profile is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")

    preview = json.loads(profile.preview_report) if profile.preview_report else None
    if preview is None:
        preview = {
            "title": "姻缘运势测算预览",
            "locked": True,
            "lockedNote": "完整版需付费解锁",
        }
    return ok_response(
        {
            "profileId": profile.id,
            "name": profile.name_a,
            "birth": decrypt_text(profile.birth_a),
            "previewReport": _preview_view(preview),
        }
    )
