"""简版合婚报告服务：基于测算因子生成完整报告契约 JSON。

评分维度：
- 五行互补（满分 60）：年干五行生克，相生加分、相克减分、比和居中。
- 生肖合婚（满分 30）：地支六合/三合/六冲/相刑/无特殊。
- 日干时辰（满分 10）：双方出生时辰地支关系；时辰缺失取中值。

对外输出完整报告契约（title/score/rank/scoreNote/analysis/karma/lockedPreview），
供订单报告接口在解锁前后使用。算法函数化、可替换，后续可接入真实测算引擎。
"""

from __future__ import annotations

from app.services.divination import HOURS, ZODIAC

# 生肖 → 地支
ZODIAC_BRANCH = dict(zip(ZODIAC, HOURS))

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

# 生肖（地支）评分：满分 30
_ZODIAC_SCORE = {"六合": 20, "三合": 10, "无": 5, "相刑": -10, "六冲": -15}
# 时辰评分：满分 10（缺失取中值 5）
_HOUR_SCORE = {"六合": 10, "三合": 8, "无": 6, "相刑": 4, "六冲": 3}
# 五行评分：满分 60
_ELEMENT_SCORE = {"相生": 60, "比和": 48, "相克": 26}

# rank 五档（threshold 递减）
_RANK_BANDS = [
    (90, "天作之合 · 上等婚配"),
    (80, "琴瑟和鸣 · 上吉之配"),
    (70, "中上之合 · 良缘可成"),
    (60, "中平之配 · 磨合可圆"),
    (0, "缘浅之合 · 宜加经营"),
]

# 五行生克评语（按男女方向，男=nameA，女=nameB）
_ELEMENT_NOTE = {
    "A生B": "男{ea}生女{eb},{eb}得{ea}之生助,男以情滋养女方,两情相悦,互有补益。",
    "B生A": "女{eb}生男{ea},{ea}得女之生助,女以柔滋养男方,家宅和顺,情深意笃。",
    "比和": "男{ea}与女{eb}同气相求,性情投契,同声相应,相处融洽,少生龃龉。",
    "A克B": "男{ea}克女{eb},男主刚而女主柔,需女方以柔化解,男方多些体恤,方保长久。",
    "B克A": "女{eb}克男{ea},女中刚强,男需包容退让,以静制动,方可化解相克之势。",
}

# 分数段收尾评语
_BAND_NOTE = {
    90: "天作之合,百年好合,珠联璧合,实属上等良配。",
    80: "琴瑟和鸣,婚配顺遂,相辅相成,可期白首。",
    70: "良缘可成,虽有磨合,悉心经营,亦得圆满。",
    60: "中平之配,多需沟通,同甘共苦,亦可白头。",
    0: "缘浅之合,尤需经营,以心换心,方得长久。",
}

# 命理总评章节描述
_ZODIAC_DESC = {
    "六合": "生肖六合,天缘契合",
    "三合": "生肖三合,气类相投",
    "六冲": "生肖六冲,性情相激",
    "相刑": "生肖相刑,时有抵牾",
    "无": "生肖平和,缘分中正",
}
_ELEMENT_DESC = {"相生": "五行相生,互有补益", "比和": "五行比和,同气相应", "相克": "五行相克,宜柔克刚"}
_HOUR_DESC = {
    "六合": "双方时辰六合,锦上添花",
    "三合": "双方时辰相合,助力姻缘",
    "六冲": "双方时辰相冲,尚需调和",
    "相刑": "双方时辰相刑,宜多体谅",
    "缺": "时辰信息暂缺,仅供参考",
}

# focus_tags 定制内容：(karma 章节下标, 追加句)
_FOCUS_BODY = {
    "八字五行匹配": (0, "命盘五行生克有致,互补之势明显,若作八字详批,契合度可再上层楼。"),
    "正缘结婚年限": (1, "正缘气数渐旺,婚恋窗口期宜把握,红鸾星动之年缔结良缘,可化解流年波折。"),
    "婚后财运旺衰": (1, "婚后财库看旺衰:凡五行相生者,财源顺遂,居家理财两相宜,逐年趋旺。"),
    "性格相克化解": (1, "性格相克处,以柔济刚、以静制动,多一分包容少一分计较,自可化干戈为玉帛。"),
    "子女缘分推演": (0, "子女宫气数中平偏旺,晚得贵子,血脉相承,家宅和乐可期。"),
}

DEFAULT_LOCKED_PREVIEW = [
    {
        "title": "未来3年情感磨合与化解危机节点",
        "body": "完整版将逐年推演未来三年情感走势,标注磨合期与危机节点,并给出化解之法。付费解锁后即可查看。",
    },
    {
        "title": "婚后家庭财库与旺夫/旺妻指数预测",
        "body": "完整版将测算婚后家庭财库旺衰与旺夫/旺妻指数,助力家宅兴旺。付费解锁后即可查看。",
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


def _score_note(ea: str, eb: str, element_rel: str, score: int) -> str:
    """按五行生克方向与分数段生成评语。"""
    if element_rel == "相生":
        phrase = _ELEMENT_NOTE["A生B" if _GENERATES[ea] == eb else "B生A"]
    elif element_rel == "相克":
        phrase = _ELEMENT_NOTE["A克B" if _OVERCOMES[ea] == eb else "B克A"]
    else:
        phrase = _ELEMENT_NOTE["比和"]
    note = phrase.format(ea=ea, eb=eb)
    band = 0
    for threshold, _ in _RANK_BANDS:
        if score >= threshold:
            band = threshold
            break
    return note + _BAND_NOTE[band]


def _analysis_text(factors: dict, za: str, zb: str, ea: str, eb: str, zodiac_rel: str, element_rel: str, hour_rel: str) -> str:
    """命理总评章节：生肖 + 五行 + 时辰综合描述。"""
    return (
        f"{factors['nameA']}属{za}、五行属{ea},{factors['nameB']}属{zb}、五行属{eb}。"
        f"{_ZODIAC_DESC[zodiac_rel]},{_ELEMENT_DESC[element_rel]},"
        f"{_HOUR_DESC.get(hour_rel, '双方时辰平和,中正无碍')}。"
        "综合命理参详,此配对整体可期,宜惜缘相守,共赴白首。"
    )


def _karma_chapters(factors: dict, focus_tags: list[str] | None) -> list[dict]:
    """前世缘分与相处之道两章节；focus_tags 定制内容侧重。"""
    za, zb = factors["zodiacA"], factors["zodiacB"]
    bodies = [
        (
            f"前世轮回中,属{za}与属{zb}曾有宿世之约,今世再续前缘。"
            "五百年回眸换今生擦肩,此等姻缘非偶然,乃因果牵引。"
            "缘起则聚,缘尽则散,今世既已相逢,当惜眼前人,共修来世福。"
        ),
        (
            f"属{za}与属{zb}一刚一柔,性格各有长短。相处贵在求同存异:"
            "善用对方长处,包容彼此短处,小事不争,大事共商,"
            "方能使互补之利大于相克之弊,白首同心。"
        ),
    ]
    for tag in (focus_tags or []):
        entry = _FOCUS_BODY.get(tag)
        if entry is None:
            continue
        idx, sentence = entry
        bodies[idx] += sentence
    return [
        {"title": "前世缘分 · 宿世因果", "body": bodies[0]},
        {"title": "相处之道 · 性格互补", "body": bodies[1]},
    ]


def generate_report(factors: dict, focus_tags: list[str] | None = None) -> dict:
    """生成简版合婚报告契约 JSON。

    输入 divination.generate_factors 的 factors dict 与可选 focus_tags，
    输出契约：title/score/rank/scoreNote/analysis/karma/lockedPreview。
    """
    za, zb = factors["zodiacA"], factors["zodiacB"]
    ea, eb = factors["elementA"], factors["elementB"]
    ha, hb = factors["birthHourA"], factors["birthHourB"]

    zodiac_rel = _branch_relation(ZODIAC_BRANCH[za], ZODIAC_BRANCH[zb])
    element_rel = _element_relation(ea, eb)

    if ha and hb:
        hour_rel = _branch_relation(ha, hb)
        hour_score = _HOUR_SCORE.get(hour_rel, 6)
    else:
        hour_rel = "缺"
        hour_score = 5

    score = _ELEMENT_SCORE[element_rel] + _ZODIAC_SCORE[zodiac_rel] + hour_score
    score = max(0, min(100, score))
    rank = _rank_of(score)
    score_note = _score_note(ea, eb, element_rel, score)
    analysis = _analysis_text(factors, za, zb, ea, eb, zodiac_rel, element_rel, hour_rel)

    return {
        "title": f"属相{za}配{zb}·八字合婚详批",
        "score": score,
        "rank": rank,
        "scoreNote": score_note,
        "analysis": {"label": "命理总评", "text": analysis},
        "karma": _karma_chapters(factors, focus_tags),
        "lockedPreview": [dict(item) for item in DEFAULT_LOCKED_PREVIEW],
    }
