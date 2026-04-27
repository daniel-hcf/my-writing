import base64

import httpx
from openai import AsyncOpenAI

from ..models import ProviderConfig
from .base import ImageProvider, TextProvider


def _build_client(cfg: ProviderConfig) -> AsyncOpenAI:
    kwargs = {"api_key": cfg.apiKey or "ollama"}
    if cfg.baseUrl:
        kwargs["base_url"] = cfg.baseUrl
    return AsyncOpenAI(**kwargs)


class OpenAITextProvider(TextProvider):
    def __init__(self, cfg: ProviderConfig):
        self.client = _build_client(cfg)
        self.model = cfg.model or "gpt-4o"

    async def chat(self, system: str, user: str, json_mode: bool = True) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


class OpenAIImageProvider(ImageProvider):
    def __init__(self, cfg: ProviderConfig):
        self.client = _build_client(cfg)
        self.model = cfg.model or "gpt-image-1"

    async def generate(self, prompt: str) -> str:
        resp = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        item = resp.data[0]
        if item.b64_json:
            return f"data:image/png;base64,{item.b64_json}"
        if item.url:
            # SiliconFlow 等服务只返回 URL，下载后转 base64 持久化存储
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(item.url)
                r.raise_for_status()
            ctype = r.headers.get("content-type", "image/png").split(";")[0]
            b64 = base64.b64encode(r.content).decode()
            return f"data:{ctype};base64,{b64}"
        raise RuntimeError("图片服务未返回图片数据")
