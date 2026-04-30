from .config import DIMENSIONS

DIMENSION_LIST = "、".join(DIMENSIONS)


def daily_assignment_system() -> str:
    return (
        "你是一位资深写作教练，擅长为学员设计每日写作训练题目。"
        "你需要基于学员当前的薄弱维度设计一题场景写作题，让学员有针对性地练习。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def daily_assignment_user(focus: str | None, recent_titles: list[str] | None = None) -> str:
    focus_line = (
        f"本次重点训练维度：{focus}。请构造一个能凸显该维度训练价值的题材，并把训练点写进 title。"
        if focus
        else "这是学员的首次练习，请综合考察各维度。"
    )
    recent_block = ""
    if recent_titles:
        items = "\n".join(f"  - {t}" for t in recent_titles)
        recent_block = f"\n\n近期已出过的题目（请避免重复类似题材和场景）：\n{items}\n"
    return f"""
请设计一道中文创意写作题，目标字数 500 字以上。
{focus_line}{recent_block}

可选维度共 7 个：{DIMENSION_LIST}。
请输出严格的 JSON，结构如下（不要 Markdown 代码块）：{{
  "title": "题目标题，简短一句话",
  "scenario": "100~200 字的中文场景设定与梗概"
}}

约束：
- scenario 用中文，留有想象空间，不要替学员把故事写完。
- 标题要尽量具体，让学员一眼知道练什么。
""".strip()


def image_practice_system() -> str:
    return (
        "你是一位资深写作教练，擅长设计看图写作练习。"
        "你需要基于学员当前的薄弱维度，生成一题适合看图写作的标题和英文图片描述。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def image_practice_user(focus: str | None, recent_titles: list[str] | None = None) -> str:
    focus_line = (
        f"本次重点训练维度：{focus}。请构造一个能凸显该维度训练价值的画面，并把训练点写进 title。"
        if focus
        else "这是学员的看图写作练习，请综合考察各维度。"
    )
    recent_block = ""
    if recent_titles:
        items = "\n".join(f"  - {t}" for t in recent_titles)
        recent_block = f"\n\n近期已出过的题目（请避免重复类似题材和画面）：\n{items}\n"
    return f"""
请设计一道看图写作题，目标字数 500 字以上。
{focus_line}{recent_block}

可选维度共 7 个：{DIMENSION_LIST}。
请输出严格的 JSON，结构如下（不要 Markdown 代码块）：{{
  "title": "题目标题，简短一句话",
  "imagePrompt": "用于图片生成的英文描述，要具体、有画面感、镜头感"
}}

约束：
- imagePrompt 用英文，描述具体场景、人物、氛围、镜头感。
- 标题用中文，提示写作方向，但不要把故事写完。
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
        "你是一位资深中文写作老师，需要根据 7 个维度对学员的作品进行 1~10 分整数评分，"
        "并给出每个维度的优点、不足、建议。要求评分客观、点评具体，避免空话套话。"
        "你必须严格只输出一个合法 JSON 对象。"
    )


def scoring_user(assignment: dict, content: str) -> str:
    a_type = assignment.get("type")
    a_title = assignment.get("title") or ""
    a_scenario = assignment.get("scenario") or ""
    focus = assignment.get("focus_dimension") or assignment.get("focusDimension") or ""

    title_block = f"题目标题：{a_title}"
    if a_type == "daily" and a_scenario:
        prompt_block = f"场景设定：{a_scenario}"
    elif a_type == "image_practice":
        prompt_block = "题目类型：看图写作"
    else:
        prompt_block = "题目类型：自由写作"
    focus_block = f"本次重点训练维度：{focus}" if focus else "本次为综合训练"

    dim_schema = ",\n    ".join([f'"{d}": 8' for d in DIMENSIONS])
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
- feedback 每个维度都要有具体优点、不足、可操作的建议；
- overall 不超过 200 字。
""".strip()
