"""测算模块：信息校验、测算因子提取、预览报告算法骨架。

姻缘测算（正缘画像 + 桃花期预览）：仅需单人姓名/生辰/时辰，以姻缘为主线。
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
    name: str,
    birth: str,
    birth_hour: str | None = None,
    is_lunar: bool | None = None,
) -> None:
    """校验测算信息；不合法抛 BizError(14001, HTTP 422)。"""
    if not NAME_RE.match((name or "").strip()):
        raise BizError(ErrorCode.DIVINATION_INFO_INVALID, "测算信息无效：name 需为 2~20 位中文/英文/间隔号")

    d = _parse_date(birth)
    if d < DATE_MIN or d > date.today():
        raise BizError(ErrorCode.DIVINATION_INFO_INVALID, "测算信息无效：birth 需在 1900-01-01 至今天之间")

    if birth_hour not in (None, "") and birth_hour not in HOURS:
        raise BizError(ErrorCode.DIVINATION_INFO_INVALID, "测算信息无效：birthHour 需为十二时辰（子~亥）之一或空")


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
    name: str,
    birth: str,
    birth_hour: str | None = None,
    is_lunar: bool = False,
) -> dict:
    """提取测算因子（生辰/时辰/生肖/五行），供预览报告与后续完整测算复用。"""
    d = _parse_date(birth)
    return {
        "name": name,
        "birth": birth,
        "birthHour": birth_hour,
        "isLunar": bool(is_lunar),
        "zodiac": year_zodiac(d.year),
        "element": year_element(d.year),
    }


def generate_preview_report(factors: dict) -> dict:
    """生成预览报告（掩码，不涉及真实测算内容）。

    返回 dict 含 title/locked/lockedNote/summary；对外响应仅取前三项，
    summary 仅为展示型摘要（生肖/五行标签），完整测算 B 阶段实现。
    """
    title = f"{factors['name']} · 姻缘正缘测算预览"
    summary = (
        f"{factors['name']}（属{factors['zodiac']}·{factors['element']}）"
        "的正缘画像与桃花时机速览。"
        "以上为免费预览，完整姻缘天书需付费解锁。"
    )
    return {
        "title": title,
        "locked": True,
        "lockedNote": "完整版需付费解锁",
        "summary": summary,
    }
