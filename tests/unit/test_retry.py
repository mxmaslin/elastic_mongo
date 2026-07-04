"""Retry helper behaviour."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from stream_catalog.infrastructure.retry import with_retries


class Boom(Exception):
    pass


async def test_returns_result_on_first_success() -> None:
    operation = AsyncMock(return_value=42)
    assert await with_retries(operation, retried_exceptions=(Boom,)) == 42
    assert operation.await_count == 1


async def test_retries_then_succeeds() -> None:
    operation = AsyncMock(side_effect=[Boom("1"), Boom("2"), "ok"])
    with patch("stream_catalog.infrastructure.retry.asyncio.sleep") as sleep:
        result = await with_retries(
            operation, retried_exceptions=(Boom,), attempts=3, base_delay=0.1
        )
    assert result == "ok"
    assert operation.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [0.1, 0.2]  # exponential


async def test_raises_after_exhausting_attempts() -> None:
    operation = AsyncMock(side_effect=Boom("always"))
    with patch("stream_catalog.infrastructure.retry.asyncio.sleep"), pytest.raises(Boom):
        await with_retries(operation, retried_exceptions=(Boom,), attempts=3)
    assert operation.await_count == 3


async def test_unlisted_exception_not_retried() -> None:
    operation = AsyncMock(side_effect=ValueError("other"))
    with pytest.raises(ValueError, match="other"):
        await with_retries(operation, retried_exceptions=(Boom,))
    assert operation.await_count == 1


async def test_rejects_zero_attempts() -> None:
    with pytest.raises(ValueError, match="attempts"):
        await with_retries(AsyncMock(), retried_exceptions=(Boom,), attempts=0)
