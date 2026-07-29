from typing import Any

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.ai.base import AIProviderBase
from app.core.config import settings


class OpenRouterProvider(AIProviderBase):
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        self.model = settings.openrouter_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError, RateLimitError)),
    )
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        model_name = model or self.model

        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg["role"] if msg["role"] in ("user", "assistant", "system") else "user"
            api_messages.append({"role": role, "content": msg["content"]})

        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            choice = response.choices[0]

            return {
                "content": choice.message.content or "",
                "token_count": response.usage.total_tokens if response.usage else 0,
                "provider": "openrouter",
                "model": model_name,
            }

        except RateLimitError:
            raise Exception("OpenRouter rate limit exceeded. Please try again later.")
        except APITimeoutError:
            raise Exception("OpenRouter request timed out. Please try again.")
        except APIError as e:
            raise Exception(f"OpenRouter API error: {e.status_code} - {e.message}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError, RateLimitError)),
    )
    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        model_name = model or self.model

        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg["role"] if msg["role"] in ("user", "assistant", "system") else "user"
            api_messages.append({"role": role, "content": msg["content"]})

        stream = await self.client.chat.completions.create(
            model=model_name,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def create_embedding(self, text: str, model: str | None = None) -> list[float]:
        raise NotImplementedError("OpenRouter does not support embedding endpoints")

    async def is_available(self) -> bool:
        return bool(settings.openrouter_api_key) and not settings.openrouter_api_key.startswith("YOUR_")
