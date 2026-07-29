from abc import ABC, abstractmethod
from typing import Any


class AIProviderBase(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def create_embedding(self, text: str, model: str | None = None) -> list[float]:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass
