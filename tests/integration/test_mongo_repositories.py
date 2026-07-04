"""MongoDB repository behaviour against a real server."""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from stream_catalog.config import Settings
from stream_catalog.domain.entities import Watchlist
from stream_catalog.domain.errors import ConcurrencyConflictError, TitleNotFoundError
from stream_catalog.domain.value_objects import TitleId
from stream_catalog.infrastructure.mongo.title_repository import MongoTitleRepository
from stream_catalog.infrastructure.mongo.watchlist_repository import MongoWatchlistRepository
from tests.unit.factories import make_series, make_title


@pytest_asyncio.fixture
async def titles_repo(
    mongo_client: AsyncIOMotorClient[dict[str, Any]], settings: Settings
) -> MongoTitleRepository:
    repo = MongoTitleRepository(mongo_client[settings.mongo_db])
    await repo.ensure_indexes()
    return repo


@pytest_asyncio.fixture
async def watchlists_repo(
    mongo_client: AsyncIOMotorClient[dict[str, Any]], settings: Settings
) -> MongoWatchlistRepository:
    return MongoWatchlistRepository(mongo_client[settings.mongo_db])


class TestTitleRepository:
    async def test_roundtrip_movie(self, titles_repo: MongoTitleRepository) -> None:
        title = make_title()
        await titles_repo.add(title)
        loaded = await titles_repo.get(title.id)
        assert loaded == title

    async def test_roundtrip_series_with_seasons(self, titles_repo: MongoTitleRepository) -> None:
        series = make_series(seasons_count=2)
        await titles_repo.add(series)
        loaded = await titles_repo.get(series.id)
        assert loaded.seasons == series.seasons

    async def test_get_missing_raises(self, titles_repo: MongoTitleRepository) -> None:
        with pytest.raises(TitleNotFoundError):
            await titles_repo.get(TitleId.new())

    async def test_save_bumps_version(self, titles_repo: MongoTitleRepository) -> None:
        title = make_title()
        await titles_repo.add(title)
        title.update_details(name="Renamed")
        await titles_repo.save(title)
        assert title.version == 1
        loaded = await titles_repo.get(title.id)
        assert loaded.name == "Renamed"
        assert loaded.version == 1

    async def test_stale_save_conflicts(self, titles_repo: MongoTitleRepository) -> None:
        title = make_title()
        await titles_repo.add(title)
        stale = await titles_repo.get(title.id)
        title.update_details(name="First writer")
        await titles_repo.save(title)
        stale.update_details(name="Second writer")
        with pytest.raises(ConcurrencyConflictError):
            await titles_repo.save(stale)

    async def test_delete_and_missing_delete(self, titles_repo: MongoTitleRepository) -> None:
        title = make_title()
        await titles_repo.add(title)
        await titles_repo.delete(title.id)
        with pytest.raises(TitleNotFoundError):
            await titles_repo.delete(title.id)

    async def test_list_page_newest_first(self, titles_repo: MongoTitleRepository) -> None:
        for number in range(5):
            await titles_repo.add(make_title(name=f"Movie {number}"))
        page, total = await titles_repo.list_page(offset=1, limit=2)
        assert total == 5
        assert len(page) == 2
        assert page[0].created_at >= page[1].created_at

    async def test_iter_all(self, titles_repo: MongoTitleRepository) -> None:
        for number in range(3):
            await titles_repo.add(make_title(name=f"Movie {number}"))
        names = {title.name async for title in titles_repo.iter_all()}
        assert names == {"Movie 0", "Movie 1", "Movie 2"}


class TestWatchlistRepository:
    async def test_missing_watchlist_is_empty_aggregate(
        self, watchlists_repo: MongoWatchlistRepository
    ) -> None:
        watchlist = await watchlists_repo.get("nobody")
        assert watchlist.items == []
        assert watchlist.version == 0

    async def test_upsert_and_reload(self, watchlists_repo: MongoWatchlistRepository) -> None:
        watchlist = Watchlist(user_id="user-1")
        watchlist.add(TitleId.new())
        await watchlists_repo.save(watchlist)
        assert watchlist.version == 1
        loaded = await watchlists_repo.get("user-1")
        assert loaded.version == 1
        assert len(loaded.items) == 1

    async def test_stale_save_conflicts(self, watchlists_repo: MongoWatchlistRepository) -> None:
        watchlist = Watchlist(user_id="user-1")
        watchlist.add(TitleId.new())
        await watchlists_repo.save(watchlist)

        stale = Watchlist(user_id="user-1")  # version 0, but version 1 is stored
        stale.add(TitleId.new())
        with pytest.raises(ConcurrencyConflictError):
            await watchlists_repo.save(stale)
