from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.core.config import settings, AIProvider


class EmbeddingService:
    def __init__(self):
        self.providers = {
            AIProvider.OPENROUTER: OpenRouterProvider(),
            AIProvider.GEMINI: GeminiProvider(),
            AIProvider.OPENAI: OpenAIProvider(),
        }

    async def create_embedding(self, text: str, provider: AIProvider | None = None) -> list[float]:
        selected = provider or settings.default_ai_provider
        ai_provider = self.providers.get(selected)

        if not ai_provider or not await ai_provider.is_available():
            for p in self.providers.values():
                if await p.is_available():
                    ai_provider = p
                    break

        if not ai_provider:
            raise Exception("Hech qanday AI provayder mavjud emas")

        return await ai_provider.create_embedding(text)
