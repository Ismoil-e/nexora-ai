from typing import Any

import httpx

from app.ai.base import AIProviderBase
from app.core.config import settings


class GeminiProvider(AIProviderBase):
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client = httpx.AsyncClient(timeout=60.0)

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        model_name = model or "gemini-2.5-flash"
        url = f"{self.base_url}/models/{model_name}:generateContent?key={self.api_key}"

        contents = []
        for msg in messages:
            role = "model" if msg["role"] in ("assistant", "model") else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}],
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        response = await self._client.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        return {
            "content": text,
            "token_count": data.get("usageMetadata", {}).get("totalTokenCount", 0),
            "provider": "gemini",
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

        model_name = model or "gemini-2.5-flash"
        url = f"{self.base_url}/models/{model_name}:streamGenerateContent?alt=sse&key={self.api_key}"

        contents = []
        for msg in messages:
            role = "model" if msg["role"] in ("assistant", "model") else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}],
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async with self._client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(f"Gemini API stream error: {response.status_code} - {error_text.decode('utf-8')}")

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for p in parts:
                                text = p.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue

    async def create_embedding(self, text: str, model: str | None = None) -> list[float]:
        model_name = model or "text-embedding-004"
        url = f"{self.base_url}/models/{model_name}:embedContent?key={self.api_key}"

        payload = {
            "model": f"models/{model_name}",
            "content": {"parts": [{"text": text}]},
        }

        response = await self._client.post(url, json=payload, timeout=30.0)

        if response.status_code != 200:
            raise Exception(f"Gemini embedding error: {response.status_code}")

        data = response.json()
        return data.get("embedding", {}).get("values", [])

    async def is_available(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("YOUR_")

    async def close(self):
        await self._client.aclose()
