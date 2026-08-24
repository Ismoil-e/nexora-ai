"""Model Router — intelligent routing of tasks to the optimal AI provider and model.

Routing decisions are based on:
- Task type (chat, reasoning, document analysis, code, etc.)
- Model capability and context window
- Cost efficiency
- Latency requirements
- Organization policy and data sensitivity
- Provider availability
- User preference where permitted
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    """Extensible task types for routing decisions."""
    CHAT = "chat"
    REASONING = "reasoning"
    DOCUMENT_ANALYSIS = "document_analysis"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SEARCH = "search"
    ANALYTICS = "analytics"
    FORECASTING = "forecasting"
    REPORT_GENERATION = "report_generation"
    PLANNING = "planning"
    CODE = "code"
    TOOL_EXECUTION = "tool_execution"
    AGENT_COORDINATION = "agent_coordination"
    EMBEDDING = "embedding"
    MULTIMODAL = "multimodal"


@dataclass
class ModelCapability:
    """Describes a model's strengths and limits."""
    provider: str
    model: str
    context_window: int = 128000
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_code: bool = False
    cost_per_1k_input: float = 0.001
    cost_per_1k_output: float = 0.002
    latency_ms_avg: int = 1000
    max_output_tokens: int = 4096
    strong_reasoning: bool = False
    languages: list[str] = field(default_factory=lambda: ["en", "uz"])


@dataclass
class RoutingDecision:
    """Result of the routing decision."""
    provider: str
    model: str
    temperature: float
    max_tokens: int
    reasoning: str
    alternatives: list[dict[str, Any]] = field(default_factory=list)


# Default model catalog — configurable per-tenant
DEFAULT_MODEL_CATALOG: list[ModelCapability] = [
    # OpenAI models
    ModelCapability(
        provider="openai", model="gpt-4o", context_window=128000,
        supports_tools=True, supports_vision=True, supports_code=True,
        cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        latency_ms_avg=2000, max_output_tokens=4096, strong_reasoning=True,
    ),
    ModelCapability(
        provider="openai", model="gpt-4o-mini", context_window=128000,
        supports_tools=True, supports_vision=True,
        cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
        latency_ms_avg=800, max_output_tokens=4096,
    ),
    ModelCapability(
        provider="openai", model="gpt-3.5-turbo", context_window=16385,
        supports_tools=True,
        cost_per_1k_input=0.0005, cost_per_1k_output=0.0015,
        latency_ms_avg=600, max_output_tokens=4096,
    ),
    # Gemini models
    ModelCapability(
        provider="gemini", model="gemini-2.5-flash", context_window=1000000,
        supports_tools=True, supports_vision=True, supports_code=True,
        cost_per_1k_input=0.0001, cost_per_1k_output=0.0004,
        latency_ms_avg=700, max_output_tokens=8192, strong_reasoning=True,
    ),
    ModelCapability(
        provider="gemini", model="gemini-2.5-pro", context_window=1000000,
        supports_tools=True, supports_vision=True, supports_code=True,
        cost_per_1k_input=0.00125, cost_per_1k_output=0.005,
        latency_ms_avg=2500, max_output_tokens=65536, strong_reasoning=True,
    ),
    ModelCapability(
        provider="gemini", model="gemini-1.5-pro", context_window=2000000,
        supports_tools=True, supports_vision=True,
        cost_per_1k_input=0.00125, cost_per_1k_output=0.005,
        latency_ms_avg=2000, max_output_tokens=8192, strong_reasoning=True,
    ),
    # OpenRouter models (as pass-through)
    ModelCapability(
        provider="openrouter", model="anthropic/claude-sonnet-4", context_window=200000,
        supports_tools=True, supports_code=True,
        cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        latency_ms_avg=2000, max_output_tokens=8192, strong_reasoning=True,
    ),
    ModelCapability(
        provider="openrouter", model="meta-llama/llama-3.1-70b-instruct", context_window=128000,
        supports_tools=True,
        cost_per_1k_input=0.0004, cost_per_1k_output=0.0006,
        latency_ms_avg=1200, max_output_tokens=4096,
    ),
    # Embedding models
    ModelCapability(
        provider="openai", model="text-embedding-3-small", context_window=8191,
        supports_streaming=False, supports_tools=False,
        cost_per_1k_input=0.00002, cost_per_1k_output=0,
        latency_ms_avg=300, max_output_tokens=0,
    ),
    ModelCapability(
        provider="gemini", model="text-embedding-004", context_window=2048,
        supports_streaming=False, supports_tools=False,
        cost_per_1k_input=0.00001, cost_per_1k_output=0,
        latency_ms_avg=200, max_output_tokens=0,
    ),
]

# Task type → preferred model traits mapping
_TASK_MODEL_PREFERENCES: dict[TaskType, dict[str, Any]] = {
    TaskType.CHAT: {"prefer_fast": True, "min_context": 8000},
    TaskType.REASONING: {"strong_reasoning": True, "min_context": 16000},
    TaskType.DOCUMENT_ANALYSIS: {"supports_vision": True, "min_context": 32000},
    TaskType.SUMMARIZATION: {"min_context": 32000, "prefer_cost_effective": True},
    TaskType.EXTRACTION: {"min_context": 16000},
    TaskType.CLASSIFICATION: {"prefer_fast": True, "prefer_cost_effective": True},
    TaskType.SEARCH: {"prefer_fast": True},
    TaskType.ANALYTICS: {"strong_reasoning": True, "supports_tools": True},
    TaskType.FORECASTING: {"strong_reasoning": True, "min_context": 16000},
    TaskType.REPORT_GENERATION: {"min_context": 32000, "strong_reasoning": True},
    TaskType.PLANNING: {"strong_reasoning": True, "supports_tools": True},
    TaskType.CODE: {"supports_code": True, "strong_reasoning": True},
    TaskType.TOOL_EXECUTION: {"supports_tools": True},
    TaskType.AGENT_COORDINATION: {"strong_reasoning": True, "supports_tools": True},
    TaskType.EMBEDDING: {"is_embedding": True},
    TaskType.MULTIMODAL: {"supports_vision": True, "strong_reasoning": True},
}


def classify_task_type(user_input: str, metadata: dict[str, Any] | None = None) -> TaskType:
    """Heuristic classification of user input into a task type.

    Uses keyword analysis — a real system could use an LLM classifier.
    """
    text = (user_input or "").lower()
    meta = metadata or {}
    explicit = meta.get("task_type")
    if explicit:
        try:
            return TaskType(explicit)
        except ValueError:
            pass

    # Code detection
    code_indicators = ["def ", "class ", "import ", "function ", "const ", "let ",
                       "async ", "await ", "return ", "```", "code", "kod", "yoz",
                       "dastur", "script", "program"]
    if any(ind in text for ind in code_indicators):
        return TaskType.CODE

    # Analytics / KPI
    analytics_indicators = ["tahlil", "analytics", "kpi", "metric", "hisobot",
                            "sotish", "saves", "daromad", "profit", "revenue",
                            "performance", "natija", "dashboard"]
    if any(ind in text for ind in analytics_indicators):
        return TaskType.ANALYTICS

    # Report generation
    report_indicators = ["report", "hisobot", "generate report", "tayyorla",
                         "summarize", "xulosa", "yig'indi"]
    if any(ind in text for ind in report_indicators):
        return TaskType.REPORT_GENERATION

    # Planning
    planning_indicators = ["reja", "plan", "bosqich", "step", "strategy",
                           "tactical", "qanday qilish", "how to", "keyingi qadam"]
    if any(ind in text for ind in planning_indicators):
        return TaskType.PLANNING

    # Document analysis
    doc_indicators = ["hujjat", "document", "pdf", "fayl", "file", "ocr",
                      "rasmdan", "image", "photo", "surat"]
    if any(ind in text for ind in doc_indicators):
        return TaskType.DOCUMENT_ANALYSIS

    # Classification
    class_indicators = ["classify", "categorize", "aniqla", "turkumla",
                        "belgila", "label", "type"]
    if any(ind in text for ind in class_indicators):
        return TaskType.CLASSIFICATION

    # Forecasting
    forecast_indicators = ["prognoz", "forecast", "predict", "bashorat",
                           "kelajak", "future", "trend"]
    if any(ind in text for ind in forecast_indicators):
        return TaskType.FORECASTING

    # Summarization
    summary_indicators = ["qisqacha", "summary", "qisqartir", "shorten",
                          "mohiyat", "essence", "gist"]
    if any(ind in text for ind in summary_indicators):
        return TaskType.SUMMARIZATION

    # Default to chat
    return TaskType.CHAT


class ModelRouter:
    """Routes tasks to the optimal provider/model based on task type and constraints."""

    def __init__(
        self,
        catalog: list[ModelCapability] | None = None,
        provider_policy: dict[str, Any] | None = None,
        default_provider: str = "gemini",
        default_model: str = "gemini-2.5-flash",
    ):
        self.catalog = catalog or DEFAULT_MODEL_CATALOG
        self.provider_policy = provider_policy or {}
        self.default_provider = default_provider
        self.default_model = default_model
        self._availability_cache: dict[str, bool] = {}
        self._cache_ttl = 300  # seconds
        self._last_check: dict[str, float] = {}

    def route(
        self,
        task_type: TaskType | str | None = None,
        *,
        user_input: str = "",
        metadata: dict[str, Any] | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
        required_capabilities: list[str] | None = None,
        max_cost_per_1k: float | None = None,
        data_sensitivity: str = "normal",
    ) -> RoutingDecision:
        """Determine the optimal provider and model for a given task."""
        meta = metadata or {}

        # Use explicit preference if provided
        if preferred_model:
            for cap in self.catalog:
                if cap.model == preferred_model:
                    provider = preferred_provider or cap.provider
                    temp = meta.get("temperature", 0.4)
                    max_tok = meta.get("max_tokens", cap.max_output_tokens)
                    return RoutingDecision(
                        provider=provider,
                        model=preferred_model,
                        temperature=float(temp),
                        max_tokens=int(max_tok),
                        reasoning=f"Explicit model preference: {preferred_model}",
                    )

        # Classify task type
        if task_type:
            try:
                tt = TaskType(task_type) if isinstance(task_type, str) else task_type
            except ValueError:
                tt = classify_task_type(user_input, meta)
        else:
            tt = classify_task_type(user_input, meta)

        # Get preferences for this task type
        prefs = _TASK_MODEL_PREFERENCES.get(tt, {})

        # Filter catalog by required capabilities
        candidates = list(self.catalog)

        # Apply provider policy (disabled providers, allowed providers)
        allowed_providers = self.provider_policy.get("allowed_providers")
        if allowed_providers:
            candidates = [c for c in candidates if c.provider in allowed_providers]

        disabled_providers = self.provider_policy.get("disabled_providers", [])
        candidates = [c for c in candidates if c.provider not in disabled_providers]

        # Filter by required capabilities
        if required_capabilities:
            for req in required_capabilities:
                candidates = [c for c in candidates if getattr(c, req, False)]

        # Filter by task preferences
        if prefs.get("min_context"):
            min_ctx = prefs["min_context"]
            candidates = [c for c in candidates if c.context_window >= min_ctx]

        if prefs.get("strong_reasoning"):
            reasoning_candidates = [c for c in candidates if c.strong_reasoning]
            if reasoning_candidates:
                candidates = reasoning_candidates

        if prefs.get("supports_vision"):
            vision_candidates = [c for c in candidates if c.supports_vision]
            if vision_candidates:
                candidates = vision_candidates

        if prefs.get("supports_code"):
            code_candidates = [c for c in candidates if c.supports_code]
            if code_candidates:
                candidates = code_candidates

        if prefs.get("supports_tools"):
            tool_candidates = [c for c in candidates if c.supports_tools]
            if tool_candidates:
                candidates = tool_candidates

        # Cost constraint
        if max_cost_per_1k is not None:
            candidates = [
                c for c in candidates
                if (c.cost_per_1k_input + c.cost_per_1k_output) <= max_cost_per_1k
            ]

        # Embedding special case
        if prefs.get("is_embedding"):
            embedding_candidates = [
                c for c in candidates
                if c.model.startswith("text-embedding") or "embedding" in c.model
            ]
            if embedding_candidates:
                candidates = embedding_candidates

        # Sensitivity-based routing — for highly sensitive data, prefer local/self-hosted
        if data_sensitivity == "high":
            # Prefer providers with strong data policies
            sensitive_providers = {"openai", "gemini"}
            sensitive_candidates = [c for c in candidates if c.provider in sensitive_providers]
            if sensitive_candidates:
                candidates = sensitive_candidates

        # If preferred provider is specified, boost those
        if preferred_provider:
            provider_boost = [c for c in candidates if c.provider == preferred_provider]
            if provider_boost:
                candidates = provider_boost

        # Scoring and selection
        if not candidates:
            # Fallback to defaults
            return RoutingDecision(
                provider=self.default_provider,
                model=self.default_model,
                temperature=float(meta.get("temperature", 0.4)),
                max_tokens=int(meta.get("max_tokens", 4096)),
                reasoning="No suitable model found — using defaults",
            )

        # Score candidates
        scored = []
        for cap in candidates:
            score = 0.0

            # Prefer cost-effective models for simple tasks
            if prefs.get("prefer_cost_effective"):
                total_cost = cap.cost_per_1k_input + cap.cost_per_1k_output
                score += max(0, 10 - total_cost * 1000)

            # Prefer fast models
            if prefs.get("prefer_fast"):
                score += max(0, 10 - cap.latency_ms_avg / 500)

            # Reasoning bonus
            if prefs.get("strong_reasoning") and cap.strong_reasoning:
                score += 5

            # Large context bonus
            if cap.context_window >= 100000:
                score += 3
            elif cap.context_window >= 32000:
                score += 2

            # Tool support bonus for tool-heavy tasks
            if prefs.get("supports_tools") and cap.supports_tools:
                score += 2

            # Default Gemini flash preference for general tasks
            if cap.provider == "gemini" and "flash" in cap.model:
                score += 1

            scored.append((score, cap))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        alternatives = [
            {"provider": s[1].provider, "model": s[1].model, "score": round(s[0], 2)}
            for s in scored[1:4]
        ]

        temperature = float(meta.get("temperature", 0.4))
        max_tokens = int(meta.get("max_tokens", min(best.max_output_tokens, 4096)))

        return RoutingDecision(
            provider=best.provider,
            model=best.model,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning=f"Task type={tt.value}, scored={round(scored[0][0], 2)}",
            alternatives=alternatives,
        )

    def get_model_info(self, provider: str, model: str) -> ModelCapability | None:
        """Get capability info for a specific model."""
        for cap in self.catalog:
            if cap.provider == provider and cap.model == model:
                return cap
        return None

    def list_models(self, provider: str | None = None) -> list[dict[str, Any]]:
        """List available models, optionally filtered by provider."""
        models = self.catalog
        if provider:
            models = [m for m in models if m.provider == provider]
        return [
            {
                "provider": m.provider,
                "model": m.model,
                "context_window": m.context_window,
                "supports_streaming": m.supports_streaming,
                "supports_tools": m.supports_tools,
                "supports_vision": m.supports_vision,
                "supports_code": m.supports_code,
                "cost_per_1k_input": m.cost_per_1k_input,
                "cost_per_1k_output": m.cost_per_1k_output,
                "strong_reasoning": m.strong_reasoning,
            }
            for m in models
        ]


# Process-wide singleton
model_router = ModelRouter()
