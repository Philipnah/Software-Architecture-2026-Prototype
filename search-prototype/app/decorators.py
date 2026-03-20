import functools
import time
from typing import Any, Callable


def timed(operation_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for logging execution time of service operations."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                print(f"[TIMING] {operation_name} took {elapsed_ms:.2f} ms")

        return wrapper

    return decorator
