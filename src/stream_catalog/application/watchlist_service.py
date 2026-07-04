"""Watchlist use cases with optimistic-concurrency retry."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from stream_catalog.domain.entities import Title, Watchlist
from stream_catalog.domain.errors import ConcurrencyConflictError
from stream_catalog.domain.ports import TitleRepository, WatchlistRepository
from stream_catalog.domain.value_objects import TitleId

logger = logging.getLogger(__name__)

_CONFLICT_ATTEMPTS = 3


class WatchlistService:
    def __init__(self, watchlists: WatchlistRepository, titles: TitleRepository) -> None:
        self._watchlists = watchlists
        self._titles = titles

    async def add_title(self, user_id: str, title_id: TitleId) -> bool:
        """Add a title to the user's watchlist; idempotent (PUT semantics).

        Returns True when the item was actually added.
        """
        await self._titles.get(title_id)  # raises TitleNotFoundError for dangling ids

        async def mutation(watchlist: Watchlist) -> bool:
            return watchlist.add(title_id)

        return await self._mutate_with_retry(user_id, mutation)

    async def remove_title(self, user_id: str, title_id: TitleId) -> bool:
        """Remove a title from the watchlist; idempotent (DELETE semantics)."""

        async def mutation(watchlist: Watchlist) -> bool:
            return watchlist.remove(title_id)

        return await self._mutate_with_retry(user_id, mutation)

    async def get_watchlist(self, user_id: str) -> tuple[Watchlist, list[Title]]:
        """Return the watchlist and resolved titles, skipping deleted ones."""
        watchlist = await self._watchlists.get(user_id)
        titles = await self._titles.get_many([item.title_id for item in watchlist.items])
        missing = {item.title_id for item in watchlist.items} - {title.id for title in titles}
        if missing:
            logger.info(
                "Watchlist of %s references %d deleted title(s), skipping: %s",
                user_id,
                len(missing),
                ", ".join(sorted(str(title_id) for title_id in missing)),
            )
        return watchlist, titles

    async def _mutate_with_retry(
        self, user_id: str, mutation: Callable[[Watchlist], Awaitable[bool]]
    ) -> bool:
        """Load-mutate-save with a bounded retry on concurrent modification."""
        for attempt in range(1, _CONFLICT_ATTEMPTS + 1):
            watchlist = await self._watchlists.get(user_id)
            changed = await mutation(watchlist)
            if not changed:
                return False
            try:
                await self._watchlists.save(watchlist)
            except ConcurrencyConflictError:
                if attempt == _CONFLICT_ATTEMPTS:
                    raise
                logger.info(
                    "Watchlist of %s modified concurrently, retrying (%d/%d)",
                    user_id,
                    attempt,
                    _CONFLICT_ATTEMPTS,
                )
                continue
            return True
        raise AssertionError("unreachable")  # pragma: no cover
