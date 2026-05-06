from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from .. import editorial
from ..config import HOST, PORT
from ..models import EditorialScheduleUpdate, RSSSourceCreate, RSSSourceUpdate, SMTPConfigUpdate
from ..services import is_text_configured, load_full_config

router = APIRouter(prefix="/api/editorial", tags=["editorial"])


def _app_base_url() -> str:
    return f"http://{HOST}:{PORT}"


@router.get("/packs")
def source_packs():
    return editorial.list_source_packs()


@router.post("/packs/{pack_id}/import")
def import_pack(pack_id: str):
    try:
        return editorial.import_source_pack(pack_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/sources")
def sources():
    return editorial.list_sources()


@router.post("/sources")
def create_source(payload: RSSSourceCreate):
    try:
        return editorial.create_source(payload.name, payload.url, payload.channel, payload.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put("/sources/{source_id}")
def update_source(source_id: int, payload: RSSSourceUpdate):
    try:
        return editorial.update_source(source_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/sources/{source_id}")
def delete_source(source_id: int):
    editorial.delete_source(source_id)
    return {"ok": True}


@router.post("/fetch")
async def fetch_sources():
    return await editorial.fetch_enabled_sources()


@router.get("/materials")
def materials(channel: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500)):
    return editorial.list_materials(channel=channel, limit=limit)


@router.get("/materials/{material_id}")
def material(material_id: int):
    item = editorial.get_material(material_id)
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")
    return item


@router.post("/materials/{material_id}/deep-dive")
async def deep_dive(material_id: int):
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置")
    try:
        return await editorial.generate_deep_dive(material_id, cfg)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"深挖失败：{exc}")


@router.post("/materials/{material_id}/story-ideas")
async def story_ideas(material_id: int):
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置")
    try:
        return await editorial.generate_story_ideas(material_id, cfg)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成灵感失败：{exc}")


@router.get("/briefs")
def briefs(limit: int = Query(default=30, ge=1, le=100)):
    return editorial.list_briefs(limit=limit)


@router.post("/briefs/today/generate")
async def generate_today_brief():
    cfg = load_full_config()
    if not is_text_configured(cfg):
        raise HTTPException(status_code=400, detail="文本模型未配置")
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        return await editorial.generate_brief_for_date(today, cfg, app_base_url=_app_base_url(), force=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成简报失败：{exc}")


@router.post("/briefs/{brief_id}/send")
def send_brief(brief_id: int):
    try:
        return editorial.send_brief_email(brief_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"发送失败：{exc}")


@router.get("/smtp")
def get_smtp():
    return editorial.load_smtp_config(mask_secret=True)


@router.put("/smtp")
def put_smtp(payload: SMTPConfigUpdate):
    return editorial.create_or_update_smtp_config(payload.model_dump())


@router.post("/smtp/test")
def test_smtp():
    try:
        return editorial.test_smtp_connection()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SMTP 测试失败：{exc}")


@router.get("/schedule")
def get_schedule():
    return editorial.load_schedule_config()


@router.put("/schedule")
def put_schedule(payload: EditorialScheduleUpdate):
    try:
        return editorial.save_schedule_config(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
