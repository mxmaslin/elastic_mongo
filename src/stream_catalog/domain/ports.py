"""Ports (interfaces) implemented by the infrastructure layer."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Sequence
from typing import Protocol

from stream_catalog.domain.entities import Title, Watchlist
from stream_catalog.domain.search import SearchQuery, SearchResultPage
from stream_catalog.domain.value_objects import TitleId


class TitleRepository(Protocol):
    """Persistence port for the Title aggregate. MongoDB is the source of truth."""

    async def add(self, title: Title) -> None: ...

    async def get(self, title_id: TitleId) -> Title:
        """Raise ``TitleNotFoundError`` when the title does not exist."""
        ...

    async def get_many(self, title_ids: Sequence[TitleId]) -> list[Title]:
        """Return the titles that exist in one batch; missing ids are skipped."""
        ...

    async def save(self, title: Title) -> None:
        """Persist changes with an optimistic-concurrency check on ``version``.

        Raise ``ConcurrencyConflictError`` on a version mismatch and
        ``TitleNotFoundError`` when the title was deleted concurrently.
        """
        ...

    async def delete(self, title_id: TitleId) -> None:
        """Raise ``TitleNotFoundError`` when the title does not exist."""
        ...

    async def list_page(self, *, offset: int, limit: int) -> tuple[list[Title], int]:
        """Return a page of titles (newest first) and the total count."""
        ...

    def iter_all(self) -> AsyncIterator[Title]:
        """Stream every title; used by the reindex use case."""
        ...


class WatchlistRepository(Protocol):
    """Persistence port for the Watchlist aggregate."""

    async def get(self, user_id: str) -> Watchlist:
        """Return the user's watchlist; an empty aggregate if none is stored yet."""
        ...

    async def save(self, watchlist: Watchlist) -> None:
        """Upsert with an optimistic-concurrency check on ``version``.

        Raise ``ConcurrencyConflictError`` on a version mismatch.
        """
        ...


class TitleSearchIndex(Protocol):
    """Search port. Implementations must raise ``SearchUnavailableError``
    when the backend cannot be reached (after internal retries)."""

    async def ensure_ready(self) -> None:
        """Create the index (mapping included) if it does not exist yet."""
        ...

    async def index(self, title: Title) -> None: ...

    async def remove(self, title_id: TitleId) -> None: ...

    async def search(self, query: SearchQuery) -> SearchResultPage: ...

    async def rebuild(self, titles: AsyncIterable[Title]) -> int:
        """Rebuild the index from scratch without downtime for readers.

        Return the number of indexed titles; used by the reindex use case.
        """
        ...
