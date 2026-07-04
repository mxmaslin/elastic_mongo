"""A tiny async retry helper with exponential backoff.

Deliberately hand-rolled instead of pulling a dependency: the policy is a
few lines and stays fully under test.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retries(
    operation: Callable[[], Awaitable[T]],
    *,
    retried_exceptions: tuple[type[Exception], ...],
    attempts: int = 3,
    base_delay: float = 0.1,
) -> T:
    """Run ``operation`` retrying on ``retried_exceptions``.

    Backoff is exponential: base_delay, 2*base_delay, 4*base_delay, ...
    The last failure is re-raised for the caller to translate.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except retried_exceptions as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = base_delay * (2**attempt)
            logger.warning(
                "Operation failed (%s), retry %d/%d in %.2fs",
                exc,
                attempt + 1,
                attempts - 1,
                delay,
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error
