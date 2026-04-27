from anthropic import AsyncAnthropic

from ..models import ProviderConfig
from .base import TextProvider


class AnthropicTextProvider(TextProvider):
    def __init__(self, cfg: ProviderConfig):
        kwargs = {"api_key": cfg.apiKey}
        if cfg.baseUrl:
            kwargs["base_url"] = cfg.baseUrl
        self.client = AsyncAnthropic(**kwargs)
        self.model = cfg.model or "claude-sonnet-4-6"

    async def chat(self, system: str, user: str, json_mode: bool = True) -> str:
        sys_text = system
        if json_mode:
            sys_text = (system + "\n\n严格只输出一个合法 JSON 对象，不要任何额外文字。").strip()
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=sys_text,
            messages=[{"role": "user", "content": user}],
        )
        parts = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)
