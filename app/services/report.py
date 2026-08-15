"""简版单人运势报告服务：基于测算因子生成完整报告契约 JSON。

评分维度：
- 日主五行能量（满分 60）：按出生年份天干五行定日主，时辰五行生克加减；时辰缺失取基准分。
- 正缘姻缘指数（满分 30）：生肖支与时辰支六合/三合/无/刑/冲简化规则；时辰缺失取中值。
- 时辰信息（满分 10）：时辰缺失取中值 5。

对外输出完整报告契约（title/score/rank/scoreNote/analysis/karma/lockedPreview），
供订单报告接口在解锁前后使用。算法函数化、可替换，后续可接入真实测算引擎。
"""

from __future__ import annotations

from app.services.divination import HOURS, ZODIAC

# 生肖 → 地支
ZODIAC_BRANCH = dict(zip(ZODIAC, HOURS))

# 地支五行（时辰五行映射）
BRANCH_ELEMENT = {
    "子": "水",
    "亥": "水",
    "寅": "木",
    "卯": "木",
    "巳": "火",
    "午": "火",
    "申": "金",
    "酉": "金",
    "丑": "土",
    "辰": "土",
    "未": "土",
    "戌": "土",
}

# 地支六合
_LIU_HE = {("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"), ("巳", "申"), ("午", "未")}
# 地支三合局
_SAN_HE_GROUPS = [("申", "子", "辰"), ("寅", "午", "戌"), ("巳", "酉", "丑"), ("亥", "卯", "未")]
# 地支六冲
_LIU_CHONG = {("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥")}
# 地支相刑（含辰午酉亥自刑）
_XING = {
    ("子", "卯"),
    ("卯", "子"),
    ("寅", "巳"),
    ("巳", "申"),
    ("申", "寅"),
    ("丑", "戌"),
    ("戌", "未"),
    ("未", "丑"),
    ("辰", "辰"),
    ("午", "午"),
    ("酉", "酉"),
    ("亥", "亥"),
}

# 五行相生 / 相克
_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_OVERCOMES = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 日主五行能量（满分 60）：年干五行定基准分，时辰五行生克加减；缺失取基准分
_ELEMENT_BASE = 30
_ELEMENT_HOUR_BONUS = {"相生": 30, "比和": 18, "相克": 6}
# 正缘姻缘指数（满分 30）：生肖支与时辰支关系；时辰缺失取中值
_LOVE_SCORE = {"六合": 30, "三合": 26, "无": 22, "相刑": 18, "六冲": 14}
_LOVE_MID = 20
# 时辰信息（满分 10）：缺失取中值 5
_HOUR_INFO = {"缺": 5, "有": 10}

# rank 五档（threshold 递减）
_RANK_BANDS = [
    (90, "上等运势 · 正缘可期"),
    (80, "中上运势 · 良缘可成"),
    (70, "中平运势 · 磨合可圆"),
    (60, "平稳运势 · 厚积薄发"),
    (0, "缘浅之合 · 宜加经营"),
]

# 日主强弱评语（时辰生克方向）
_ELEMENT_NOTE = {
    "相生": "日主得时辰生助，气机充盈",
    "比和": "日主与时辰同气，根基稳固",
    "相克": "日主与时辰生克交错，气机稍欠",
}

# 分数段收尾评语
_BAND_NOTE = {
    90: "上等运势，正缘可期，姻缘宫得时得地，宜主动把握，顺遂可期。",
    80: "中上运势，良缘可成，多一份用心经营，姻缘自会水到渠成。",
    70: "中平运势，磨合可圆，感情之事贵在坚持，悉心经营亦有圆满。",
    60: "平稳运势，厚积薄发，先修自身，缘分自来，宜稳中求进。",
    0: "缘浅之合，宜加经营，桃花虽淡，用心灌溉亦可绽放。",
}

# focus_tags 定制内容：(karma 章节下标, 追加句)
_FOCUS_BODY = {
    "正缘桃花期": (0, "正缘桃花期已至，近年红鸾星动之机，宜多社交、善把握，良缘自现。"),
    "婚后财运旺衰": (2, "婚后财库看旺衰：财星得地者家财渐丰，宜开源节流、稳健理财，财运逐年趋旺。"),
    "性格解析": (1, "性格解析贵在知命：明自身长短，扬长避短，与人相处多几分通透，少几分执拗。"),
    "事业运势": (2, "事业运势看官星：流年逢生扶则步步高升，宜专注深耕、待时而动，自有伯乐相携。"),
    "避坑锦囊": (1, "避坑锦囊：口舌之争最易招损，情绪上头时宜三思后行，远离小人是非，方得安然。"),
}

DEFAULT_LOCKED_PREVIEW = [
    {
        "title": "正缘画像与桃花旺衰节点",
        "body": "完整版将生成你的专属正缘画像，推演未来数年桃花旺衰与脱单关键节点，并给出应期把握之法。付费解锁后即可查看。",
    },
    {
        "title": "婚后财运走势与家庭财富规划",
        "body": "完整版将测算婚后财运旺衰与家庭财富走势，助力家宅兴旺、财库充盈。付费解锁后即可查看。",
    },
]


def _branch_relation(a: str, b: str) -> str:
    """地支关系：六合 > 三合 > 六冲 > 相刑 > 无；同支看自刑。"""
    if a == b:
        return "相刑" if a in ("辰", "午", "酉", "亥") else "无"
    if (a, b) in _LIU_HE or (b, a) in _LIU_HE:
        return "六合"
    for group in _SAN_HE_GROUPS:
        if a in group and b in group:
            return "三合"
    if (a, b) in _LIU_CHONG or (b, a) in _LIU_CHONG:
        return "六冲"
    if (a, b) in _XING or (b, a) in _XING:
        return "相刑"
    return "无"


def _element_relation(ea: str, eb: str) -> str:
    """五行关系：相生 > 相克 > 比和。"""
    if _GENERATES[ea] == eb or _GENERATES[eb] == ea:
        return "相生"
    if _OVERCOMES[ea] == eb or _OVERCOMES[eb] == ea:
        return "相克"
    return "比和"


def _rank_of(score: int) -> str:
    """分数映射五档 rank。"""
    for threshold, rank in _RANK_BANDS:
        if score >= threshold:
            return rank
    return _RANK_BANDS[-1][1]


def _element_score(day_element: str, hour: str | None) -> int:
    """日主五行能量（满分 60）：年干五行定基准，时辰五行生克加减；缺失取基准分。"""
    if hour is None:
        return _ELEMENT_BASE
    return _ELEMENT_BASE + _ELEMENT_HOUR_BONUS[_element_relation(day_element, BRANCH_ELEMENT[hour])]


def _love_score(zodiac_branch: str, hour: str | None) -> int:
    """正缘姻缘指数（满分 30）：生肖支与时辰支六合/三合/无/刑/冲；时辰缺失取中值。"""
    if hour is None:
        return _LOVE_MID
    return _LOVE_SCORE[_branch_relation(zodiac_branch, hour)]


def _hour_info_score(hour: str | None) -> int:
    """时辰信息（满分 10）：缺失取中值 5。"""
    return _HOUR_INFO["有"] if hour else _HOUR_INFO["缺"]


def _score_note(name: str, element_rel: str, love_rel: str, score: int) -> str:
    """按日主强弱、姻缘地支关系与分数段生成评语。"""
    note = f"{name}日主{_ELEMENT_NOTE[element_rel]}，姻缘宫地支{love_rel}，气数中正。"
    band = 0
    for threshold, _ in _RANK_BANDS:
        if score >= threshold:
            band = threshold
            break
    return note + _BAND_NOTE[band]


def _analysis_text(
    factors: dict,
    day_element: str,
    element_rel: str,
    zodiac_branch: str,
    hour: str | None,
    love_rel: str,
) -> str:
    """命理总评章节：日主强弱 + 五行喜用 + 性格。"""
    name = factors["name"]
    zodiac = factors["zodiac"]
    text = f"{name}属{zodiac}、五行属{day_element}。{_ELEMENT_NOTE[element_rel]}。"
    if hour:
        text += f"命主生于{hour}时，命宫{zodiac}与时辰地支{love_rel}，正缘桃花气数有依。"
    else:
        text += "时辰信息暂缺，命局推断以年柱为准，略有出入，仅供参考。"
    text += (
        f"五行喜用宜取生扶{day_element}之神，性格外柔内刚、重情重诺，"
        "宜扬长避短、宽以待人，运势自可渐入佳境。"
    )
    return text


def _karma_chapters(factors: dict, focus_tags: list[str] | None) -> list[dict]:
    """正缘画像/性格解析/事业财运三章节；focus_tags 定制内容侧重。"""
    name = factors["name"]
    zodiac = factors["zodiac"]
    element = factors["element"]
    bodies = [
        (
            f"{name}属{zodiac}，正缘画像以五行属{element}者为佳，气质沉稳、心思细腻之人更易结缘。"
            "桃花期多现于五行生扶之年，红鸾星动之际，宜主动走出舒适圈，良缘自现。"
        ),
        (
            f"{name}性格以{element}性为底色，外柔内刚，重情重诺。"
            "相处之道贵在求同存异：善用对方长处，包容彼此短处，小事不争，大事共商，白首同心。"
        ),
        (
            f"{name}事业财运走势与五行{element}气数相呼应，中年渐入佳境。"
            "财运旺衰看流年财星：得地之年财源顺遂，宜开源节流、稳中求进，家业渐丰。"
        ),
    ]
    for tag in (focus_tags or []):
        entry = _FOCUS_BODY.get(tag)
        if entry is None:
            continue
        idx, sentence = entry
        bodies[idx] += sentence
    return [
        {"title": "正缘画像 · 桃花期预测", "body": bodies[0]},
        {"title": "性格解析 · 相处之道", "body": bodies[1]},
        {"title": "事业财运 · 旺衰走势", "body": bodies[2]},
    ]


def generate_single_report(factors: dict, focus_tags: list[str] | None = None) -> dict:
    """生成简版单人运势报告契约 JSON。

    输入 divination.generate_factors 的 factors dict 与可选 focus_tags，
    输出契约：title/score/rank/scoreNote/analysis/karma/lockedPreview。
    """
    name = factors["name"]
    zodiac = factors["zodiac"]
    element = factors["element"]
    hour = factors["birthHour"]

    zodiac_branch = ZODIAC_BRANCH[zodiac]
    element_rel = _element_relation(element, BRANCH_ELEMENT[hour]) if hour else "比和"
    love_rel = _branch_relation(zodiac_branch, hour) if hour else "缺"

    element_score = _element_score(element, hour)
    love_score = _love_score(zodiac_branch, hour)
    hour_score = _hour_info_score(hour)
    score = max(0, min(100, element_score + love_score + hour_score))
    rank = _rank_of(score)
    score_note = _score_note(name, element_rel, love_rel, score)
    analysis = _analysis_text(factors, element, element_rel, zodiac_branch, hour, love_rel)

    return {
        "title": f"{name} · 八字命盘详批（姻缘预览）",
        "score": score,
        "rank": rank,
        "scoreNote": score_note,
        "analysis": {"label": "命理总评", "text": analysis},
        "karma": _karma_chapters(factors, focus_tags),
        "lockedPreview": [dict(item) for item in DEFAULT_LOCKED_PREVIEW],
    }
