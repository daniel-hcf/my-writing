from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..config import DAILY_MIN_CHAR_COUNT, IMAGE_PRACTICE_MIN_CHAR_COUNT, OUTLINE_PRACTICE_MIN_CHAR_COUNT
from ..db import connect
from ..models import SubmissionCreate
from ..services import (
    is_text_configured,
    load_full_config,
    pre_generate_tomorrow,
    score_submission,
    submission_row_to_dict,
)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

MIN_CHAR_COUNTS = {
    "daily": DAILY_MIN_CHAR_COUNT,
    "image_practice": IMAGE_PRACTICE_MIN_CHAR_COUNT,
    "outline_practice": OUTLINE_PRACTICE_MIN_CHAR_COUNT,
}


def min_char_count_for_assignment_type(assignment_type: str) -> int:
    return MIN_CHAR_COUNTS.get(assignment_type, 1)


@router.post("")
async def create(payload: SubmissionCreate, background: BackgroundTasks):
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置")
    with connect() as conn:
        arow = conn.execute("SELECT type FROM assignments WHERE id = ?", (payload.assignmentId,)).fetchone()
    if not arow:
        raise HTTPException(status_code=404, detail="作业不存在")
    min_count = min_char_count_for_assignment_type(arow["type"])
    if arow["type"] != "journal" and len(payload.content) < min_count:
        raise HTTPException(status_code=400, detail=f"作品至少 {min_count} 字")
    try:
        result = await score_submission(payload.assignmentId, payload.content, cfg)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"评分失败：{e}")

    background.add_task(pre_generate_tomorrow, cfg)
    return result


@router.get("")
def list_(limit: int = 50):
    limit = max(1, min(200, limit))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT s.*, a.title AS assignment_title, a.type AS assignment_type
            FROM submissions s
            JOIN assignments a ON a.id = s.assignment_id
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = submission_row_to_dict(r)
        d["assignmentTitle"] = r["assignment_title"]
        d["assignmentType"] = r["assignment_type"]
        d["totalScore"] = sum(d["scores"].values())
        out.append(d)
    return out


@router.get("/{sid}")
def by_id(sid: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (sid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return submission_row_to_dict(row)


@router.delete("/{sid}")
def delete(sid: int):
    with connect() as conn:
        row = conn.execute("SELECT id FROM submissions WHERE id = ?", (sid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="记录不存在")
        conn.execute("DELETE FROM submissions WHERE id = ?", (sid,))
    return {"ok": True}
