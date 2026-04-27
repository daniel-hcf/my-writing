from fastapi import APIRouter, HTTPException

from ..models import TestRequest
from ..providers import get_image_provider, get_text_provider
from ..services import load_full_config

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/test")
async def test(req: TestRequest):
    cfg = load_full_config()
    try:
        if req.target == "text":
            provider = get_text_provider(cfg.text)
            out = await provider.chat(
                "你是一个测试助手。",
                '请只输出一个 JSON：{"ok": true}',
                json_mode=True,
            )
            return {"ok": True, "preview": out[:200]}
        else:
            provider = get_image_provider(cfg.image)
            url = await provider.generate("a tiny abstract test pattern, minimal")
            return {"ok": True, "preview": url[:64] + "..."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"测试失败：{e}")
