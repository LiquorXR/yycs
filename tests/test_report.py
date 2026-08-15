"""简版合婚报告服务单元测试：评分规则、rank 五档、契约结构、focus_tags。"""

from __future__ import annotations

from app.services.report import generate_report


def _factors(zodiac_a, element_a, hour_a, zodiac_b, element_b, hour_b) -> dict:
    return {
        "nameA": "张三",
        "nameB": "李四",
        "birthA": "1990-01-01",
        "birthB": "1991-01-01",
        "birthHourA": hour_a,
        "birthHourB": hour_b,
        "isLunar": False,
        "zodiacA": zodiac_a,
        "elementA": element_a,
        "zodiacB": zodiac_b,
        "elementB": element_b,
    }


def test_score_element_sheng_ke_boundary():
    # 无特殊生肖（虎/兔）5 分 + 无特殊时辰（丑/寅）6 分作底
    sheng = generate_report(_factors("虎", "木", "丑", "兔", "火", "寅"))
    bihe = generate_report(_factors("虎", "木", "丑", "兔", "木", "寅"))
    ke = generate_report(_factors("虎", "木", "丑", "兔", "土", "寅"))
    assert sheng["score"] == 71  # 相生 60 + 5 + 6
    assert bihe["score"] == 59  # 比和 48 + 5 + 6
    assert ke["score"] == 37  # 相克 26 + 5 + 6


def test_score_element_reversed_direction():
    # 反向生克方向判定一致
    sheng = generate_report(_factors("虎", "火", "丑", "兔", "木", "寅"))  # 木生火（B生A）
    ke = generate_report(_factors("虎", "土", "丑", "兔", "木", "寅"))  # 木克土（B克A）
    assert sheng["score"] == 71
    assert ke["score"] == 37


def test_score_liu_he():
    # 鼠/牛 子丑六合 +20；相克 26 + 六合 20 + 时辰无 6 = 52
    r = generate_report(_factors("鼠", "木", "丑", "牛", "土", "寅"))
    assert r["score"] == 52


def test_score_san_he():
    # 猴/鼠 申子辰三合 +10；26 + 10 + 6 = 42
    r = generate_report(_factors("猴", "木", "丑", "鼠", "土", "寅"))
    assert r["score"] == 42


def test_score_liu_chong():
    # 鼠/马 子午六冲 -15；26 - 15 + 6 = 17
    r = generate_report(_factors("鼠", "木", "丑", "马", "土", "寅"))
    assert r["score"] == 17


def test_score_xing():
    # 鼠/兔 子卯相刑 -10；26 - 10 + 6 = 22
    r = generate_report(_factors("鼠", "木", "丑", "兔", "土", "寅"))
    assert r["score"] == 22


def test_score_hour_missing_takes_mid():
    # 时辰缺失取中值 5：相生 60 + 六合 20 + 5 = 85
    r = generate_report(_factors("鼠", "木", None, "牛", "火", None))
    assert r["score"] == 85


def test_score_clamped_to_range():
    # 极端组合分数仍在 0-100 且为 int
    r = generate_report(_factors("鼠", "木", "丑", "马", "土", "寅"))
    assert isinstance(r["score"], int)
    assert 0 <= r["score"] <= 100


def test_rank_five_bands():
    # 90 → 天作之合（相生 60 + 六合 20 + 时辰六合 10）
    r = generate_report(_factors("鼠", "木", "子", "牛", "火", "丑"))
    assert r["score"] == 90
    assert r["rank"] == "天作之合 · 上等婚配"
    # 80 → 琴瑟和鸣（相生 60 + 三合 10 + 时辰六合 10）
    r = generate_report(_factors("猴", "木", "子", "鼠", "火", "丑"))
    assert r["score"] == 80
    assert r["rank"] == "琴瑟和鸣 · 上吉之配"
    # 71 → 中上之合
    r = generate_report(_factors("虎", "木", "丑", "兔", "火", "寅"))
    assert r["score"] == 71
    assert r["rank"] == "中上之合 · 良缘可成"
    # 64 → 中平之配（比和 48 + 三合 10 + 时辰无 6）
    r = generate_report(_factors("猴", "木", "丑", "鼠", "木", "寅"))
    assert r["score"] == 64
    assert r["rank"] == "中平之配 · 磨合可圆"
    # 55 → 缘浅之合（相生 60 + 六冲 -15 + 时辰六合 10）
    r = generate_report(_factors("鼠", "木", "子", "马", "火", "丑"))
    assert r["score"] == 55
    assert r["rank"] == "缘浅之合 · 宜加经营"


def test_contract_schema_complete():
    factors = _factors("鼠", "木", "子", "牛", "火", "丑")
    r = generate_report(factors)
    for key in ("title", "score", "rank", "scoreNote", "analysis", "karma", "lockedPreview"):
        assert key in r
    assert isinstance(r["score"], int) and 0 <= r["score"] <= 100
    assert r["title"] == "属相鼠配牛·八字合婚详批"
    assert r["rank"]
    assert r["scoreNote"]
    assert r["analysis"]["label"] == "命理总评" and r["analysis"]["text"]
    assert len(r["karma"]) == 2
    assert all(set(k) == {"title", "body"} and k["title"] and k["body"] for k in r["karma"])
    assert len(r["lockedPreview"]) == 2
    assert all(set(k) == {"title", "body"} and k["title"] and k["body"] for k in r["lockedPreview"])


def test_focus_tags_with_and_without():
    factors = _factors("鼠", "木", "子", "牛", "火", "丑")
    base = generate_report(factors)
    # 不传 focus_tags 正常
    assert len(base["karma"]) == 2
    assert len(base["lockedPreview"]) == 2
    # 传入 focus_tags（含未知标签）正常且内容侧重定制
    tagged = generate_report(
        factors,
        focus_tags=["八字五行匹配", "婚后财运旺衰", "未知标签"],
    )
    assert len(tagged["karma"]) == 2
    assert tagged["karma"] != base["karma"]
    assert any("财库" in k["body"] for k in tagged["karma"])
