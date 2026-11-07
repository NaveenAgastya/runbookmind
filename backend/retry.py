"""Small retry-with-backoff decorator used for LLM and Hindsight calls."""
import functools
import logging
import time
from typing import Callable, TypeVar

T = TypeVar("T")
log = logging.getLogger("runbookmind")


def with_retries(attempts: int = 3, base_delay: float = 0.8) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - external services raise many types
                    if attempt == attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    log.warning("%s failed (%s), retry %d/%d in %.1fs", fn.__name__, exc, attempt, attempts - 1, delay)
                    time.sleep(delay)
            raise RuntimeError("unreachable")

        return wrapper

    return decorator
