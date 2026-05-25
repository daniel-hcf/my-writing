from fastapi import APIRouter, HTTPException

from .. import outlines
from ..models import (
    OutlineChapterUpdate,
    OutlineCharactersUpdate,
    OutlineProjectCreate,
    OutlineProjectUpdate,
    OutlineReviewRequest,
    OutlineVolumeUpdate,
)
from ..services import is_text_configured, load_full_config

router = APIRouter(prefix="/api/outlines", tags=["outlines"])


def _handle_value_error(exc: ValueError) -> None:
    message = str(exc)
    if message == "project_not_found":
        raise HTTPException(status_code=404, detail="project not found")
    if message == "chapter_out_of_range":
        raise HTTPException(status_code=400, detail="chapter number must be between 1 and 10")
    if message == "title_required":
        raise HTTPException(status_code=400, detail="title is required")
    if message == "invalid_review_scope":
        raise HTTPException(status_code=400, detail="invalid review scope")
    raise HTTPException(status_code=400, detail=message)


@router.get("/projects")
def list_projects():
    return outlines.list_projects()


@router.post("/projects")
def create_project(payload: OutlineProjectCreate):
    try:
        return outlines.create_project(payload.model_dump())
    except ValueError as exc:
        _handle_value_error(exc)


@router.get("/projects/{project_id}")
def get_project(project_id: int):
    try:
        return outlines.get_project(project_id)
    except ValueError as exc:
        _handle_value_error(exc)


@router.put("/projects/{project_id}")
def update_project(project_id: int, payload: OutlineProjectUpdate):
    try:
        return outlines.update_project(project_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        _handle_value_error(exc)


@router.delete("/projects/{project_id}")
def delete_project(project_id: int):
    try:
        return outlines.delete_project(project_id)
    except ValueError as exc:
        _handle_value_error(exc)


@router.put("/projects/{project_id}/characters")
def update_characters(project_id: int, payload: OutlineCharactersUpdate):
    try:
        return outlines.update_characters(project_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        _handle_value_error(exc)


@router.put("/projects/{project_id}/volume")
def update_volume(project_id: int, payload: OutlineVolumeUpdate):
    try:
        return outlines.update_volume(project_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        _handle_value_error(exc)


@router.put("/projects/{project_id}/chapters/{chapter_no}")
def update_chapter(project_id: int, chapter_no: int, payload: OutlineChapterUpdate):
    try:
        return outlines.update_chapter(project_id, chapter_no, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        _handle_value_error(exc)


@router.post("/projects/{project_id}/review")
async def review_project(project_id: int, payload: OutlineReviewRequest):
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="text model is not configured")
    try:
        return await outlines.review_project(project_id, payload.scope, cfg)
    except ValueError as exc:
        _handle_value_error(exc)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"review failed: {exc}")


@router.post("/projects/{project_id}/chapters/{chapter_no}/review")
async def review_chapter(project_id: int, chapter_no: int):
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="text model is not configured")
    try:
        return await outlines.review_chapter(project_id, chapter_no, cfg)
    except ValueError as exc:
        _handle_value_error(exc)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"review failed: {exc}")
