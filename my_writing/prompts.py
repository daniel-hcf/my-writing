from .config import DIMENSIONS

DIMENSION_LIST = "、".join(DIMENSIONS)


def daily_assignment_system() -> str:
    return (
        "你是一位资深男频爽文写作教练，擅长为学员设计每日故事种子扩写训练。"
        "你需要基于学员当前的薄弱维度设计一个适合扩写成 300~800 字连载章节片段的故事种子，"
        "并让学员重点练习环境、动作、心理如何服务压迫、反击、爽点和追读。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def daily_assignment_user(focus: str | None, recent_titles: list[str] | None = None) -> str:
    focus_line = (
        f"本次额外关注维度：{focus}。请让故事种子自然带出该维度的男频爽文练习空间，并把训练点写进 title。"
        if focus
        else "这是学员的首次男频爽文故事种子扩写练习，请综合考察各维度。"
    )
    recent_block = ""
    if recent_titles:
        items = "\n".join(f"  - {t}" for t in recent_titles)
        recent_block = f"\n\n近期已出过的题目（请避免重复类似题材和场景）：\n{items}\n"
    return f"""
请设计一道男频爽文故事种子扩写题，学员目标扩写 300~800 字。
{focus_line}{recent_block}

可选维度共 7 个：{DIMENSION_LIST}。
请输出严格的 JSON，结构如下（不要 Markdown 代码块）：{{
  "title": "题目标题，简短一句话",
  "scenario": "20~60 字的一句话中文故事种子"
}}

约束：
- scenario 必须是一句可扩写的核心情境，包含主角处境、欲望、压迫/羞辱/危机、可反击空间、转折或悬念中的至少三项。
- 要优先设计适合连载章节的强情节题，能制造开篇钩子、反击期待、爽点预期和追读欲。
- 题材可在都市、玄幻、修仙、末世、异能、学院、宗门等男频爽文场景中变化，但不要写成纯文艺氛围题。
- 不要写完整梗概，不要写结局，不要替学员把故事讲完。
- 故事种子要适合练环境、动作、心理，让学员能扩写成一场有压迫、选择、反击或尾钩的完整小说片段。
- 标题要尽量具体，让学员一眼知道今天练什么。
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

可选维度共 7 个：{DIMENSION_LIST}。
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

可选维度共 7 个：{DIMENSION_LIST}。
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
        "你是一位偏严格的男频爽文训练编辑兼责编，需要根据 7 个维度对学员的作品进行 1~10 分整数评分，"
        "并给出每个维度的优点、不足、建议。评分重点是开篇钩子、主角目标、压迫感、反击爽点、升级感、"
        "信息释放、节奏密度、尾钩和追读欲。要求评分客观、点评具体，避免空话套话。"
        "不默认高分，不硬夸，不为了鼓励而回避问题；普通完成不应轻易给 8 分以上，"
        "明显影响追读的问题必须明确扣分到 6 分或以下。"
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
            "题目类型：男频爽文故事种子扩写（目标 300~800 字，重点看环境、动作、心理是否支撑压迫、反击、爽点和尾钩）\n"
            f"故事种子：{a_scenario}"
        )
    elif a_type == "outline_practice" and a_scenario:
        prompt_block = (
            "题目类型：男频爽文章节小纲练习（学员根据标题和冲突引子写 100~200 字故事小纲，重点看目标、阻碍、反击、爽点、升级和尾钩）\n"
            f"冲突引子：{a_scenario}"
        )
    elif a_type == "image_practice":
        prompt_block = "题目类型：男频爽文看图写作"
    else:
        prompt_block = "题目类型：自由写作"
    focus_block = f"本次重点训练维度：{focus}" if focus else "本次为综合训练"

    example_scores = [6, 5, 5, 6, 5, 5, 5]
    dim_schema = ",\n    ".join([f'"{d}": {example_scores[i]}' for i, d in enumerate(DIMENSIONS)])
    feedback_schema = ",\n    ".join(
        [f'"{d}": {{"优点": "...", "不足": "...", "建议": "..."}}' for d in DIMENSIONS]
    )

    return f"""
{title_block}
{prompt_block}
{focus_block}

学员作品（共 {len(content)} 字）：
<<<
{content}
>>>

请对作品打分并给出点评。严格输出 JSON：{{
  "scores": {{
    {dim_schema}
  }},
  "feedback": {{
    {feedback_schema}
  }},
  "overall": "整体一段话点评"
}}

要求：
- scores 中每个值必须是 1~10 的整数；
- feedback 每个维度都要有具体优点、不足、可操作的建议；“优点”必须基于文本证据，没有明显亮点时可以写“基本完成但亮点不足”；
- “不足”必须指出会让男频爽文读者流失、跳读或不追更的具体原因，“建议”必须是下一稿能直接执行的改法；
- 人物塑造看主角欲望、压迫处境、行动力和辨识度；对话描写看冲突、试探、压迫、反击，而不是闲聊；
- 场景描写看是否服务危机、奇观、资源和爽点；叙事结构看章节推进、反转、爽点兑现和尾钩；
- 情感表达看羞辱、愤怒、不甘、热血、复仇期待是否有效；语言文采看清晰、利落、节奏快，不追求散文腔；
- 细节描写看道具、身份、规则、战力/资源信息是否能制造期待；
- 如果是故事种子扩写，请特别评价环境、动作、心理是否把种子扩成了有效男频爽文场景；
- 如果是故事小纲练习，请特别评价叙事结构、冲突强度、反击爽点、升级空间和可扩写性；
- 不默认高分，不硬夸，普通完成不应轻易给 8 分以上；明显削弱追读欲的问题必须明确扣分；
- overall 不超过 200 字，要总结最影响追读的一两个问题，并给出下一稿优先修改方向。
""".strip()
