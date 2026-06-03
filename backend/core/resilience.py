"""Retry logic with exponential backoff and circuit breaker for external services."""
import functools
from typing import Any, Callable

import pybreaker
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from backend.core.logging import get_logger

# ── Circuit Breakers ─────────────────────────────────────────

# LLM circuit breaker — fail fast if LLM is down
llm_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="llm_circuit_breaker",
)

google_api_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=120,
    name="google_api_circuit_breaker",
)

search_breaker = pybreaker.CircuitBreaker(
    fail_max=10,
    reset_timeout=30,
    name="search_circuit_breaker",
)


# ── Retry Decorators ─────────────────────────────────────────

def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for retrying with exponential backoff.

    Usage:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def call_external_api():
            ...
    """
    log = get_logger("retry")

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(log._logger, "WARNING"),
    )


def with_circuit_breaker(breaker: pybreaker.CircuitBreaker) -> Callable:
    """
    Decorator to wrap a function with a circuit breaker.

    Usage:
        @with_circuit_breaker(llm_breaker)
        def call_llm():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# ── Combined Retry + Circuit Breaker ─────────────────────────

def resilient_service_call(
    breaker: pybreaker.CircuitBreaker,
    max_attempts: int = 3,
) -> Callable:
    """
    Combined decorator: retry with backoff + circuit breaker.

    Usage:
        @resilient_service_call(llm_breaker, max_attempts=3)
        def call_llm():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @retry_with_backoff(
            max_attempts=max_attempts,
            min_wait=1.0,
            max_wait=30.0,
            exceptions=(ConnectionError, TimeoutError, OSError),
        )
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# ── Circuit Breaker State Check ──────────────────────────────

def get_circuit_breaker_states() -> dict[str, str]:
    """Get current state of all circuit breakers for health check."""
    breakers = {
        "llm": llm_breaker,
        "google_api": google_api_breaker,
        "search": search_breaker,
    }

    states = {}
    for name, breaker in breakers.items():
        state = breaker.current_state
        fail_count = breaker.fail_counter

        if state == "open":
            states[name] = f"OPEN (failing fast, {fail_count} failures)"
        elif state == "half-open":
            states[name] = f"HALF-OPEN (testing recovery, {fail_count} failures)"
        else:
            states[name] = f"CLOSED (healthy, {fail_count} failures)"

    return states
