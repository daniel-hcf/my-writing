import json
import sqlite3
from datetime import datetime

from .db import connect
from .models import FullConfig
from .providers import get_text_provider
from .services import parse_json_loose

CHAPTER_COUNT = 10

PROJECT_FIELDS = {
    "title": "title",
    "genre": "genre",
    "premise": "premise",
    "mainGoal": "main_goal",
    "corePayoff": "core_payoff",
    "currentStep": "current_step",
}

CHARACTER_FIELDS = {
    "protagonistIdentity": "protagonist_identity",
    "protagonistGoal": "protagonist_goal",
    "protagonistWeakness": "protagonist_weakness",
    "protagonistGrowth": "protagonist_growth",
    "antagonistIdentity": "antagonist_identity",
    "antagonistReason": "antagonist_reason",
    "antagonistPressure": "antagonist_pressure",
}

VOLUME_FIELDS = {
    "title": "title",
    "goal": "goal",
    "pressure": "pressure",
    "payoff": "payoff",
    "endingHook": "ending_hook",
    "openingHook": "opening_hook",
    "midpointEscalation": "midpoint_escalation",
    "finalExplosion": "final_explosion",
}

CHAPTER_FIELDS = {
    "title": "title",
    "summary": "summary",
    "payoff": "payoff",
    "hook": "hook",
    "draft": "draft",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _project_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "genre": row["genre"],
        "premise": row["premise"],
        "mainGoal": row["main_goal"],
        "corePayoff": row["core_payoff"],
        "currentStep": row["current_step"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _characters_row_to_dict(row: sqlite3.Row | None) -> dict:
    return {
        key: row[column] if row else ""
        for key, column in CHARACTER_FIELDS.items()
    }


def _volume_row_to_dict(row: sqlite3.Row | None) -> dict:
    return {
        key: row[column] if row else ""
        for key, column in VOLUME_FIELDS.items()
    }


def _chapter_row_to_dict(row: sqlite3.Row | None, chapter_no: int) -> dict:
    data = {
        key: row[column] if row else ""
        for key, column in CHAPTER_FIELDS.items()
    }
    data["chapterNo"] = chapter_no
    data["updatedAt"] = row["updated_at"] if row else None
    return data


def _review_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "projectId": row["project_id"],
        "chapterNo": row["chapter_no"],
        "scope": row["scope"],
        "issues": json.loads(row["issues"]),
        "questions": json.loads(row["questions"]),
        "suggestions": json.loads(row["suggestions"]),
        "raw": row["raw"],
        "createdAt": row["created_at"],
    }


def _ensure_project_exists(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM outline_projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ValueError("project_not_found")
    return row


def _touch_project(conn: sqlite3.Connection, project_id: int, current_step: str | None = None) -> None:
    if current_step:
        conn.execute(
            "UPDATE outline_projects SET updated_at = ?, current_step = ? WHERE id = ?",
            (_now(), current_step, project_id),
        )
    else:
        conn.execute("UPDATE outline_projects SET updated_at = ? WHERE id = ?", (_now(), project_id))


def _ensure_outline_scaffold(conn: sqlite3.Connection, project_id: int) -> None:
    updated_at = _now()
    conn.execute(
        "INSERT OR IGNORE INTO outline_characters (project_id, updated_at) VALUES (?, ?)",
        (project_id, updated_at),
    )
    conn.execute(
        "INSERT OR IGNORE INTO outline_volumes (project_id, updated_at) VALUES (?, ?)",
        (project_id, updated_at),
    )
    for chapter_no in range(1, CHAPTER_COUNT + 1):
        conn.execute(
            "INSERT OR IGNORE INTO outline_chapters (project_id, chapter_no, updated_at) VALUES (?, ?, ?)",
            (project_id, chapter_no, updated_at),
        )


def _project_progress(project: dict) -> dict:
    fields = [
        project.get("premise"),
        project.get("mainGoal"),
        project.get("corePayoff"),
        project["characters"].get("protagonistGoal"),
        project["characters"].get("antagonistPressure"),
        project["volume"].get("goal"),
        project["volume"].get("endingHook"),
    ]
    completed_chapters = sum(
        1
        for chapter in project["chapters"]
        if chapter.get("title") and chapter.get("summary") and chapter.get("hook")
    )
    base_done = sum(1 for value in fields if (value or "").strip())
    return {
        "coreFieldsDone": base_done,
        "coreFieldsTotal": len(fields),
        "completedChapters": completed_chapters,
        "totalChapters": CHAPTER_COUNT,
        "percent": round(((base_done / len(fields)) * 0.55 + (completed_chapters / CHAPTER_COUNT) * 0.45) * 100),
    }


def create_project(payload: dict) -> dict:
    now = _now()
    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("title_required")
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO outline_projects
              (title, genre, premise, main_goal, core_payoff, current_step, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                (payload.get("genre") or "").strip(),
                (payload.get("premise") or "").strip(),
                (payload.get("mainGoal") or "").strip(),
                (payload.get("corePayoff") or "").strip(),
                (payload.get("currentStep") or "core").strip() or "core",
                now,
                now,
            ),
        )
        project_id = cur.lastrowid
        _ensure_outline_scaffold(conn, project_id)
    return get_project(project_id)


def list_projects() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM outline_projects ORDER BY updated_at DESC, id DESC").fetchall()
    return [project_summary(get_project(row["id"])) for row in rows]


def project_summary(project: dict) -> dict:
    return {
        "id": project["id"],
        "title": project["title"],
        "genre": project["genre"],
        "premise": project["premise"],
        "currentStep": project["currentStep"],
        "updatedAt": project["updatedAt"],
        "progress": project["progress"],
    }


def get_project(project_id: int) -> dict:
    with connect() as conn:
        project_row = _ensure_project_exists(conn, project_id)
        _ensure_outline_scaffold(conn, project_id)
        characters = conn.execute("SELECT * FROM outline_characters WHERE project_id = ?", (project_id,)).fetchone()
        volume = conn.execute("SELECT * FROM outline_volumes WHERE project_id = ?", (project_id,)).fetchone()
        chapter_rows = {
            row["chapter_no"]: row
            for row in conn.execute(
                "SELECT * FROM outline_chapters WHERE project_id = ? ORDER BY chapter_no ASC",
                (project_id,),
            ).fetchall()
        }
        reviews = conn.execute(
            "SELECT * FROM outline_reviews WHERE project_id = ? ORDER BY id DESC LIMIT 20",
            (project_id,),
        ).fetchall()

    project = _project_row_to_dict(project_row)
    project["characters"] = _characters_row_to_dict(characters)
    project["volume"] = _volume_row_to_dict(volume)
    project["chapters"] = [
        _chapter_row_to_dict(chapter_rows.get(chapter_no), chapter_no)
        for chapter_no in range(1, CHAPTER_COUNT + 1)
    ]
    project["reviews"] = [_review_row_to_dict(row) for row in reviews]
    project["progress"] = _project_progress(project)
    return project


def update_project(project_id: int, payload: dict) -> dict:
    values = {
        column: (payload[key] or "").strip()
        for key, column in PROJECT_FIELDS.items()
        if key in payload and payload[key] is not None
    }
    if "title" in values and not values["title"]:
        raise ValueError("title_required")
    if values:
        assignments = ", ".join(f"{column} = ?" for column in values)
        params = [*values.values(), _now(), project_id]
        with connect() as conn:
            _ensure_project_exists(conn, project_id)
            conn.execute(
                f"UPDATE outline_projects SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(params),
            )
    return get_project(project_id)


def delete_project(project_id: int) -> dict:
    with connect() as conn:
        _ensure_project_exists(conn, project_id)
        conn.execute("DELETE FROM outline_projects WHERE id = ?", (project_id,))
    return {"ok": True}


def _partial_update_project_child(
    project_id: int,
    table: str,
    field_map: dict[str, str],
    payload: dict,
    step: str,
) -> dict:
    values = {
        column: payload[key] or ""
        for key, column in field_map.items()
        if key in payload and payload[key] is not None
    }
    with connect() as conn:
        _ensure_project_exists(conn, project_id)
        _ensure_outline_scaffold(conn, project_id)
        if values:
            assignments = ", ".join(f"{column} = ?" for column in values)
            conn.execute(
                f"UPDATE {table} SET {assignments}, updated_at = ? WHERE project_id = ?",
                (*values.values(), _now(), project_id),
            )
            _touch_project(conn, project_id, step)
    return get_project(project_id)


def update_characters(project_id: int, payload: dict) -> dict:
    return _partial_update_project_child(project_id, "outline_characters", CHARACTER_FIELDS, payload, "characters")


def update_volume(project_id: int, payload: dict) -> dict:
    return _partial_update_project_child(project_id, "outline_volumes", VOLUME_FIELDS, payload, "volume")


def update_chapter(project_id: int, chapter_no: int, payload: dict) -> dict:
    if chapter_no < 1 or chapter_no > CHAPTER_COUNT:
        raise ValueError("chapter_out_of_range")
    values = {
        column: payload[key] or ""
        for key, column in CHAPTER_FIELDS.items()
        if key in payload and payload[key] is not None
    }
    with connect() as conn:
        _ensure_project_exists(conn, project_id)
        _ensure_outline_scaffold(conn, project_id)
        if values:
            assignments = ", ".join(f"{column} = ?" for column in values)
            conn.execute(
                f"UPDATE outline_chapters SET {assignments}, updated_at = ? WHERE project_id = ? AND chapter_no = ?",
                (*values.values(), _now(), project_id, chapter_no),
            )
            _touch_project(conn, project_id, "chapters")
    return get_project(project_id)


def _review_system() -> str:
    return (
        "你是男频连载大纲教练。你只能检查用户自己写的大纲，指出问题并提问，"
        "不能生成新剧情，不能替用户决定走向，不能输出完整替代大纲。严格只输出 JSON。"
    )


def _review_user(project: dict, scope: str, chapter_no: int | None = None) -> str:
    if chapter_no is not None:
        chapter = project["chapters"][chapter_no - 1]
        target = {
            "scope": "chapter",
            "chapter": chapter,
            "projectCore": {
                "title": project["title"],
                "premise": project["premise"],
                "mainGoal": project["mainGoal"],
                "corePayoff": project["corePayoff"],
            },
            "characters": project["characters"],
            "volume": project["volume"],
        }
    elif scope == "characters":
        target = {"scope": scope, "characters": project["characters"], "projectCore": project}
    elif scope == "volume":
        target = {"scope": scope, "volume": project["volume"], "projectCore": project, "characters": project["characters"]}
    else:
        target = {
            "scope": "core",
            "title": project["title"],
            "genre": project["genre"],
            "premise": project["premise"],
            "mainGoal": project["mainGoal"],
            "corePayoff": project["corePayoff"],
        }
    return f"""
请检查下面的大纲信息，只指出问题、追问和修改建议，不要替作者生成剧情。

大纲信息：
{json.dumps(target, ensure_ascii=False)}

请输出严格 JSON：
{{
  "issues": ["最影响追读或开写的具体问题"],
  "questions": ["作者下一步需要回答的具体问题"],
  "suggestions": ["不代写剧情的修改方向"]
}}
""".strip()


def _list_from_review(data: dict, key: str) -> list[str]:
    raw = data.get(key)
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _save_review(project_id: int, scope: str, raw: str, chapter_no: int | None = None) -> dict:
    try:
        data = parse_json_loose(raw)
    except (ValueError, json.JSONDecodeError):
        data = {
            "issues": ["AI 返回内容不是有效 JSON"],
            "questions": ["请稍后重试，或先根据右侧检查清单手动自检。"],
            "suggestions": [raw.strip()[:500] if raw.strip() else "暂无可用建议"],
        }
    issues = _list_from_review(data, "issues")
    questions = _list_from_review(data, "questions")
    suggestions = _list_from_review(data, "suggestions")
    now = _now()
    with connect() as conn:
        _ensure_project_exists(conn, project_id)
        cur = conn.execute(
            """
            INSERT INTO outline_reviews
              (project_id, chapter_no, scope, issues, questions, suggestions, raw, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                chapter_no,
                scope,
                json.dumps(issues, ensure_ascii=False),
                json.dumps(questions, ensure_ascii=False),
                json.dumps(suggestions, ensure_ascii=False),
                raw,
                now,
            ),
        )
        review_id = cur.lastrowid
        row = conn.execute("SELECT * FROM outline_reviews WHERE id = ?", (review_id,)).fetchone()
    return _review_row_to_dict(row)


async def review_project(project_id: int, scope: str, cfg: FullConfig) -> dict:
    if scope not in {"core", "characters", "volume"}:
        raise ValueError("invalid_review_scope")
    project = get_project(project_id)
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(_review_system(), _review_user(project, scope))
    return _save_review(project_id, scope, raw)


async def review_chapter(project_id: int, chapter_no: int, cfg: FullConfig) -> dict:
    if chapter_no < 1 or chapter_no > CHAPTER_COUNT:
        raise ValueError("chapter_out_of_range")
    project = get_project(project_id)
    text_provider = get_text_provider(cfg.text)
    raw = await text_provider.chat(_review_system(), _review_user(project, "chapter", chapter_no=chapter_no))
    return _save_review(project_id, "chapter", raw, chapter_no=chapter_no)
