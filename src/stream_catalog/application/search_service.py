"""Search use case: a thin façade over the search port.

Unlike catalog writes, search *requires* the backend, so
``SearchUnavailableError`` propagates and the API maps it onto 503.
"""

from __future__ import annotations

from stream_catalog.domain.ports import TitleSearchIndex
from stream_catalog.domain.search import SearchQuery, SearchResultPage


class SearchService:
    def __init__(self, search_index: TitleSearchIndex) -> None:
        self._search_index = search_index

    async def search_titles(self, query: SearchQuery) -> SearchResultPage:
        return await self._search_index.search(query)
