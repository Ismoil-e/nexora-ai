from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingService
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.core.config import AIProvider, settings


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.providers = {
            AIProvider.OPENROUTER: OpenRouterProvider(),
            AIProvider.OPENAI: OpenAIProvider(),
            AIProvider.GEMINI: GeminiProvider(),
        }
        self.embedding_service = EmbeddingService()

    def _get_provider(self, provider_name: str):
        try:
            provider = AIProvider(provider_name.lower())
            return self.providers.get(provider)
        except ValueError:
            return self.providers.get(settings.default_ai_provider)

    async def chat(
        self,
        provider: str | None = None,
        model: str | None = None,
        messages: list[dict] = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        ai_provider = self._get_provider(provider) if provider else self.providers.get(settings.default_ai_provider)
        if not ai_provider or not await ai_provider.is_available():
            for p in self.providers.values():
                if await p.is_available():
                    ai_provider = p
                    break

        if not ai_provider:
            raise Exception("Hech qanday AI provayder mavjud emas")

        return await ai_provider.chat(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat_stream(
        self,
        provider: str | None = None,
        model: str | None = None,
        messages: list[dict] = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        ai_provider = self._get_provider(provider) if provider else self.providers.get(settings.default_ai_provider)
        if not ai_provider or not await ai_provider.is_available():
            for p in self.providers.values():
                if await p.is_available():
                    ai_provider = p
                    break

        if not ai_provider:
            raise Exception("Hech qanday AI provayder mavjud emas")

        if hasattr(ai_provider, "chat_stream"):
            async for chunk in ai_provider.chat_stream(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
            return

        result = await ai_provider.chat(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield result["content"]

    async def create_embedding(self, text: str) -> list[float]:
        return await self.embedding_service.create_embedding(text)
