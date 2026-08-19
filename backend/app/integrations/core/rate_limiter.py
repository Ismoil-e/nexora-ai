import asyncio
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class RateLimitExceeded(Exception):
    pass


class CircuitBreakerOpen(Exception):
    pass


class RateLimitManager:
    """In-memory sliding window rate limiter per tenant/integration."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._history: dict[str, list[float]] = {}

    def check_rate_limit(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60.0

        if key not in self._history:
            self._history[key] = []

        # Filter out timestamps outside the 1 minute window
        self._history[key] = [t for t in self._history[key] if t > window_start]

        if len(self._history[key]) >= self.rpm:
            return False

        self._history[key].append(now)
        return True


class RetryManager:
    """Exponential backoff retry executor with circuit breaker protection."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_sec: float = 1.0,
        backoff_factor: float = 2.0,
        failure_threshold: int = 5,
        reset_timeout_sec: float = 30.0,
    ):
        self.max_retries = max_retries
        self.initial_delay_sec = initial_delay_sec
        self.backoff_factor = backoff_factor
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec

        self._failure_counts: dict[str, int] = {}
        self._last_failure_times: dict[str, float] = {}

    async def execute_with_retry(
        self,
        key: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        now = time.time()
        # Circuit Breaker Check
        if self._failure_counts.get(key, 0) >= self.failure_threshold:
            last_fail = self._last_failure_times.get(key, 0)
            if now - last_fail < self.reset_timeout_sec:
                raise CircuitBreakerOpen(
                    f"Circuit breaker OPEN for '{key}'. System cooling down after consecutive failures."
                )
            else:
                # Reset half-open state
                self._failure_counts[key] = 0

        delay = self.initial_delay_sec
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                # Success clears failure streak
                self._failure_counts[key] = 0
                return result
            except Exception as exc:
                last_exception = exc
                self._failure_counts[key] = self._failure_counts.get(key, 0) + 1
                self._last_failure_times[key] = time.time()

                if attempt == self.max_retries:
                    break

                await asyncio.sleep(delay)
                delay *= self.backoff_factor

        raise last_exception or RuntimeError("Execution failed after maximum retries")


rate_limit_manager = RateLimitManager()
retry_manager = RetryManager()
