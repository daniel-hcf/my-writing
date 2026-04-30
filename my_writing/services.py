import json
import logging
import re
import sqlite3
from datetime import datetime

from . import prompts
from .config import DEFAULTS, DIMENSIONS
from .db import connect, get_config, set_config
from .models import FullConfig, ProviderConfig
from .providers import get_image_provider, get_text_provider
from .secret_store import decrypt_secret, encrypt_secret, is_encrypted

log = logging.getLogger(__name__)

MODE_DAILY = "daily"
MODE_IMAGE_PRACTICE = "image_practice"
MODE_JOURNAL = "journal"
PRACTICE_MODES = (MODE_DAILY, MODE_IMAGE_PRACTICE)
ALL_MODES = (*PRACTICE_MODES, MODE_JOURNAL)


def load_full_config() -> FullConfig:
    text_raw = get_config("text") or {}
    image_raw = get_config("image") or {}
    text = {**DEFAULTS["text"], **text_raw}
    image = {**DEFAULTS["image"], **image_raw}
    text["apiKey"] = decrypt_secret(text.get("apiKey", ""))
    image["apiKey"] = decrypt_secret(image.get("apiKey", ""))
    return FullConfig(text=ProviderConfig(**text), image=ProviderConfig(**image))


def migrate_config_secrets() -> None:
    for key in ("text", "image"):
        raw = get_config(key) or {}
        api_key = raw.get("apiKey", "")
        if api_key and not is_encrypted(api_key):
            raw["apiKey"] = encrypt_secret(api_key)
            set_config(key, raw)


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


def parse_json_loose(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("模型未返回 JSON")
    return json.loads(match.group(0))


def latest_weakest_dimension() -> str | None:
    with connect() as conn:
        row = conn.execute(
            """SELECT s.scores FROM submissions s
               JOIN assignments a ON a.id = s.assignment_id
               WHERE a.type IN (?, ?)
               ORDER BY s.id DESC LIMIT 1""",
            PRACTICE_MODES,
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
    candidates.sort(key=lambda item: item[1])
    return candidates[0][0]


def recent_assignment_titles(mode: str | None = None, n: int = 10) -> list[str]:
    today = datetime.now().strftime("%Y-%m-%d")
    filters = ["date = ?"]
    params: list[object] = [today]
    submit_filters: list[str] = []
    submit_params: list[object] = []

    if mode:
        filters.append("type = ?")
        params.append(mode)
        submit_filters.append("a.type = ?")
        submit_params.append(mode)
    else:
        filters.append("type IN (?, ?)")
        params.extend(PRACTICE_MODES)
        submit_filters.append("a.type IN (?, ?)")
        submit_params.extend(PRACTICE_MODES)

    with connect() as conn:
        today_rows = conn.execute(
            f"SELECT title FROM assignments WHERE {' AND '.join(filters)} ORDER BY id DESC",
            tuple(params),
        ).fetchall()
        submitted_rows = conn.execute(
            f"""SELECT a.title FROM assignments a
                INNER JOIN submissions s ON s.assignment_id = a.id
                WHERE {' AND '.join(submit_filters)}
                ORDER BY s.id DESC LIMIT ?""",
            (*submit_params, n),
        ).fetchall()

    seen: set[str] = set()
    titles: list[str] = []
    for row in [*today_rows, *submitted_rows]:
        title = row["title"]
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def cleanup_orphan_assignments(mode: str | None = None) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    filters = ["date < ?", "id NOT IN (SELECT assignment_id FROM submissions)"]
    params: list[object] = [today]
    if mode:
        filters.append("type = ?")
        params.append(mode)
    else:
        filters.append("type IN (?, ?)")
        params.extend(PRACTICE_MODES)
    with connect() as conn:
        conn.execute(f"DELETE FROM assignments WHERE {' AND '.join(filters)}", tuple(params))


async def generate_daily_assignment(
    focus: str | None,
    cfg: FullConfig,
    recent_titles: list[str] | None = None,
) -> dict:
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(
        prompts.daily_assignment_system(),
        prompts.daily_assignment_user(focus, recent_titles),
    )
    data = parse_json_loose(raw)
    title = (data.get("title") or "").strip() or "今日每日一练"
    scenario = (data.get("scenario") or "").strip() or "请围绕题目自由展开。"
    return {
        "type": MODE_DAILY,
        "title": title,
        "scenario": scenario,
        "image_data": None,
        "focus_dimension": focus,
    }


async def generate_image_practice_assignment(
    focus: str | None,
    cfg: FullConfig,
    recent_titles: list[str] | None = None,
) -> dict:
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(
        prompts.image_practice_system(),
        prompts.image_practice_user(focus, recent_titles),
    )
    data = parse_json_loose(raw)
    title = (data.get("title") or "").strip() or "看图写作练习"
    image_prompt = (data.get("imagePrompt") or "").strip()
    if not image_prompt:
        raise ValueError("图片题缺少 imagePrompt")
    image_provider = get_image_provider(cfg.image)
    image_data = await image_provider.generate(image_prompt)
    return {
        "type": MODE_IMAGE_PRACTICE,
        "title": title,
        "scenario": None,
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


def get_assignment_by_date(date: str, mode_filter: str | None = None) -> sqlite3.Row | None:
    with connect() as conn:
        if mode_filter:
            return conn.execute(
                "SELECT * FROM assignments WHERE date = ? AND type = ? ORDER BY id DESC LIMIT 1",
                (date, mode_filter),
            ).fetchone()
        return conn.execute(
            "SELECT * FROM assignments WHERE date = ? AND type IN (?, ?) ORDER BY id DESC LIMIT 1",
            (date, *PRACTICE_MODES),
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


def get_current_unsubmitted_assignment(date: str, mode: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            """SELECT a.* FROM assignments a
               WHERE a.date = ? AND a.type = ?
               AND NOT EXISTS (
                   SELECT 1 FROM submissions s WHERE s.assignment_id = a.id
               )
               ORDER BY a.id DESC LIMIT 1""",
            (date, mode),
        ).fetchone()


def assignment_mode_has_submission(date: str, mode: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            """SELECT 1 FROM assignments a
               JOIN submissions s ON s.assignment_id = a.id
               WHERE a.date = ? AND a.type = ?
               LIMIT 1""",
            (date, mode),
        ).fetchone()
    return row is not None


def delete_unsubmitted_assignments(date: str, mode: str) -> None:
    with connect() as conn:
        conn.execute(
            """DELETE FROM assignments
               WHERE date = ? AND type = ?
               AND id NOT IN (SELECT assignment_id FROM submissions)""",
            (date, mode),
        )


def get_or_create_journal_assignment(date: str) -> dict:
    row = get_assignment_by_date(date, mode_filter=MODE_JOURNAL)
    if not row:
        aid = insert_assignment(
            {
                "type": MODE_JOURNAL,
                "title": "每日随笔",
                "scenario": None,
                "image_data": None,
                "focus_dimension": None,
            },
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
    row = get_assignment_by_date(today, mode_filter=MODE_DAILY)
    if not row:
        focus = latest_weakest_dimension()
        recent = recent_assignment_titles(MODE_DAILY)
        data = await generate_daily_assignment(focus, cfg, recent)
        aid = insert_assignment(data, today)
        row = get_assignment_by_id(aid)
    result = assignment_row_to_dict(row)
    sub = get_submission_by_assignment(row["id"])
    if sub:
        result["submission"] = submission_row_to_dict(sub)
    return result


async def replace_today_daily_assignment(cfg: FullConfig) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    if assignment_mode_has_submission(today, MODE_DAILY):
        raise ValueError("今日每日一练已完成，不能再换题")
    delete_unsubmitted_assignments(today, MODE_DAILY)
    focus = latest_weakest_dimension()
    recent = recent_assignment_titles(MODE_DAILY)
    data = await generate_daily_assignment(focus, cfg, recent)
    aid = insert_assignment(data, today)
    return assignment_row_to_dict(get_assignment_by_id(aid))


async def get_or_create_today_image_practice(cfg: FullConfig) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    row = get_current_unsubmitted_assignment(today, MODE_IMAGE_PRACTICE)
    if not row:
        focus = latest_weakest_dimension()
        recent = recent_assignment_titles(MODE_IMAGE_PRACTICE)
        data = await generate_image_practice_assignment(focus, cfg, recent)
        aid = insert_assignment(data, today)
        row = get_assignment_by_id(aid)
    return assignment_row_to_dict(row)


async def replace_today_image_practice(cfg: FullConfig) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    delete_unsubmitted_assignments(today, MODE_IMAGE_PRACTICE)
    focus = latest_weakest_dimension()
    recent = recent_assignment_titles(MODE_IMAGE_PRACTICE)
    data = await generate_image_practice_assignment(focus, cfg, recent)
    aid = insert_assignment(data, today)
    return assignment_row_to_dict(get_assignment_by_id(aid))


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


async def score_submission(assignment_id: int, content: str, cfg: FullConfig) -> dict:
    row = get_assignment_by_id(assignment_id)
    if row is None:
        raise ValueError("作业不存在")
    assignment = {
        "type": row["type"],
        "title": row["title"],
        "scenario": row["scenario"],
        "focus_dimension": row["focus_dimension"],
    }
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(prompts.scoring_system(), prompts.scoring_user(assignment, content))
    try:
        data = parse_json_loose(raw)
    except (ValueError, json.JSONDecodeError):
        retry = await text_provider.chat(
            prompts.scoring_system(),
            prompts.scoring_user(assignment, content) + "\n\n请只输出 JSON 对象，不要任何其他文字。",
        )
        data = parse_json_loose(retry)

    scores_raw = data.get("scores") or {}
    feedback_raw = data.get("feedback") or {}
    overall = (data.get("overall") or "").strip()

    scores: dict[str, int] = {}
    feedback: dict[str, dict] = {}
    for dim in DIMENSIONS:
        score = scores_raw.get(dim, 5)
        try:
            score_int = int(round(float(score)))
        except (TypeError, ValueError):
            score_int = 5
        scores[dim] = max(1, min(10, score_int))
        dim_feedback = feedback_raw.get(dim) or {}
        feedback[dim] = {
            "优点": (dim_feedback.get("优点") or "").strip(),
            "不足": (dim_feedback.get("不足") or "").strip(),
            "建议": (dim_feedback.get("建议") or "").strip(),
        }

    today = datetime.now().strftime("%Y-%m-%d")
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


async def pre_generate_tomorrow(cfg: FullConfig) -> None:
    from datetime import timedelta

    target = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if get_assignment_by_date(target, mode_filter=MODE_DAILY):
        return
    try:
        focus = latest_weakest_dimension()
        recent = recent_assignment_titles(MODE_DAILY)
        data = await generate_daily_assignment(focus, cfg, recent)
        insert_assignment(data, target)
    except Exception as exc:
        log.warning("预生成明日作业失败：%s", exc)


def collect_stats(mode: str = "all") -> dict:
    where_sql = "a.type IN (?, ?)"
    params: tuple[object, ...] = PRACTICE_MODES
    if mode in PRACTICE_MODES:
        where_sql = "a.type = ?"
        params = (mode,)
    elif mode != "all":
        raise ValueError(f"unknown mode: {mode}")

    with connect() as conn:
        rows = conn.execute(
            f"""SELECT s.date, s.scores FROM submissions s
                JOIN assignments a ON a.id = s.assignment_id
                WHERE {where_sql}
                ORDER BY s.id ASC""",
            params,
        ).fetchall()

    if not rows:
        return {"latest": None, "average": None, "series": []}

    series = []
    for row in rows:
        try:
            scores = json.loads(row["scores"])
        except json.JSONDecodeError:
            continue
        series.append({"date": row["date"], "scores": scores})

    latest = series[-1]["scores"] if series else None
    average = {}
    for dim in DIMENSIONS:
        values = [item["scores"].get(dim) for item in series if dim in item["scores"]]
        if values:
            average[dim] = round(sum(values) / len(values), 2)

    return {"latest": latest, "average": average, "series": series}
