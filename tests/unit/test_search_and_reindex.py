"""Search query validation and the reindex use case."""

from __future__ import annotations

import pytest

from stream_catalog.application.reindex_service import ReindexService
from stream_catalog.application.search_service import SearchService
from stream_catalog.domain.errors import DomainValidationError, SearchUnavailableError
from stream_catalog.domain.search import SearchFilters, SearchQuery
from tests.unit.factories import make_title
from tests.unit.fakes import FakeSearchIndex, InMemoryTitleRepository


class TestSearchQueryValidation:
    def test_text_is_trimmed_and_blank_becomes_none(self) -> None:
        assert SearchQuery(text="  dune  ").text == "dune"
        assert SearchQuery(text="   ").text is None

    def test_limit_bounds(self) -> None:
        with pytest.raises(DomainValidationError):
            SearchQuery(limit=0)
        with pytest.raises(DomainValidationError):
            SearchQuery(limit=101)

    def test_pagination_window(self) -> None:
        with pytest.raises(DomainValidationError):
            SearchQuery(offset=10_000, limit=1)

    def test_year_range_ordering(self) -> None:
        with pytest.raises(DomainValidationError):
            SearchFilters(year_from=2020, year_to=2010)


class TestSearchService:
    async def test_propagates_unavailability(self) -> None:
        index = FakeSearchIndex()
        index.available = False
        service = SearchService(index)
        with pytest.raises(SearchUnavailableError):
            await service.search_titles(SearchQuery(text="dune"))


class TestReindexService:
    async def test_rebuilds_index_and_streams_everything(self) -> None:
        titles = InMemoryTitleRepository()
        index = FakeSearchIndex()
        for number in range(7):
            await titles.add(make_title(name=f"Movie {number}"))
        service = ReindexService(titles, index)
        indexed = await service.reindex_all()
        assert indexed == 7
        assert index.rebuilds == 1
        assert len(index.indexed) == 7

    async def test_rebuild_replaces_stale_documents(self) -> None:
        titles = InMemoryTitleRepository()
        index = FakeSearchIndex()
        stale = make_title(name="Deleted meanwhile")
        index.indexed[stale.id.value] = stale
        await titles.add(make_title(name="Survivor"))
        indexed = await ReindexService(titles, index).reindex_all()
        assert indexed == 1
        assert [title.name for title in index.indexed.values()] == ["Survivor"]
