from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.core.config import settings, AIProvider


class EmbeddingService:
    EMBEDDING_MODELS = {
        AIProvider.GEMINI: "text-embedding-004",
        AIProvider.OPENAI: "text-embedding-3-small",
        AIProvider.OPENROUTER: None,
    }
    EMBEDDING_VERSION = "1.0"

    def __init__(self):
        self.providers = {
            AIProvider.OPENROUTER: OpenRouterProvider(),
            AIProvider.GEMINI: GeminiProvider(),
            AIProvider.OPENAI: OpenAIProvider(),
        }

    async def _select_provider(self, provider: AIProvider | None = None):
        selected = provider or settings.default_ai_provider
        ai_provider = self.providers.get(selected)

        if not ai_provider or not await ai_provider.is_available():
            for p in self.providers.values():
                if await p.is_available():
                    ai_provider = p
                    break

        if not ai_provider:
            raise Exception("Hech qanday AI provayder mavjud emas")
        return ai_provider

    async def create_embedding(self, text: str, provider: AIProvider | None = None) -> list[float]:
        ai_provider = await self._select_provider(provider)
        return await ai_provider.create_embedding(text)

    async def get_embedding_info(self, provider: AIProvider | None = None) -> dict:
        """Returns the active embedding model metadata for versioning/dimensions tracking."""
        ai_provider = await self._select_provider(provider)
        selected = provider or settings.default_ai_provider

        model = self.EMBEDDING_MODELS.get(selected)
        if model is None:
            # Fall back to the provider that is actually available
            for key, p in self.providers.items():
                if p is ai_provider:
                    model = self.EMBEDDING_MODELS.get(key)
                    break

        return {
            "provider": str(selected),
            "model": model,
            "version": self.EMBEDDING_VERSION,
        }
