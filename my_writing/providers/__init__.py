from ..models import ProviderConfig
from .anthropic_provider import AnthropicTextProvider
from .base import ImageProvider, TextProvider
from .ollama_provider import OllamaTextProvider
from .openai_provider import OpenAIImageProvider, OpenAITextProvider


def get_text_provider(cfg: ProviderConfig) -> TextProvider:
    p = cfg.provider.lower()
    if p == "anthropic":
        return AnthropicTextProvider(cfg)
    if p == "ollama":
        return OllamaTextProvider(cfg)
    # openai 与所有 OpenAI 兼容服务统一走这里
    return OpenAITextProvider(cfg)


def get_image_provider(cfg: ProviderConfig) -> ImageProvider:
    p = cfg.provider.lower()
    if p in ("openai", ""):
        return OpenAIImageProvider(cfg)
    raise ValueError(f"暂不支持图片服务：{cfg.provider}")


__all__ = [
    "TextProvider",
    "ImageProvider",
    "get_text_provider",
    "get_image_provider",
]
