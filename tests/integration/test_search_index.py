"""Elasticsearch adapter behaviour against a real server."""

from __future__ import annotations

import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch

from stream_catalog.config import Settings
from stream_catalog.domain.errors import SearchUnavailableError
from stream_catalog.domain.search import SearchFilters, SearchQuery, SearchSort
from stream_catalog.domain.value_objects import Genre, TitleId, TitleType
from stream_catalog.infrastructure.elasticsearch.search_index import EsTitleSearchIndex
from tests.unit.factories import make_series, make_title


@pytest_asyncio.fixture
async def search_index(es_client: AsyncElasticsearch, settings: Settings) -> EsTitleSearchIndex:
    index = EsTitleSearchIndex(
        es_client,
        index_name=settings.es_index,
        refresh_on_write=True,
    )
    await index.ensure_ready()
    return index


@pytest_asyncio.fixture
async def populated_index(search_index: EsTitleSearchIndex) -> EsTitleSearchIndex:
    await search_index.bulk_index(
        [
            make_title(name="Inception", genres=["sci-fi", "thriller"], release_year=2010),
            make_title(name="Interstellar", genres=["sci-fi", "drama"], release_year=2014),
            make_title(
                name="The Grand Budapest Hotel",
                genres=["comedy"],
                release_year=2014,
                rating=8.1,
                cast=["Ralph Fiennes"],
            ),
            make_series(name="Dark"),
        ]
    )
    return search_index


class TestSearch:
    async def test_full_text_relevance(self, populated_index: EsTitleSearchIndex) -> None:
        page = await populated_index.search(SearchQuery(text="inception"))
        assert page.total == 1
        assert page.hits[0].name == "Inception"
        assert page.hits[0].highlights  # highlight fragments returned

    async def test_fuzzy_match_tolerates_typo(self, populated_index: EsTitleSearchIndex) -> None:
        page = await populated_index.search(SearchQuery(text="incepton"))
        assert any(hit.name == "Inception" for hit in page.hits)

    async def test_search_by_cast(self, populated_index: EsTitleSearchIndex) -> None:
        page = await populated_index.search(SearchQuery(text="Ralph Fiennes"))
        assert page.hits
        assert page.hits[0].name == "The Grand Budapest Hotel"

    async def test_genre_and_year_filters(self, populated_index: EsTitleSearchIndex) -> None:
        page = await populated_index.search(
            SearchQuery(
                filters=SearchFilters(genres=(Genre("sci-fi"),), year_from=2012),
                sort=SearchSort.YEAR_DESC,
            )
        )
        assert [hit.name for hit in page.hits] == ["Interstellar"]

    async def test_type_filter(self, populated_index: EsTitleSearchIndex) -> None:
        page = await populated_index.search(
            SearchQuery(filters=SearchFilters(type=TitleType.SERIES))
        )
        assert [hit.name for hit in page.hits] == ["Dark"]

    async def test_sort_by_rating(self, populated_index: EsTitleSearchIndex) -> None:
        page = await populated_index.search(SearchQuery(sort=SearchSort.RATING_DESC, limit=2))
        ratings = [hit.rating for hit in page.hits]
        assert ratings == sorted(ratings, key=lambda value: -(value or 0))

    async def test_pagination(self, populated_index: EsTitleSearchIndex) -> None:
        first = await populated_index.search(SearchQuery(limit=2, sort=SearchSort.YEAR_DESC))
        second = await populated_index.search(
            SearchQuery(limit=2, offset=2, sort=SearchSort.YEAR_DESC)
        )
        assert first.total == second.total == 4
        first_ids = {hit.title_id for hit in first.hits}
        second_ids = {hit.title_id for hit in second.hits}
        assert not first_ids & second_ids


class TestIndexLifecycle:
    async def test_remove_is_idempotent(self, search_index: EsTitleSearchIndex) -> None:
        title = make_title()
        await search_index.index(title)
        await search_index.remove(title.id)
        await search_index.remove(title.id)  # second delete of a missing doc: no error
        page = await search_index.search(SearchQuery())
        assert page.total == 0

    async def test_remove_missing_ok(self, search_index: EsTitleSearchIndex) -> None:
        await search_index.remove(TitleId.new())

    async def test_recreate_drops_documents(self, populated_index: EsTitleSearchIndex) -> None:
        await populated_index.recreate()
        page = await populated_index.search(SearchQuery())
        assert page.total == 0


class TestUnavailability:
    async def test_unreachable_backend_raises_domain_error(self) -> None:
        dead_client = AsyncElasticsearch(
            "http://localhost:59200",  # nothing listens here
            request_timeout=0.2,
            retry_on_timeout=False,
            max_retries=0,
        )
        index = EsTitleSearchIndex(
            dead_client,
            index_name="unused",
            retry_attempts=2,
            retry_base_delay=0.01,
        )
        try:
            with pytest.raises(SearchUnavailableError):
                await index.search(SearchQuery(text="anything"))
        finally:
            await dead_client.close()
