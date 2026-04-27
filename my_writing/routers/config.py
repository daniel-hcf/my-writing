from fastapi import APIRouter

from ..config import DEFAULTS
from ..db import set_config
from ..models import FullConfig
from ..services import is_image_configured, is_text_configured, load_full_config

router = APIRouter(prefix="/api/config", tags=["config"])

MASK = "***"


@router.get("")
def get_config_endpoint():
    cfg = load_full_config()
    text = cfg.text.model_dump()
    image = cfg.image.model_dump()
    text["apiKey"] = MASK if text["apiKey"] else ""
    image["apiKey"] = MASK if image["apiKey"] else ""
    return {
        "text": text,
        "image": image,
        "ready": {
            "text": is_text_configured(cfg),
            "image": is_image_configured(cfg),
        },
        "defaults": DEFAULTS,
    }


@router.put("")
def put_config_endpoint(payload: FullConfig):
    current = load_full_config()
    text = payload.text.model_dump()
    image = payload.image.model_dump()
    # 若前端传回的是脱敏掩码或空串，保留旧值，避免清空 Key。
    if text["apiKey"] in ("", MASK):
        text["apiKey"] = current.text.apiKey
    if image["apiKey"] in ("", MASK):
        image["apiKey"] = current.image.apiKey
    set_config("text", text)
    set_config("image", image)
    return {"ok": True}
