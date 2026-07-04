"""Full reindex: rebuild the Elasticsearch index from MongoDB.

This is the convergence mechanism for the best-effort indexing strategy:
whatever happened to the search index, one reindex run makes it consistent
with the source of truth again.
"""

from __future__ import annotations

import logging

from stream_catalog.domain.ports import TitleRepository, TitleSearchIndex

logger = logging.getLogger(__name__)


class ReindexService:
    def __init__(self, titles: TitleRepository, search_index: TitleSearchIndex) -> None:
        self._titles = titles
        self._search_index = search_index

    async def reindex_all(self) -> int:
        """Stream every title from the source of truth into a fresh index."""
        indexed = await self._search_index.rebuild(self._titles.iter_all())
        logger.info("Reindex finished: %d titles", indexed)
        return indexed
