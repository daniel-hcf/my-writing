from datetime import datetime

from fastapi import APIRouter, HTTPException

from ..services import (
    assignment_row_to_dict,
    generate_assignment,
    get_assignment_by_id,
    get_or_create_today_assignment,
    insert_assignment,
    is_text_configured,
    latest_weakest_dimension,
    load_full_config,
)

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.get("/today")
async def today():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    try:
        return await get_or_create_today_assignment(cfg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"生成作业失败：{e}")


@router.post("/new")
async def new_assignment():
    """强制生成一道新作业（不管今日是否已有）。"""
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置，请先到设置页填写。")
    try:
        focus = latest_weakest_dimension()
        data = await generate_assignment(focus, cfg)
        today = datetime.now().strftime("%Y-%m-%d")
        aid = insert_assignment(data, today)
        return assignment_row_to_dict(get_assignment_by_id(aid))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"生成作业失败：{e}")


@router.get("/{aid}")
def by_id(aid: int):
    row = get_assignment_by_id(aid)
    if row is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return assignment_row_to_dict(row)
