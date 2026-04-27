from abc import ABC, abstractmethod


class TextProvider(ABC):
    @abstractmethod
    async def chat(self, system: str, user: str, json_mode: bool = True) -> str: ...


class ImageProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """返回 data URL，例如 'data:image/png;base64,...'"""
