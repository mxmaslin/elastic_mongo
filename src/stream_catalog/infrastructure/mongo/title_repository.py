"""MongoDB implementation of ``TitleRepository`` with optimistic concurrency."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from stream_catalog.domain.entities import Title
from stream_catalog.domain.errors import ConcurrencyConflictError, TitleNotFoundError
from stream_catalog.domain.value_objects import TitleId
from stream_catalog.infrastructure.mongo.mappers import title_from_document, title_to_document

COLLECTION = "titles"


class MongoTitleRepository:
    def __init__(self, database: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        self._collection = database[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("created_at", -1)])
        await self._collection.create_index("genres")

    async def add(self, title: Title) -> None:
        await self._collection.insert_one(title_to_document(title))

    async def get(self, title_id: TitleId) -> Title:
        document = await self._collection.find_one({"_id": title_id.value})
        if document is None:
            raise TitleNotFoundError(title_id.value)
        return title_from_document(document)

    async def save(self, title: Title) -> None:
        document = title_to_document(title)
        document["version"] = title.version + 1
        result = await self._collection.replace_one(
            {"_id": title.id.value, "version": title.version},
            document,
        )
        if result.matched_count == 0:
            exists = await self._collection.count_documents({"_id": title.id.value}, limit=1)
            if exists:
                raise ConcurrencyConflictError(
                    f"Title {title.id.value!r} was modified concurrently"
                )
            raise TitleNotFoundError(title.id.value)
        title.version += 1

    async def delete(self, title_id: TitleId) -> None:
        result = await self._collection.delete_one({"_id": title_id.value})
        if result.deleted_count == 0:
            raise TitleNotFoundError(title_id.value)

    async def list_page(self, *, offset: int, limit: int) -> tuple[list[Title], int]:
        total = await self._collection.count_documents({})
        cursor = self._collection.find({}).sort("created_at", -1).skip(offset).limit(limit)
        titles = [title_from_document(document) async for document in cursor]
        return titles, total

    async def iter_all(self) -> AsyncIterator[Title]:
        async for document in self._collection.find({}):
            yield title_from_document(document)
