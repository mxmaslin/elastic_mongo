"""Catalog use cases, including graceful degradation when search is down."""

from __future__ import annotations

import pytest

from stream_catalog.application.catalog_service import CatalogService
from stream_catalog.application.commands import CreateTitleCommand, UpdateTitleCommand
from stream_catalog.domain.errors import TitleNotFoundError
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleId, TitleType
from tests.unit.fakes import FakeSearchIndex, InMemoryTitleRepository


@pytest.fixture
def titles() -> InMemoryTitleRepository:
    return InMemoryTitleRepository()


@pytest.fixture
def search_index() -> FakeSearchIndex:
    return FakeSearchIndex()


@pytest.fixture
def service(titles: InMemoryTitleRepository, search_index: FakeSearchIndex) -> CatalogService:
    return CatalogService(titles, search_index)


def _create_command(name: str = "Inception") -> CreateTitleCommand:
    return CreateTitleCommand(
        name=name,
        type=TitleType.MOVIE,
        description="Dreams within dreams.",
        genres=[Genre("sci-fi")],
        release_year=ReleaseYear(2010),
        rating=Rating(8.8),
    )


async def test_create_persists_and_indexes(
    service: CatalogService,
    titles: InMemoryTitleRepository,
    search_index: FakeSearchIndex,
) -> None:
    title = await service.create_title(_create_command())
    assert title.id.value in titles.storage
    assert title.id.value in search_index.indexed


async def test_create_succeeds_when_search_is_down(
    service: CatalogService,
    titles: InMemoryTitleRepository,
    search_index: FakeSearchIndex,
) -> None:
    search_index.available = False
    title = await service.create_title(_create_command())
    assert title.id.value in titles.storage  # Mongo write survived the ES outage
    assert title.id.value not in search_index.indexed


async def test_update_reindexes(service: CatalogService, search_index: FakeSearchIndex) -> None:
    title = await service.create_title(_create_command())
    updated = await service.update_title(title.id, UpdateTitleCommand(name="Inception (2010)"))
    assert updated.name == "Inception (2010)"
    assert search_index.indexed[title.id.value].name == "Inception (2010)"


async def test_update_missing_title_raises(service: CatalogService) -> None:
    with pytest.raises(TitleNotFoundError):
        await service.update_title(TitleId.new(), UpdateTitleCommand(name="X"))


async def test_delete_removes_from_repo_and_index(
    service: CatalogService,
    titles: InMemoryTitleRepository,
    search_index: FakeSearchIndex,
) -> None:
    title = await service.create_title(_create_command())
    await service.delete_title(title.id)
    assert title.id.value not in titles.storage
    assert title.id.value in search_index.removed


async def test_delete_succeeds_when_search_is_down(
    service: CatalogService,
    titles: InMemoryTitleRepository,
    search_index: FakeSearchIndex,
) -> None:
    title = await service.create_title(_create_command())
    search_index.available = False
    await service.delete_title(title.id)
    assert title.id.value not in titles.storage


async def test_list_titles_pages(service: CatalogService) -> None:
    for index in range(5):
        await service.create_title(_create_command(name=f"Movie {index}"))
    page, total = await service.list_titles(offset=0, limit=3)
    assert total == 5
    assert len(page) == 3
