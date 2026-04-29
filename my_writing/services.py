import json
import logging
import re
import sqlite3
from datetime import datetime

from . import prompts
from .config import DEFAULTS, DIMENSIONS
from .db import connect, get_config
from .models import FullConfig, ProviderConfig
from .providers import get_image_provider, get_text_provider

log = logging.getLogger(__name__)


# ---- 配置 ----------------------------------------------------------------

def load_full_config() -> FullConfig:
    text_raw = get_config("text") or {}
    image_raw = get_config("image") or {}
    text = {**DEFAULTS["text"], **text_raw}
    image = {**DEFAULTS["image"], **image_raw}
    return FullConfig(text=ProviderConfig(**text), image=ProviderConfig(**image))


def is_text_configured(cfg: FullConfig) -> bool:
    t = cfg.text
    if not t.provider or not t.model:
        return False
    if t.provider.lower() != "ollama" and not t.apiKey:
        return False
    return True


def is_image_configured(cfg: FullConfig) -> bool:
    i = cfg.image
    return bool(i.provider and i.model and i.apiKey)


# ---- JSON 容错 -----------------------------------------------------------

def parse_json_loose(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("模型未返回 JSON")
    return json.loads(m.group(0))


# ---- 弱项识别 ------------------------------------------------------------

def latest_weakest_dimension() -> str | None:
    with connect() as conn:
        row = conn.execute(
            """SELECT s.scores FROM submissions s
               JOIN assignments a ON a.id = s.assignment_id
               WHERE a.type != 'journal'
               ORDER BY s.id DESC LIMIT 1"""
        ).fetchone()
    if not row:
        return None
    try:
        scores = json.loads(row["scores"])
    except json.JSONDecodeError:
        return None
    candidates = [(d, scores.get(d, 10)) for d in DIMENSIONS if d in scores]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


# ---- 作业生成 ------------------------------------------------------------

def recent_assignment_titles(n: int = 10) -> list[str]:
    """
    返回去重后的题目标题列表，供 AI 避免重复：
    - 今天出过的所有题（不管有没有提交），防止当天反复换题时重出
    - 加上最近 n 条提交过的题，做长期去重
    """
    today = datetime.now().strftime("%Y-%m-%d")
    with connect() as conn:
        today_rows = conn.execute(
            "SELECT title FROM assignments WHERE type != 'journal' AND date = ? ORDER BY id DESC",
            (today,),
        ).fetchall()
        submitted_rows = conn.execute(
            """SELECT a.title FROM assignments a
               INNER JOIN submissions s ON s.assignment_id = a.id
               WHERE a.type != 'journal'
               ORDER BY s.id DESC LIMIT ?""",
            (n,),
        ).fetchall()
    seen: set[str] = set()
    result: list[str] = []
    for r in [*today_rows, *submitted_rows]:
        t = r["title"]
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def cleanup_orphan_assignments() -> None:
    """删除历史上从未提交的非随笔作业（今天的保留，以防用户还在写）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    with connect() as conn:
        conn.execute(
            """DELETE FROM assignments
               WHERE type != 'journal'
               AND date < ?
               AND id NOT IN (SELECT assignment_id FROM submissions)""",
            (today,),
        )


async def generate_assignment(
    focus: str | None,
    cfg: FullConfig,
    recent_titles: list[str] | None = None,
) -> dict:
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(
        prompts.assignment_system(),
        prompts.assignment_user(focus, recent_titles),
    )
    data = parse_json_loose(raw)

    a_type = data.get("type")
    if a_type not in ("image", "scenario"):
        a_type = "scenario"
    title = (data.get("title") or "").strip()
    scenario = (data.get("scenario") or "").strip() or None
    image_prompt = (data.get("imagePrompt") or "").strip() or None
    image_data: str | None = None

    if a_type == "image":
        if not image_prompt:
            a_type = "scenario"
        else:
            try:
                image_provider = get_image_provider(cfg.image)
                image_data = await image_provider.generate(image_prompt)
            except Exception as e:  # 图片失败 → 回退场景
                log.warning("图片生成失败，回退为场景写作：%s", e)
                a_type = "scenario"
                fallback_raw = await text_provider.chat(
                    prompts.scenario_fallback_system(),
                    prompts.scenario_fallback_user(title, image_prompt),
                )
                fb = parse_json_loose(fallback_raw)
                title = (fb.get("title") or title).strip()
                scenario = (fb.get("scenario") or "").strip() or scenario or "请围绕题目自由展开。"

    if a_type == "scenario" and not scenario:
        scenario = "请围绕题目自由展开。"

    return {
        "type": a_type,
        "title": title or "今日写作练习",
        "scenario": scenario,
        "image_data": image_data,
        "focus_dimension": focus,
    }


def insert_assignment(data: dict, date: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO assignments
              (date, type, title, scenario, image_data, focus_dimension, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                data["type"],
                data["title"],
                data.get("scenario"),
                data.get("image_data"),
                data.get("focus_dimension"),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def get_assignment_by_date(date: str, type_filter: str | None = None) -> sqlite3.Row | None:
    with connect() as conn:
        if type_filter:
            return conn.execute(
                "SELECT * FROM assignments WHERE date = ? AND type = ? ORDER BY id DESC LIMIT 1",
                (date, type_filter),
            ).fetchone()
        return conn.execute(
            "SELECT * FROM assignments WHERE date = ? AND type != 'journal' ORDER BY id DESC LIMIT 1",
            (date,),
        ).fetchone()


def get_assignment_by_id(aid: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM assignments WHERE id = ?", (aid,)).fetchone()


def get_submission_by_assignment(assignment_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM submissions WHERE assignment_id = ? ORDER BY id DESC LIMIT 1",
            (assignment_id,),
        ).fetchone()


def get_or_create_journal_assignment(date: str) -> dict:
    row = get_assignment_by_date(date, type_filter="journal")
    if not row:
        aid = insert_assignment(
            {"type": "journal", "title": "每日随笔", "scenario": None, "image_data": None, "focus_dimension": None},
            date,
        )
        row = get_assignment_by_id(aid)
    result = assignment_row_to_dict(row)
    sub = get_submission_by_assignment(row["id"])
    if sub:
        result["submission"] = submission_row_to_dict(sub)
    return result


async def get_or_create_today_assignment(cfg: FullConfig) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    row = get_assignment_by_date(today)
    if not row:
        focus = latest_weakest_dimension()
        recent = recent_assignment_titles()
        data = await generate_assignment(focus, cfg, recent)
        aid = insert_assignment(data, today)
        row = get_assignment_by_id(aid)

    result = assignment_row_to_dict(row)
    sub = get_submission_by_assignment(row["id"])
    if sub:
        result["submission"] = submission_row_to_dict(sub)
    return result


def assignment_row_to_dict(row: sqlite3.Row | None) -> dict:
    if row is None:
        return {}
    return {
        "id": row["id"],
        "date": row["date"],
        "type": row["type"],
        "title": row["title"],
        "scenario": row["scenario"],
        "imageData": row["image_data"],
        "focusDimension": row["focus_dimension"],
        "createdAt": row["created_at"],
    }


# ---- 评分 ----------------------------------------------------------------

async def score_submission(assignment_id: int, content: str, cfg: FullConfig) -> dict:
    row = get_assignment_by_id(assignment_id)
    if row is None:
        raise ValueError("作业不存在")
    a = {
        "type": row["type"],
        "title": row["title"],
        "scenario": row["scenario"],
        "focus_dimension": row["focus_dimension"],
    }
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(prompts.scoring_system(), prompts.scoring_user(a, content))
    try:
        data = parse_json_loose(raw)
    except (ValueError, json.JSONDecodeError):
        # 重试一次，强调只输出 JSON
        retry = await text_provider.chat(
            prompts.scoring_system(),
            prompts.scoring_user(a, content) + "\n\n请只输出 JSON 对象，不要任何其他文字。",
        )
        data = parse_json_loose(retry)

    scores_raw = data.get("scores") or {}
    feedback_raw = data.get("feedback") or {}
    overall = (data.get("overall") or "").strip()

    scores: dict[str, int] = {}
    feedback: dict[str, dict] = {}
    for d in DIMENSIONS:
        s = scores_raw.get(d, 5)
        try:
            s_int = int(round(float(s)))
        except (TypeError, ValueError):
            s_int = 5
        scores[d] = max(1, min(10, s_int))
        fb = feedback_raw.get(d) or {}
        feedback[d] = {
            "优点": (fb.get("优点") or "").strip(),
            "不足": (fb.get("不足") or "").strip(),
            "建议": (fb.get("建议") or "").strip(),
        }

    today = datetime.now().strftime("%Y-%m-%d")
    payload = {
        "scores": scores,
        "feedback": feedback,
        "overall": overall,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO submissions
              (assignment_id, date, content, char_count, scores, feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assignment_id,
                today,
                content,
                len(content),
                json.dumps(scores, ensure_ascii=False),
                json.dumps({"dims": feedback, "overall": overall}, ensure_ascii=False),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        sid = cur.lastrowid

    return {
        "id": sid,
        "assignmentId": assignment_id,
        "date": today,
        "scores": scores,
        "feedback": feedback,
        "overall": overall,
    }


def submission_row_to_dict(row: sqlite3.Row) -> dict:
    feedback_raw = json.loads(row["feedback"])
    if isinstance(feedback_raw, dict) and "dims" in feedback_raw:
        feedback = feedback_raw["dims"]
        overall = feedback_raw.get("overall", "")
    else:
        feedback = feedback_raw
        overall = ""
    return {
        "id": row["id"],
        "assignmentId": row["assignment_id"],
        "date": row["date"],
        "content": row["content"],
        "charCount": row["char_count"],
        "scores": json.loads(row["scores"]),
        "feedback": feedback,
        "overall": overall,
        "createdAt": row["created_at"],
    }


# ---- 后台预生成明日作业 --------------------------------------------------

async def pre_generate_tomorrow(cfg: FullConfig) -> None:
    """在评分完成后，提前为下一天生成作业。已存在则跳过。"""
    from datetime import timedelta

    target = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if get_assignment_by_date(target):
        return
    try:
        focus = latest_weakest_dimension()
        recent = recent_assignment_titles()
        data = await generate_assignment(focus, cfg, recent)
        insert_assignment(data, target)
    except Exception as e:
        log.warning("预生成明日作业失败：%s", e)


# ---- 统计 ----------------------------------------------------------------

def collect_stats() -> dict:
    with connect() as conn:
        rows = conn.execute(
            """SELECT s.date, s.scores FROM submissions s
               JOIN assignments a ON a.id = s.assignment_id
               WHERE a.type != 'journal'
               ORDER BY s.id ASC"""
        ).fetchall()

    if not rows:
        return {"latest": None, "average": None, "series": []}

    series = []
    for r in rows:
        try:
            s = json.loads(r["scores"])
        except json.JSONDecodeError:
            continue
        series.append({"date": r["date"], "scores": s})  # noqa: using r["scores"] already parsed

    latest = series[-1]["scores"] if series else None
    avg = {}
    for d in DIMENSIONS:
        vals = [s["scores"].get(d) for s in series if d in s["scores"]]
        if vals:
            avg[d] = round(sum(vals) / len(vals), 2)

    return {"latest": latest, "average": avg, "series": series}
