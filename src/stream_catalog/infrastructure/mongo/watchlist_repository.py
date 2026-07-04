"""MongoDB implementation of ``WatchlistRepository``.

Persistence uses a version-guarded upsert: a concurrent writer either loses
the version match (matched_count == 0) or hits the unique ``_id`` constraint
(DuplicateKeyError) — both translate into ``ConcurrencyConflictError``.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from stream_catalog.domain.entities import Watchlist
from stream_catalog.domain.errors import ConcurrencyConflictError
from stream_catalog.infrastructure.mongo.mappers import (
    watchlist_from_document,
    watchlist_to_document,
)

COLLECTION = "watchlists"


class MongoWatchlistRepository:
    def __init__(self, database: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = database[COLLECTION]

    async def get(self, user_id: str) -> Watchlist:
        document = await self._collection.find_one({"_id": user_id})
        if document is None:
            return Watchlist(user_id=user_id)
        return watchlist_from_document(document)

    async def save(self, watchlist: Watchlist) -> None:
        document = watchlist_to_document(watchlist)
        document["version"] = watchlist.version + 1
        try:
            result = await self._collection.replace_one(
                {"_id": watchlist.user_id, "version": watchlist.version},
                document,
                upsert=watchlist.version == 0,
            )
        except DuplicateKeyError as exc:
            raise ConcurrencyConflictError(
                f"Watchlist of {watchlist.user_id!r} was created concurrently"
            ) from exc
        if result.matched_count == 0 and result.upserted_id is None:
            raise ConcurrencyConflictError(
                f"Watchlist of {watchlist.user_id!r} was modified concurrently"
            )
        watchlist.version += 1
