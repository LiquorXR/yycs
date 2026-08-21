"""测算模块路由：提交测算信息、重新获取预览报告、隐私版本、客服删除。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.errors import BizError, ErrorCode
from app.core.response import ok_response
from app.core.timeutil import utcnow
from app.db.session import get_db
from app.models.profile import Profile
from app.models.report import Report
from app.services.divination import generate_factors, generate_preview_report, validate_profile_input
from app.services.idempotency import IDEM_SCOPE_PROFILE, get_idempotent_response, store_idempotent_response
from app.services.report import generate_single_report
from app.services.seq import next_profile_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["profiles"])

_PREVIEW_FIELDS = ("title", "locked", "lockedNote")


class ProfileCreateRequest(BaseModel):
    name: str
    birth: str
    birthHour: str | None = None
    isLunar: bool = False
    focusTags: list[str] | None = Field(default=None, description="正缘桃花期/婚后财运旺衰/性格解析/事业运势/避坑锦囊")
    agreedPrivacyVersion: str | None = Field(default=None, description="已同意的隐私政策版本，需等于当前版本")


def _preview_view(preview: dict) -> dict:
    """对外预览视图：仅暴露 title/locked/lockedNote（不含 summary）。"""
    return {k: preview.get(k) for k in _PREVIEW_FIELDS}


@router.get("/api/privacy/version")
def get_privacy_version() -> dict:
    """隐私政策当前版本（公开，供前端比对与展示）。"""
    return ok_response(
        {
            "version": settings.PRIVACY_VERSION,
            "effectiveDate": settings.PRIVACY_EFFECTIVE_DATE,
            "companyName": settings.COMPANY_NAME,
            "icpNo": settings.ICP_NO,
            "contactEmail": settings.CONTACT_EMAIL,
            "contactAddress": settings.CONTACT_ADDRESS,
            "retentionDaysUnpaid": settings.DATA_RETENTION_DAYS_UNPAID,
            "retentionDaysPaid": settings.DATA_RETENTION_DAYS_PAID,
        }
    )


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

    # 隐私政策同意校验：必须携带当前版本
    if not payload.agreedPrivacyVersion or payload.agreedPrivacyVersion != settings.PRIVACY_VERSION:
        raise BizError(ErrorCode.PARAM_VALIDATION, "请先阅读并同意隐私政策")

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
        agreed_privacy_version=payload.agreedPrivacyVersion,
        consented_at=utcnow(),
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


@router.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str, db: Session = Depends(get_db)) -> dict:
    """客服删除/匿名化测算档案（PIPL 删除权，行使后无法恢复）。

    仅供客服后台调用，不在 H5 前端暴露；操作将匿名化姓名与生辰密文并清空因子。
    """
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if profile is None:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")

    # 匿名化：姓名掩码，生辰重置为不可逆占位，清空敏感因子
    profile.name_a = "已删除"
    profile.birth_a = encrypt_text("1900-01-01")
    profile.birth_hour_a = None
    profile.combo_data = None
    profile.preview_report = None
    profile.agreed_privacy_version = None
    profile.consented_at = None
    db.commit()
    logger.info("客服删除测算档案：profile_id=%s", profile_id)
    return ok_response({"profileId": profile_id, "deleted": True})
