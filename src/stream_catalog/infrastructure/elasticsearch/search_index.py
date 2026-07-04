"""Elasticsearch implementation of ``TitleSearchIndex``.

All calls go through a retry policy with exponential backoff; when the
backend stays unreachable the adapter raises ``SearchUnavailableError`` and
lets the application layer decide (best-effort for writes, 503 for search).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from elastic_transport import TransportError
from elasticsearch import ApiError, AsyncElasticsearch
from elasticsearch import helpers as es_helpers

from stream_catalog.domain.entities import Title
from stream_catalog.domain.errors import SearchUnavailableError
from stream_catalog.domain.search import (
    SearchHit,
    SearchQuery,
    SearchResultPage,
    SearchSort,
)
from stream_catalog.domain.value_objects import TitleId, TitleType
from stream_catalog.infrastructure.elasticsearch.mapping import TITLES_MAPPING
from stream_catalog.infrastructure.retry import with_retries

_RETRIED = (TransportError,)
_HTTP_NOT_FOUND = 404

_SORT_CLAUSES: dict[SearchSort, list[dict[str, Any]]] = {
    SearchSort.RELEVANCE: [{"_score": "desc"}, {"updated_at": "desc"}],
    SearchSort.RATING_DESC: [{"rating": {"order": "desc", "missing": "_last"}}],
    SearchSort.YEAR_DESC: [{"release_year": "desc"}],
    SearchSort.YEAR_ASC: [{"release_year": "asc"}],
}


def _title_to_source(title: Title) -> dict[str, Any]:
    return {
        "name": title.name,
        "description": title.description,
        "cast": list(title.cast),
        "genres": [genre.value for genre in title.genres],
        "type": title.type.value,
        "release_year": title.release_year.value,
        "rating": title.rating.value if title.rating is not None else None,
        "updated_at": title.updated_at.isoformat(),
    }


class EsTitleSearchIndex:
    def __init__(
        self,
        client: AsyncElasticsearch,
        *,
        index_name: str = "titles",
        refresh_on_write: bool = False,
        retry_attempts: int = 3,
        retry_base_delay: float = 0.1,
    ) -> None:
        self._client = client
        self._index_name = index_name
        # "wait_for" makes writes visible to search before responding; used in tests.
        self._refresh: bool | str = "wait_for" if refresh_on_write else False
        self._retry_attempts = retry_attempts
        self._retry_base_delay = retry_base_delay

    async def ensure_ready(self) -> None:
        async def operation() -> None:
            if not await self._client.indices.exists(index=self._index_name):
                await self._client.indices.create(index=self._index_name, body=TITLES_MAPPING)

        await self._run(operation)

    async def index(self, title: Title) -> None:
        async def operation() -> None:
            await self._client.index(
                index=self._index_name,
                id=title.id.value,
                document=_title_to_source(title),
                refresh=self._refresh,
            )

        await self._run(operation)

    async def remove(self, title_id: TitleId) -> None:
        async def operation() -> None:
            await self._client.delete(
                index=self._index_name,
                id=title_id.value,
                refresh=self._refresh,
            )

        try:
            await self._run(operation)
        except SearchUnavailableError:
            raise
        except ApiError as exc:
            if exc.status_code != _HTTP_NOT_FOUND:  # already absent: idempotent delete
                raise

    async def search(self, query: SearchQuery) -> SearchResultPage:
        request = self._build_request(query)

        async def operation() -> Any:
            return await self._client.search(index=self._index_name, **request)

        response = await self._run(operation)
        hits_section = response["hits"]
        hits = tuple(
            SearchHit(
                title_id=hit["_id"],
                name=hit["_source"]["name"],
                type=TitleType(hit["_source"]["type"]),
                release_year=hit["_source"]["release_year"],
                rating=hit["_source"]["rating"],
                genres=tuple(hit["_source"]["genres"]),
                score=hit.get("_score"),
                highlights={
                    field: tuple(fragments) for field, fragments in hit.get("highlight", {}).items()
                },
            )
            for hit in hits_section["hits"]
        )
        return SearchResultPage(hits=hits, total=hits_section["total"]["value"])

    async def bulk_index(self, titles: Sequence[Title]) -> int:
        async def operation() -> int:
            success, _ = await es_helpers.async_bulk(
                self._client,
                (
                    {
                        "_index": self._index_name,
                        "_id": title.id.value,
                        "_source": _title_to_source(title),
                    }
                    for title in titles
                ),
                refresh=self._refresh,
            )
            return success

        indexed: int = await self._run(operation)
        return indexed

    async def recreate(self) -> None:
        async def operation() -> None:
            await self._client.options(ignore_status=404).indices.delete(index=self._index_name)
            await self._client.indices.create(index=self._index_name, body=TITLES_MAPPING)

        await self._run(operation)

    def _build_request(self, query: SearchQuery) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query.text:
            must.append(
                {
                    "multi_match": {
                        "query": query.text,
                        "fields": ["name^3", "cast^2", "description"],
                        "fuzziness": "AUTO",
                    }
                }
            )
        filters: list[dict[str, Any]] = []
        if query.filters.genres:
            filters.append({"terms": {"genres": [genre.value for genre in query.filters.genres]}})
        if query.filters.type is not None:
            filters.append({"term": {"type": query.filters.type.value}})
        year_range: dict[str, int] = {}
        if query.filters.year_from is not None:
            year_range["gte"] = query.filters.year_from
        if query.filters.year_to is not None:
            year_range["lte"] = query.filters.year_to
        if year_range:
            filters.append({"range": {"release_year": year_range}})

        return {
            "query": {"bool": {"must": must or [{"match_all": {}}], "filter": filters}},
            "sort": _SORT_CLAUSES[query.sort],
            "from_": query.offset,
            "size": query.limit,
            "highlight": {"fields": {"name": {}, "description": {}}},
            "track_total_hits": True,
        }

    async def _run(self, operation: Any) -> Any:
        try:
            return await with_retries(
                operation,
                retried_exceptions=_RETRIED,
                attempts=self._retry_attempts,
                base_delay=self._retry_base_delay,
            )
        except TransportError as exc:
            raise SearchUnavailableError(str(exc)) from exc
