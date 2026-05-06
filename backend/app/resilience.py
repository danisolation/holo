"""Circuit breaker pattern for external API resilience.

Custom AsyncCircuitBreaker — per D-01, all 3 Python circuit breaker libraries
have async bugs or are sync-only.

Three-state machine: CLOSED → OPEN → HALF_OPEN
- CLOSED: normal operation, counting consecutive failures
- OPEN: all calls rejected with CircuitOpenError (after fail_max failures)
- HALF_OPEN: one probe call allowed after cooldown
"""
import asyncio
import time
from enum import Enum

from loguru import logger

from app.config import settings


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""

    def __init__(self, name: str, fail_count: int):
        self.name = name
        self.fail_count = fail_count
        super().__init__(f"Circuit '{name}' is open after {fail_count} consecutive failures")


class AsyncCircuitBreaker:
    def __init__(self, name: str, fail_max: int = 3, reset_timeout: float = 120.0):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._state = CircuitState.CLOSED
        self._fail_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN (cooldown expired)")
        return self._state

    @property
    def fail_count(self) -> int:
        return self._fail_count

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            current = self.state
            if current == CircuitState.OPEN:
                raise CircuitOpenError(self.name, self._fail_count)
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._on_success()
            return result
        except CircuitOpenError:
            raise
        except Exception:
            async with self._lock:
                self._on_failure()
            raise

    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit '{self.name}' HALF_OPEN probe succeeded — closing circuit")
        self._fail_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self):
        self._fail_count += 1
        self._last_failure_time = time.monotonic()
        if self._fail_count >= self.fail_max:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit '{self.name}' OPENED after {self._fail_count} consecutive failures")


# Module-level singletons — per-API isolation
vnstock_breaker = AsyncCircuitBreaker(
    "vnstock",
    fail_max=settings.circuit_breaker_fail_max,
    reset_timeout=settings.circuit_breaker_reset_timeout,
)
cafef_breaker = AsyncCircuitBreaker(
    "cafef",
    fail_max=settings.circuit_breaker_fail_max,
    reset_timeout=settings.circuit_breaker_reset_timeout,
)
gemini_breaker = AsyncCircuitBreaker(
    "gemini",
    fail_max=settings.circuit_breaker_fail_max,
    reset_timeout=settings.circuit_breaker_reset_timeout,
)
vndirect_breaker = AsyncCircuitBreaker(
    "vndirect",
    fail_max=settings.circuit_breaker_fail_max,
    reset_timeout=settings.circuit_breaker_reset_timeout,
)
fireant_breaker = AsyncCircuitBreaker(
    "fireant",
    fail_max=settings.circuit_breaker_fail_max,
    reset_timeout=settings.circuit_breaker_reset_timeout,
)
