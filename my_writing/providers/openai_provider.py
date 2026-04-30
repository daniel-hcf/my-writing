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


def _normalize_image_content_type(content_type: str, content: bytes, url: str | None = None) -> str:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype and ctype != "application/octet-stream":
        return ctype

    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    if url:
        lower = url.lower()
        if lower.endswith(".png"):
            return "image/png"
        if lower.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if lower.endswith(".gif"):
            return "image/gif"
        if lower.endswith(".webp"):
            return "image/webp"
    return "image/png"


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
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(item.url)
                response.raise_for_status()
            ctype = _normalize_image_content_type(
                response.headers.get("content-type", "image/png"),
                response.content,
                item.url,
            )
            b64 = base64.b64encode(response.content).decode()
            return f"data:{ctype};base64,{b64}"
        raise RuntimeError("图片服务未返回图片数据")
