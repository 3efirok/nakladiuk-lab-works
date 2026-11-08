"""Decorators used by the data-processing module."""

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

# Last operations performed by the analytics module (bounded history).
OPERATION_HISTORY: deque[str] = deque(maxlen=5)


def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    """Print the execution time of the decorated function."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        print(f"[time] {func.__name__}: {elapsed * 1e6:.1f} us")
        return result

    return wrapper


def record_operation(history: deque[str], label: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Parameterized decorator: append the operation name to `history` after each call."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        name = label or func.__name__

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            history.append(name)
            return result

        return wrapper

    return decorator


def require_non_empty(func: Callable[..., Any]) -> Callable[..., Any]:
    """Return None instead of calling `func` when the first argument is empty."""

    @wraps(func)
    def wrapper(items: Any, *args: Any, **kwargs: Any) -> Any:
        if not items:
            return None
        return func(items, *args, **kwargs)

    return wrapper
