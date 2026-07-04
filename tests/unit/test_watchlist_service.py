"""Watchlist use cases, including the optimistic-concurrency retry loop."""

from __future__ import annotations

import pytest

from stream_catalog.application.watchlist_service import WatchlistService
from stream_catalog.domain.entities import Watchlist
from stream_catalog.domain.errors import ConcurrencyConflictError, TitleNotFoundError
from stream_catalog.domain.value_objects import TitleId
from tests.unit.factories import make_title
from tests.unit.fakes import InMemoryTitleRepository, InMemoryWatchlistRepository


@pytest.fixture
def titles() -> InMemoryTitleRepository:
    return InMemoryTitleRepository()


@pytest.fixture
def watchlists() -> InMemoryWatchlistRepository:
    return InMemoryWatchlistRepository()


@pytest.fixture
def service(
    watchlists: InMemoryWatchlistRepository, titles: InMemoryTitleRepository
) -> WatchlistService:
    return WatchlistService(watchlists, titles)


async def test_add_and_get(service: WatchlistService, titles: InMemoryTitleRepository) -> None:
    title = make_title()
    await titles.add(title)
    assert await service.add_title("user-1", title.id) is True
    watchlist, resolved = await service.get_watchlist("user-1")
    assert [item.title_id for item in watchlist.items] == [title.id]
    assert [resolved_title.id for resolved_title in resolved] == [title.id]


async def test_add_is_idempotent(
    service: WatchlistService, titles: InMemoryTitleRepository
) -> None:
    title = make_title()
    await titles.add(title)
    assert await service.add_title("user-1", title.id) is True
    assert await service.add_title("user-1", title.id) is False


async def test_add_unknown_title_raises(service: WatchlistService) -> None:
    with pytest.raises(TitleNotFoundError):
        await service.add_title("user-1", TitleId.new())


async def test_remove_missing_is_noop(service: WatchlistService) -> None:
    assert await service.remove_title("user-1", TitleId.new()) is False


async def test_deleted_titles_skipped_in_get(
    service: WatchlistService, titles: InMemoryTitleRepository
) -> None:
    title = make_title()
    await titles.add(title)
    await service.add_title("user-1", title.id)
    await titles.delete(title.id)
    watchlist, resolved = await service.get_watchlist("user-1")
    assert len(watchlist.items) == 1  # the item survives
    assert resolved == []  # but the missing title is skipped, not an error


async def test_conflict_retried(
    service: WatchlistService,
    watchlists: InMemoryWatchlistRepository,
    titles: InMemoryTitleRepository,
) -> None:
    """First save hits a concurrent modification, the retry succeeds."""
    title = make_title()
    await titles.add(title)

    original_save = watchlists.save
    failures = {"left": 1}

    async def flaky_save(watchlist: Watchlist) -> None:
        if failures["left"] > 0:
            failures["left"] -= 1
            raise ConcurrencyConflictError("simulated concurrent write")
        await original_save(watchlist)

    watchlists.save = flaky_save  # type: ignore[method-assign]
    assert await service.add_title("user-1", title.id) is True
    stored = await watchlists.get("user-1")
    assert stored.contains(title.id)


async def test_conflict_exhausts_retries(
    service: WatchlistService,
    watchlists: InMemoryWatchlistRepository,
    titles: InMemoryTitleRepository,
) -> None:
    title = make_title()
    await titles.add(title)

    async def always_conflict(watchlist: Watchlist) -> None:
        raise ConcurrencyConflictError("simulated permanent conflict")

    watchlists.save = always_conflict  # type: ignore[method-assign]
    with pytest.raises(ConcurrencyConflictError):
        await service.add_title("user-1", title.id)
