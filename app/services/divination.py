"""测算模块：信息校验、测算因子提取、预览报告算法骨架。

预览报告仅做简单规则（生肖/五行）生成 title 与摘要，摘要不涉及真实测算内容，
预览即掩码。算法函数化、可替换，后续可改为配置化/接入真实测算引擎。
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app.core.errors import BizError, ErrorCode

# 十二生肖（按年份取模）
ZODIAC = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

# 十天干与五行映射（简化规则：按天干取五行）
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
STEM_ELEMENT = {"甲乙": "木", "丙丁": "火", "戊己": "土", "庚辛": "金", "壬癸": "水"}

# 十二时辰
HOURS = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 姓名：2~20 字符，中文 / 英文 / 间隔号（·）/ 连字符
NAME_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z·-]{2,20}$")

DATE_MIN = date(1900, 1, 1)


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise BizError(ErrorCode.DIVINATION_INFO_INVALID, "测算信息无效：出生日期需为合法日期 YYYY-MM-DD")


def validate_profile_input(
    name_a: str,
    name_b: str,
    birth_a: str,
    birth_b: str,
    birth_hour_a: str | None = None,
    birth_hour_b: str | None = None,
    is_lunar: bool | None = None,
) -> None:
    """校验测算信息；不合法抛 BizError(14001, HTTP 422)。"""
    for label, name in (("nameA", name_a), ("nameB", name_b)):
        if not NAME_RE.match((name or "").strip()):
            raise BizError(ErrorCode.DIVINATION_INFO_INVALID, f"测算信息无效：{label} 需为 2~20 位中文/英文/间隔号")

    d_a = _parse_date(birth_a)
    d_b = _parse_date(birth_b)
    for label, d in (("birthA", d_a), ("birthB", d_b)):
        if d < DATE_MIN or d > date.today():
            raise BizError(ErrorCode.DIVINATION_INFO_INVALID, f"测算信息无效：{label} 需在 1900-01-01 至今天之间")

    for label, hour in (("birthHourA", birth_hour_a), ("birthHourB", birth_hour_b)):
        if hour in (None, ""):
            continue
        if hour not in HOURS:
            raise BizError(ErrorCode.DIVINATION_INFO_INVALID, f"测算信息无效：{label} 需为十二时辰（子~亥）之一或空")


def year_zodiac(year: int) -> str:
    """按年份取生肖（简化规则）。"""
    return ZODIAC[(year - 4) % 12]


def year_element(year: int) -> str:
    """按年份天干取五行（简化规则）。"""
    stem = HEAVENLY_STEMS[(year - 4) % 10]
    for keys, element in STEM_ELEMENT.items():
        if stem in keys:
            return element
    return "土"


def generate_factors(
    name_a: str,
    birth_a: str,
    birth_hour_a: str | None,
    name_b: str,
    birth_b: str,
    birth_hour_b: str | None,
    is_lunar: bool = False,
) -> dict:
    """提取测算因子（生辰/时辰/生肖/五行），供预览报告与后续完整测算复用。"""
    d_a = _parse_date(birth_a)
    d_b = _parse_date(birth_b)
    return {
        "nameA": name_a,
        "nameB": name_b,
        "birthA": birth_a,
        "birthB": birth_b,
        "birthHourA": birth_hour_a,
        "birthHourB": birth_hour_b,
        "isLunar": bool(is_lunar),
        "zodiacA": year_zodiac(d_a.year),
        "elementA": year_element(d_a.year),
        "zodiacB": year_zodiac(d_b.year),
        "elementB": year_element(d_b.year),
    }


def generate_preview_report(profile_id: str, factors: dict) -> dict:
    """生成预览报告（掩码，不涉及真实测算内容）。

    返回 dict 含 title/contentUrl/locked/lockedNote/summary；对外响应仅取前四项，
    summary 仅为展示型摘要（生肖/五行标签），完整测算 B 阶段实现。
    """
    title = f"属相{factors['zodiacA']}配{factors['zodiacB']}·姻缘测算预览"
    summary = (
        f"{factors['nameA']}（属{factors['zodiacA']}·{factors['elementA']}）"
        f"与 {factors['nameB']}（属{factors['zodiacB']}·{factors['elementB']}）的缘分速览。"
        "以上为免费预览，完整配对报告需付费解锁。"
    )
    return {
        "title": title,
        "contentUrl": f"/static/reports/{profile_id}_preview.html",
        "locked": True,
        "lockedNote": "完整版需付费解锁",
        "summary": summary,
    }
