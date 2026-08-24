import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingService
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.core.config import AIProvider, settings
from app.security.core.prompt_guard import prompt_guard
from app.security.contracts.types import SecurityEventType, SecuritySeverity, SensitivityLevel


class AIService:
    """AI Service with enterprise security: prompt guard, usage audit logging, provider security."""

    def __init__(self, db: AsyncSession, company_id: Optional[uuid.UUID] = None,
                 user_id: Optional[uuid.UUID] = None, agent_id: Optional[str] = None):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.providers = {
            AIProvider.OPENROUTER: OpenRouterProvider(),
            AIProvider.OPENAI: OpenAIProvider(),
            AIProvider.GEMINI: GeminiProvider(),
        }
        self.embedding_service = EmbeddingService()
        self._prompt_guard = prompt_guard

    def _get_provider(self, provider_name: str):
        try:
            provider = AIProvider(provider_name.lower())
            return self.providers.get(provider)
        except ValueError:
            return self.providers.get(settings.default_ai_provider)

    def _scan_user_messages(self, messages: list[dict]) -> None:
        """Scans user messages for prompt injection attempts."""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                is_injection, patterns = self._prompt_guard.scan_for_injection(content)
                if is_injection:
                    import asyncio
                    asyncio.create_task(self._log_injection_attempt(content[:200], patterns))

    async def _log_injection_attempt(self, content_snippet: str, patterns: list):
        """Logs prompt injection attempt as a security event."""
        if not self.company_id:
            return
        from app.models.security import SecurityEvent
        event = SecurityEvent(
            company_id=self.company_id,
            user_id=self.user_id,
            event_type=SecurityEventType.PROMPT_INJECTION_DETECTED.value,
            severity=SecuritySeverity.HIGH.value,
            title="Prompt Injection Urinishi Aniqlandi",
            description=f"Foydalanuvchi xabarida xavfli injection naqshi aniqlandi. Qoldirilgan: {content_snippet[:100]}...",
        )
        self.db.add(event)
        await self.db.flush()

    async def _log_ai_usage(self, provider_name: str, model: str, tokens_in: int,
                             tokens_out: int, duration_ms: int, sensitivity: str = "INTERNAL"):
        """Logs AI usage to the audit trail."""
        if not self.company_id:
            return
        from app.models.security import AIUsageAuditLog
        # Rough cost estimation
        cost = (tokens_in * 0.000001 + tokens_out * 0.000002)  # Approximate
        log_entry = AIUsageAuditLog(
            company_id=self.company_id,
            user_id=self.user_id,
            agent_id=self.agent_id,
            provider=provider_name,
            model=model or "unknown",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=round(cost, 6),
            execution_duration_ms=duration_ms,
            sensitivity_level=sensitivity,
        )
        self.db.add(log_entry)
        await self.db.flush()

    async def chat(
        self,
        provider: str | None = None,
        model: str | None = None,
        messages: list[dict] = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        # Enterprise Security: Scan for prompt injection
        if messages:
            self._scan_user_messages(messages)

        # Apply security guardrails to system prompt
        if system_prompt:
            system_prompt = self._prompt_guard.apply_system_guardrails(system_prompt)

        ai_provider = self._get_provider(provider) if provider else self.providers.get(settings.default_ai_provider)
        if not ai_provider or not await ai_provider.is_available():
            for p in self.providers.values():
                if await p.is_available():
                    ai_provider = p
                    break

        if not ai_provider:
            raise Exception("Hech qanday AI provayder mavjud emas")

        provider_name = provider or settings.default_ai_provider.value
        start = time.time()
        result = await ai_provider.chat(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        duration_ms = int((time.time() - start) * 1000)

        # Enterprise Security: Log AI usage
        tokens_in = sum(len(m.get("content", "").split()) for m in (messages or []))
        tokens_out = len(result.get("content", "").split())
        await self._log_ai_usage(provider_name, model or "default", tokens_in, tokens_out, duration_ms)

        return result

    async def chat_stream(
        self,
        provider: str | None = None,
        model: str | None = None,
        messages: list[dict] = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        # Enterprise Security: Scan for prompt injection
        if messages:
            self._scan_user_messages(messages)

        if system_prompt:
            system_prompt = self._prompt_guard.apply_system_guardrails(system_prompt)

        ai_provider = self._get_provider(provider) if provider else self.providers.get(settings.default_ai_provider)
        if not ai_provider or not await ai_provider.is_available():
            for p in self.providers.values():
                if await p.is_available():
                    ai_provider = p
                    break

        if not ai_provider:
            raise Exception("Hech qanday AI provayder mavjud emas")

        provider_name = provider or settings.default_ai_provider.value
        start = time.time()

        if hasattr(ai_provider, "chat_stream"):
            full_content = []
            async for chunk in ai_provider.chat_stream(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                full_content.append(chunk)
                yield chunk
            duration_ms = int((time.time() - start) * 1000)
            tokens_in = sum(len(m.get("content", "").split()) for m in (messages or []))
            tokens_out = len("".join(full_content).split())
            await self._log_ai_usage(provider_name, model or "default", tokens_in, tokens_out, duration_ms)
            return

        result = await ai_provider.chat(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        duration_ms = int((time.time() - start) * 1000)
        tokens_in = sum(len(m.get("content", "").split()) for m in (messages or []))
        tokens_out = len(result.get("content", "").split())
        await self._log_ai_usage(provider_name, model or "default", tokens_in, tokens_out, duration_ms)
        yield result["content"]

    async def create_embedding(self, text: str) -> list[float]:
        return await self.embedding_service.create_embedding(text)
