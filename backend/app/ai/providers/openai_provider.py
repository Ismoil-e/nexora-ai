from typing import Any

import httpx

from app.ai.base import AIProviderBase
from app.core.config import settings


class OpenAIProvider(AIProviderBase):
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        model_name = model or "gpt-4o-mini"

        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({
                "role": msg["role"] if msg["role"] in ("user", "assistant", "system") else "user",
                "content": msg["content"],
            })

        payload = {
            "model": model_name,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        data = response.json()
        choice = data["choices"][0]

        return {
            "content": choice["message"]["content"],
            "token_count": data.get("usage", {}).get("total_tokens", 0),
            "provider": "openai",
            "model": model_name,
        }

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        import json

        model_name = model or "gpt-4o-mini"
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({
                "role": msg["role"] if msg["role"] in ("user", "assistant", "system") else "user",
                "content": msg["content"],
            })

        payload = {
            "model": model_name,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"OpenAI API stream error: {response.status_code} - {error_text.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def create_embedding(self, text: str, model: str | None = None) -> list[float]:
        model_name = model or "text-embedding-3-small"

        payload = {
            "model": model_name,
            "input": text,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/embeddings", json=payload, headers=headers)

        if response.status_code != 200:
            raise Exception(f"OpenAI embedding error: {response.status_code}")

        data = response.json()
        return data["data"][0]["embedding"]

    async def is_available(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("YOUR_")
