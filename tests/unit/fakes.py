"""In-memory fakes implementing the domain ports for unit tests."""

from __future__ import annotations

import copy
from collections.abc import AsyncIterable, AsyncIterator, Sequence

from stream_catalog.domain.entities import Title, Watchlist
from stream_catalog.domain.errors import (
    ConcurrencyConflictError,
    SearchUnavailableError,
    TitleNotFoundError,
)
from stream_catalog.domain.search import SearchQuery, SearchResultPage
from stream_catalog.domain.value_objects import TitleId


class InMemoryTitleRepository:
    def __init__(self) -> None:
        self.storage: dict[str, Title] = {}

    async def add(self, title: Title) -> None:
        self.storage[title.id.value] = copy.deepcopy(title)

    async def get(self, title_id: TitleId) -> Title:
        try:
            return copy.deepcopy(self.storage[title_id.value])
        except KeyError:
            raise TitleNotFoundError(title_id.value) from None

    async def save(self, title: Title) -> None:
        stored = self.storage.get(title.id.value)
        if stored is None:
            raise TitleNotFoundError(title.id.value)
        if stored.version != title.version:
            raise ConcurrencyConflictError(f"Title {title.id.value!r} was modified concurrently")
        title.version += 1
        self.storage[title.id.value] = copy.deepcopy(title)

    async def delete(self, title_id: TitleId) -> None:
        if self.storage.pop(title_id.value, None) is None:
            raise TitleNotFoundError(title_id.value)

    async def get_many(self, title_ids: Sequence[TitleId]) -> list[Title]:
        return [
            copy.deepcopy(self.storage[title_id.value])
            for title_id in title_ids
            if title_id.value in self.storage
        ]

    async def list_page(self, *, offset: int, limit: int) -> tuple[list[Title], int]:
        ordered = sorted(self.storage.values(), key=lambda title: title.created_at, reverse=True)
        return copy.deepcopy(ordered[offset : offset + limit]), len(ordered)

    async def iter_all(self) -> AsyncIterator[Title]:
        for title in list(self.storage.values()):
            yield copy.deepcopy(title)


class InMemoryWatchlistRepository:
    def __init__(self) -> None:
        self.storage: dict[str, Watchlist] = {}

    async def get(self, user_id: str) -> Watchlist:
        stored = self.storage.get(user_id)
        if stored is None:
            return Watchlist(user_id=user_id)
        return copy.deepcopy(stored)

    async def save(self, watchlist: Watchlist) -> None:
        stored = self.storage.get(watchlist.user_id)
        current_version = stored.version if stored is not None else 0
        if current_version != watchlist.version:
            raise ConcurrencyConflictError(
                f"Watchlist of {watchlist.user_id!r} was modified concurrently"
            )
        watchlist.version += 1
        self.storage[watchlist.user_id] = copy.deepcopy(watchlist)


class FakeSearchIndex:
    """Records indexing calls; can simulate an unavailable backend."""

    def __init__(self) -> None:
        self.available = True
        self.indexed: dict[str, Title] = {}
        self.removed: list[str] = []
        self.rebuilds = 0
        self.search_queries: list[SearchQuery] = []
        self.search_result = SearchResultPage(hits=(), total=0)

    def _check_available(self) -> None:
        if not self.available:
            raise SearchUnavailableError("search backend is down")

    async def ensure_ready(self) -> None:
        self._check_available()

    async def index(self, title: Title) -> None:
        self._check_available()
        self.indexed[title.id.value] = copy.deepcopy(title)

    async def remove(self, title_id: TitleId) -> None:
        self._check_available()
        self.indexed.pop(title_id.value, None)
        self.removed.append(title_id.value)

    async def search(self, query: SearchQuery) -> SearchResultPage:
        self._check_available()
        self.search_queries.append(query)
        return self.search_result

    async def rebuild(self, titles: AsyncIterable[Title]) -> int:
        self._check_available()
        rebuilt: dict[str, Title] = {}
        async for title in titles:
            rebuilt[title.id.value] = copy.deepcopy(title)
        self.indexed = rebuilt
        self.rebuilds += 1
        return len(rebuilt)
