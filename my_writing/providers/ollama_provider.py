import httpx

from ..models import ProviderConfig
from .base import TextProvider


class OllamaTextProvider(TextProvider):
    def __init__(self, cfg: ProviderConfig):
        self.base_url = (cfg.baseUrl or "http://localhost:11434").rstrip("/")
        self.model = cfg.model or "qwen2.5:7b"

    async def chat(self, system: str, user: str, json_mode: bool = True) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("message", {}).get("content", "")
