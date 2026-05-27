from .config import DIMENSIONS

DIMENSION_LIST = "、".join(DIMENSIONS)


def daily_assignment_system() -> str:
    return (
        "你是一位资深男频爽文节奏教练，擅长把题材/场景改造成每日故事种子扩写训练。"
        "训练目标固定为网文节奏：钩子立住、压迫推进、反击期待形成、爽点兑现、结尾留下追读。"
        "你需要生成一个适合扩写成 300~800 字连载章节片段的故事种子。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def daily_assignment_user(
    focus: str | None,
    recent_titles: list[str] | None = None,
    intent: str | None = None,
) -> str:
    intent = (intent or "").strip()
    intent_line = (
        f"用户今天想用这个题材/场景练节奏：{intent}。请优先围绕它设计题面，但要改造成有网文节奏链的训练题。"
        if intent
        else "用户今天没有指定题材/场景，请你自动选择一个适合男频爽文节奏训练的题材。"
    )
    recent_block = ""
    if recent_titles:
        items = "\n".join(f"  - {t}" for t in recent_titles)
        recent_block = f"\n\n近期已出过的题目（请避免重复类似题材和场景）：\n{items}\n"
    focus_line = f"系统建议训练核心：{focus or '节奏'}。"
    return f"""
请设计一道男频爽文故事种子扩写题，学员目标扩写 300~800 字。
{intent_line}
{focus_line}{recent_block}

训练目标只有一个：节奏。节奏链包括：钩子 → 压迫推进 → 反击期待 → 爽点兑现 → 追读。
请输出严格的 JSON，结构如下（不要 Markdown 代码块）：{{
  "title": "题目标题，简短一句话",
  "scenario": "20~60 字的一句话中文故事种子"
}}

约束：
- scenario 必须是一句可扩写的核心情境，包含主角处境、欲望、压迫/羞辱/危机、可反击空间、转折或悬念中的至少三项。
- 题面必须天然适合练节奏：开头有钩子，中段有压迫，主角有反击期待，结尾能导向爽点或追读。
- 题材可在都市、玄幻、修仙、末世、异能、学院、宗门等男频爽文场景中变化，但不要写成纯文艺氛围题。
- 不要写完整梗概，不要写结局，不要替学员把故事讲完。
- 文笔、人物、场景、细节都只作为服务节奏的手段，不要把题面设计成传统作文题。
- 标题要尽量具体，让学员一眼知道今天用什么题材/场景练节奏。
""".strip()


def outline_practice_system() -> str:
    return (
        "你是一位资深男频爽文写作教练，擅长设计章节结构与冲突训练。"
        "你需要基于学员当前的薄弱维度设计一题爽文章节小纲练习，只给标题和简短冲突引子，"
        "让学员自己写 100~200 字故事小纲，练习目标、阻碍、反击、爽点、升级和尾钩。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def outline_practice_user(focus: str | None, recent_titles: list[str] | None = None) -> str:
    focus_line = (
        f"本次额外关注维度：{focus}。请在不削弱男频爽文章节结构和冲突训练的前提下，让故事小纲也能训练该维度。"
        if focus
        else "这是一次男频爽文章节小纲练习，请综合考察故事结构、冲突设计、爽点兑现和追读。"
    )
    recent_block = ""
    if recent_titles:
        items = "\n".join(f"  - {t}" for t in recent_titles)
        recent_block = f"\n\n近期已出过的故事小纲题目（请避免重复类似题材和冲突）：\n{items}\n"
    return f"""
请设计一道男频爽文章节小纲练习，题面只包含标题和简短冲突引子，训练目标是故事结构、冲突设计、反击爽点和尾钩。
{focus_line}{recent_block}

可选维度：{DIMENSION_LIST}。
请输出严格的 JSON，结构如下（不要 Markdown 代码块）：{{
  "title": "题目标题，简短一句话",
  "scenario": "20~80 字的中文冲突引子或故事设定"
}}

约束：
- scenario 只能提供起点和矛盾，不要写成完整故事小纲。
- 不要替学员设计冲突升级、转折、反击爽点和结尾；这些是学员要练的内容。
- 冲突引子要具体，包含主角目标、强阻碍或利益压迫，有可写成 100~200 字故事小纲的扩展空间。
- 题面要能引导学员练“目标-阻碍-反击-爽点-尾钩”的章节结构，但不要直接给出完整解法。
- 避免文艺散文化、纯氛围题或低冲突日常题，优先生成适合男频连载的强情节题。
- 标题要提示故事核心矛盾，但不要直接泄露结局。
""".strip()


def image_practice_system() -> str:
    return (
        "你是一位资深男频爽文写作教练，擅长设计看图写作练习。"
        "你需要基于学员当前的薄弱维度，生成一题适合男频爽文训练的标题和英文图片描述。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def image_practice_user(focus: str | None, recent_titles: list[str] | None = None) -> str:
    focus_line = (
        f"本次重点训练维度：{focus}。请构造一个能凸显该维度男频爽文训练价值的画面，并把训练点写进 title。"
        if focus
        else "这是学员的男频爽文看图写作练习，请综合考察各维度。"
    )
    recent_block = ""
    if recent_titles:
        items = "\n".join(f"  - {t}" for t in recent_titles)
        recent_block = f"\n\n近期已出过的题目（请避免重复类似题材和画面）：\n{items}\n"
    return f"""
请设计一道男频爽文看图写作题，目标字数 500 字以上。
{focus_line}{recent_block}

可选维度：{DIMENSION_LIST}。
请输出严格的 JSON，结构如下（不要 Markdown 代码块）：{{
  "title": "题目标题，简短一句话",
  "imagePrompt": "用于图片生成的英文描述，要具体、有画面感、镜头感"
}}

约束：
- imagePrompt 用英文，描述具体场景、人物、氛围、镜头感，并突出压迫、身份落差、资源争夺、强敌逼迫或危机爆发。
- 画面要适合都市、玄幻、修仙、末世、异能、秘境、宗门等男频爽文题材，能引出反击爽点、升级期待和追读欲。
- 标题用中文，提示写作方向，但不要把故事写完，也不要直接泄露反转结局。
""".strip()


def scenario_fallback_system() -> str:
    return "你是一位写作教练，请把已生成的图片描述改写成中文场景写作题。严格只输出一个合法 JSON 对象。"


def scenario_fallback_user(title: str, image_prompt: str) -> str:
    return f"""
之前为学员生成的题目标题是：{title}
原本的图片描述（英文）是：{image_prompt}

由于图片生成失败，请把它改写成一道场景写作题，保留训练目的。请输出严格 JSON：{{
  "title": "题目标题",
  "scenario": "100~200 字的中文场景设定与梗概"
}}
""".strip()


def scoring_system() -> str:
    return (
        "你是一位偏严格的男频爽文节奏教练兼责编，只围绕一个核心给分：网文节奏。"
        "节奏指读者是否被钩子抓住、被压迫推着往前读、等待主角反击、吃到爽点，并在结尾想继续看。"
        "文笔、人物、场景、细节都不是独立评分项，只评价它们是否服务节奏。"
        "不默认高分，不硬夸，不为了鼓励而回避问题；普通完成不应轻易给 8 分以上，"
        "钩子弱、压迫断、反击期待不足、爽点没兑现或结尾没有追读时，必须明确扣分。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def scoring_user(assignment: dict, content: str) -> str:
    a_type = assignment.get("type")
    a_title = assignment.get("title") or ""
    a_scenario = assignment.get("scenario") or ""
    focus = assignment.get("focus_dimension") or assignment.get("focusDimension") or ""

    title_block = f"题目标题：{a_title}"
    if a_type == "daily" and a_scenario:
        prompt_block = (
            "题目类型：男频爽文节奏训练（目标 300~800 字，重点看钩子、压迫推进、反击期待、爽点兑现和追读）\n"
            f"故事种子：{a_scenario}"
        )
    elif a_type == "outline_practice" and a_scenario:
        prompt_block = (
            "题目类型：男频爽文章节小纲练习（学员根据标题和冲突引子写 100~200 字故事小纲，"
            "重点看目标、阻碍、反击、爽点、升级和尾钩）\n"
            f"冲突引子：{a_scenario}"
        )
    elif a_type == "image_practice":
        prompt_block = "题目类型：男频爽文看图写作"
    else:
        prompt_block = "题目类型：自由写作"
    focus_block = f"本次训练核心：{focus}" if focus else "本次训练核心：节奏"

    return f"""
{title_block}
{prompt_block}
{focus_block}

学员作品（共 {len(content)} 字）：
<<<
{content}
>>>

请只围绕网文节奏评分并给出诊断。严格输出 JSON：{{
  "rhythm_score": 1,
  "market_score": 1,
  "training_score": 1,
  "fatal_problem": "本篇最影响节奏/追读/爽感的一个问题",
  "best_part": "本篇最值得保留或扩写的一处",
  "rewrite_task": {{
    "target": "重写哪一段",
    "requirement": "下一稿必须加入、延后、删去或强化什么",
    "word_limit": "300字以内"
  }},
  "rhythm_checks": {{
    "hook": {{"status": "成立/偏弱/缺失", "reason": "钩子是否立住的原因"}},
    "pressure": {{"status": "成立/偏弱/缺失", "reason": "压迫是否推进的原因"}},
    "counter_expectation": {{"status": "成立/偏弱/缺失", "reason": "反击期待是否形成的原因"}},
    "payoff": {{"status": "成立/偏弱/缺失", "reason": "爽点是否兑现的原因"}},
    "follow_through": {{"status": "成立/偏弱/缺失", "reason": "结尾是否留下追读的原因"}}
  }},
  "overall": "整体一段话点评"
}}

要求：
- rhythm_score 是唯一主分，1~10 整数；不要再输出人物、对话、场景、文采等独立维度分。
- rhythm_score 重点看“钩子 → 压迫推进 → 反击期待 → 爽点兑现 → 追读”是否连成一条阅读链。
- market_score 按男频连载读者是否想继续看打分；training_score 按新手是否完成本次节奏训练打分。
- rhythm_checks 的 status 只能是“成立”“偏弱”“缺失”之一，每个 reason 必须具体指出文本证据或缺口。
- 文笔、人物、场景、细节只作为节奏是否成立的原因来点评，不作为独立评分项。
- fatal_problem 只指出一个最影响节奏的问题；rewrite_task 必须可执行。
- 普通完成不应轻易给 8 分以上；钩子弱、压迫断、反击期待不足、爽点没兑现或结尾无追读时必须扣分。
- overall 不超过 200 字，说明下一稿最优先怎么修节奏。
""".strip()
