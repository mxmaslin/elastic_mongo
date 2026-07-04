"""Catalog use cases: CRUD over titles with best-effort search indexing.

Consistency model
-----------------
MongoDB is the source of truth. After every successful write the title is
indexed into Elasticsearch. Indexing is *best effort*: if the search backend
is down (after retries in the adapter), the write still succeeds, a warning
is logged, and the index converges via ``ReindexService``. The trade-off
versus a transactional outbox is documented in the README.
"""

from __future__ import annotations

import logging

from stream_catalog.application.commands import CreateTitleCommand, UpdateTitleCommand
from stream_catalog.domain.entities import Title
from stream_catalog.domain.errors import SearchUnavailableError
from stream_catalog.domain.ports import TitleRepository, TitleSearchIndex
from stream_catalog.domain.value_objects import TitleId

logger = logging.getLogger(__name__)


class CatalogService:
    def __init__(self, titles: TitleRepository, search_index: TitleSearchIndex) -> None:
        self._titles = titles
        self._search_index = search_index

    async def create_title(self, command: CreateTitleCommand) -> Title:
        title = Title.create(
            name=command.name,
            type=command.type,
            description=command.description,
            genres=command.genres,
            release_year=command.release_year,
            cast=command.cast,
            rating=command.rating,
            seasons=command.seasons,
        )
        await self._titles.add(title)
        await self._index_best_effort(title)
        return title

    async def get_title(self, title_id: TitleId) -> Title:
        return await self._titles.get(title_id)

    async def update_title(self, title_id: TitleId, command: UpdateTitleCommand) -> Title:
        title = await self._titles.get(title_id)
        title.update_details(
            name=command.name,
            description=command.description,
            genres=command.genres,
            release_year=command.release_year,
            cast=command.cast,
            rating=command.rating,
            seasons=command.seasons,
        )
        await self._titles.save(title)
        await self._index_best_effort(title)
        return title

    async def delete_title(self, title_id: TitleId) -> None:
        await self._titles.delete(title_id)
        try:
            await self._search_index.remove(title_id)
        except SearchUnavailableError:
            logger.warning(
                "Search index unavailable, title %s not removed from index; "
                "run reindex to converge",
                title_id,
            )

    async def list_titles(self, *, offset: int, limit: int) -> tuple[list[Title], int]:
        return await self._titles.list_page(offset=offset, limit=limit)

    async def _index_best_effort(self, title: Title) -> None:
        try:
            await self._search_index.index(title)
        except SearchUnavailableError:
            logger.warning(
                "Search index unavailable, title %s persisted but not indexed; "
                "run reindex to converge",
                title.id,
            )
