from datetime import datetime

from fastapi import APIRouter, HTTPException

from ..models import AssignmentDraftUpdate, DailyAssignmentGenerateRequest
from ..services import (
    assignment_row_to_dict,
    cleanup_orphan_assignments,
    delete_assignment_draft,
    get_assignment_by_id,
    get_or_create_journal_assignment,
    get_or_create_today_outline_practice,
    get_or_create_today_assignment,
    get_or_create_today_image_practice,
    is_image_configured,
    is_text_configured,
    load_full_config,
    replace_today_daily_assignment,
    replace_today_image_practice,
    replace_today_outline_practice,
    repeat_daily_assignment,
    save_assignment_draft,
)

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.get("/today")
async def today():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    try:
        return await get_or_create_today_assignment(cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成作业失败：{exc}")


@router.post("/new")
async def new_assignment(payload: DailyAssignmentGenerateRequest | None = None):
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    try:
        cleanup_orphan_assignments()
        return await replace_today_daily_assignment(cfg, intent=payload.intent if payload else "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成作业失败：{exc}")


@router.get("/image-practice/today")
async def image_practice_today():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    if not is_image_configured(cfg):
        raise HTTPException(status_code=400, detail="图片模型未配置，请先到设置页填写。")
    try:
        cleanup_orphan_assignments()
        return await get_or_create_today_image_practice(cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成图片题失败：{exc}")


@router.post("/image-practice/new")
async def new_image_practice_assignment():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    if not is_image_configured(cfg):
        raise HTTPException(status_code=400, detail="图片模型未配置，请先到设置页填写。")
    try:
        cleanup_orphan_assignments()
        return await replace_today_image_practice(cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成图片题失败：{exc}")


@router.get("/outline-practice/today")
async def outline_practice_today():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    try:
        cleanup_orphan_assignments()
        return await get_or_create_today_outline_practice(cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成故事小纲题失败：{exc}")


@router.post("/outline-practice/new")
async def new_outline_practice_assignment():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    try:
        cleanup_orphan_assignments()
        return await replace_today_outline_practice(cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成故事小纲题失败：{exc}")


@router.get("/journal")
def journal():
    today = datetime.now().strftime("%Y-%m-%d")
    return get_or_create_journal_assignment(today)


@router.put("/{aid}/draft")
def save_draft(aid: int, payload: AssignmentDraftUpdate):
    try:
        return save_assignment_draft(aid, payload.content)
    except ValueError as exc:
        if str(exc) == "assignment_not_found":
            raise HTTPException(status_code=404, detail="assignment not found")
        if str(exc) == "draft_not_supported":
            raise HTTPException(status_code=400, detail="draft is not supported for this assignment type")
        if str(exc) == "assignment_already_submitted":
            raise HTTPException(status_code=400, detail="assignment already submitted")
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{aid}/draft")
def delete_draft(aid: int):
    return delete_assignment_draft(aid)


@router.post("/{aid}/repeat")
def repeat_assignment(aid: int):
    try:
        return repeat_daily_assignment(aid)
    except ValueError as exc:
        if str(exc) == "assignment_not_found":
            raise HTTPException(status_code=404, detail="assignment not found")
        if str(exc) == "repeat_only_supports_daily":
            raise HTTPException(status_code=400, detail="repeat is only supported for daily assignments")
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{aid}")
def by_id(aid: int):
    row = get_assignment_by_id(aid)
    if row is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return assignment_row_to_dict(row)
