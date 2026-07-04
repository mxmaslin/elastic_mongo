"""Full reindex: rebuild the Elasticsearch index from MongoDB.

This is the convergence mechanism for the best-effort indexing strategy:
whatever happened to the search index, one reindex run makes it consistent
with the source of truth again.
"""

from __future__ import annotations

import logging

from stream_catalog.domain.entities import Title
from stream_catalog.domain.ports import TitleRepository, TitleSearchIndex

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


class ReindexService:
    def __init__(self, titles: TitleRepository, search_index: TitleSearchIndex) -> None:
        self._titles = titles
        self._search_index = search_index

    async def reindex_all(self) -> int:
        """Recreate the index and stream every title into it in batches."""
        await self._search_index.recreate()
        indexed = 0
        batch: list[Title] = []
        async for title in self._titles.iter_all():
            batch.append(title)
            if len(batch) >= _BATCH_SIZE:
                indexed += await self._search_index.bulk_index(batch)
                batch.clear()
        if batch:
            indexed += await self._search_index.bulk_index(batch)
        logger.info("Reindex finished: %d titles", indexed)
        return indexed
