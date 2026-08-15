"""简版单人运势报告服务单元测试：评分规则、rank 五档、契约结构、focus_tags。"""

from __future__ import annotations

from app.services.report import generate_single_report


def _factors(name="张三", zodiac="虎", element="木", hour="午") -> dict:
    return {
        "name": name,
        "birth": "1995-06-15",
        "birthHour": hour,
        "isLunar": False,
        "zodiac": zodiac,
        "element": element,
    }


def test_score_element_sheng_ke_boundary():
    # 日主五行能量：相生 60 / 比和 48 / 相克 36（基准 30 + 生克加减）
    sheng = generate_single_report(_factors(zodiac="虎", element="木", hour="午"))  # 木生火 +30
    bihe = generate_single_report(_factors(zodiac="虎", element="木", hour="卯"))  # 木比和 +18
    ke = generate_single_report(_factors(zodiac="虎", element="木", hour="申"))  # 金克木 +6
    assert sheng["score"] == 96  # 60 + 三合 26 + 10
    assert bihe["score"] == 80  # 48 + 无 22 + 10
    assert ke["score"] == 60  # 36 + 六冲 14 + 10


def test_score_element_reversed_direction():
    # 反向生克方向判定一致（时辰生日主同样按相生计）：木生火（时辰生日主）
    sheng = generate_single_report(_factors(zodiac="狗", element="火", hour="寅"))  # 戌寅午三合 +26
    assert sheng["score"] == 96  # 60 + 26 + 10


def test_score_liu_he():
    # 鼠/丑时 子丑六合 +30；相克 36 + 六合 30 + 10 = 76
    r = generate_single_report(_factors(zodiac="鼠", element="木", hour="丑"))
    assert r["score"] == 76


def test_score_san_he():
    # 虎/午时 寅午戌三合 +26；60 + 26 + 10 = 96
    r = generate_single_report(_factors(zodiac="虎", element="木", hour="午"))
    assert r["score"] == 96


def test_score_liu_chong():
    # 鼠/午时 子午六冲 +14；相生 60 + 六冲 14 + 10 = 84
    r = generate_single_report(_factors(zodiac="鼠", element="木", hour="午"))
    assert r["score"] == 84


def test_score_xing():
    # 兔/子时 卯子相刑 +18；相克 36 + 相刑 18 + 10 = 64
    r = generate_single_report(_factors(zodiac="兔", element="火", hour="子"))
    assert r["score"] == 64


def test_score_hour_missing_takes_mid():
    # 时辰缺失：五行取基准 30 + 姻缘取中值 20 + 时辰信息中值 5 = 55
    r = generate_single_report(_factors(hour=None))
    assert r["score"] == 55


def test_score_clamped_to_range():
    r = generate_single_report(_factors(zodiac="鼠", element="木", hour="午"))
    assert isinstance(r["score"], int)
    assert 0 <= r["score"] <= 100


def test_rank_five_bands():
    # 96 → 上等运势（相生 60 + 三合 26 + 时辰 10）
    r = generate_single_report(_factors(zodiac="虎", element="木", hour="午"))
    assert r["score"] == 96
    assert r["rank"] == "上等运势 · 正缘可期"
    # 84 → 中上运势（相生 60 + 六冲 14 + 时辰 10）
    r = generate_single_report(_factors(zodiac="鼠", element="木", hour="午"))
    assert r["score"] == 84
    assert r["rank"] == "中上运势 · 良缘可成"
    # 76 → 中平运势（相克 36 + 六合 30 + 时辰 10）
    r = generate_single_report(_factors(zodiac="鼠", element="木", hour="丑"))
    assert r["score"] == 76
    assert r["rank"] == "中平运势 · 磨合可圆"
    # 60 → 平稳运势（相克 36 + 六冲 14 + 时辰 10）
    r = generate_single_report(_factors(zodiac="虎", element="木", hour="申"))
    assert r["score"] == 60
    assert r["rank"] == "平稳运势 · 厚积薄发"
    # 55 → 缘浅之合（时辰缺失）
    r = generate_single_report(_factors(hour=None))
    assert r["score"] == 55
    assert r["rank"] == "缘浅之合 · 宜加经营"


def test_contract_schema_complete():
    r = generate_single_report(_factors())
    for key in ("title", "score", "rank", "scoreNote", "analysis", "karma", "lockedPreview"):
        assert key in r
    assert isinstance(r["score"], int) and 0 <= r["score"] <= 100
    assert r["title"] == "张三 · 八字命盘详批（姻缘预览）"
    assert r["rank"]
    assert r["scoreNote"]
    assert r["analysis"]["label"] == "命理总评" and r["analysis"]["text"]
    assert len(r["karma"]) == 3
    assert all(set(k) == {"title", "body"} and k["title"] and k["body"] for k in r["karma"])
    assert len(r["lockedPreview"]) == 2
    assert all(set(k) == {"title", "body"} and k["title"] and k["body"] for k in r["lockedPreview"])


def test_focus_tags_with_and_without():
    base = generate_single_report(_factors())
    # 不传 focus_tags 正常
    assert len(base["karma"]) == 3
    assert len(base["lockedPreview"]) == 2
    # 传入 focus_tags（含未知标签）正常且内容侧重定制
    tagged = generate_single_report(
        _factors(),
        focus_tags=["正缘桃花期", "婚后财运旺衰", "未知标签"],
    )
    assert len(tagged["karma"]) == 3
    assert tagged["karma"] != base["karma"]
    assert "桃花期已至" in tagged["karma"][0]["body"]
    assert "财库" in tagged["karma"][2]["body"]
    assert base["karma"][0] != tagged["karma"][0]
    assert base["karma"][2] != tagged["karma"][2]
