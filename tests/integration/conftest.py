"""Integration fixtures: real MongoDB and Elasticsearch.

Run the backing services first: ``docker compose up -d mongo elasticsearch``.
Every test session works in its own database and index (uuid suffix), so
parallel runs and leftovers cannot interfere.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from elasticsearch import AsyncElasticsearch
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from stream_catalog.api.app import create_app
from stream_catalog.config import Settings

pytestmark = pytest.mark.integration


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def settings() -> Settings:
    suffix = uuid.uuid4().hex[:8]
    return Settings(
        mongo_url=os.environ.get("CATALOG_MONGO_URL", "mongodb://localhost:27017"),
        es_url=os.environ.get("CATALOG_ES_URL", "http://localhost:9200"),
        mongo_db=f"stream_catalog_test_{suffix}",
        es_index=f"titles_test_{suffix}",
        es_refresh_on_write=True,  # make writes searchable immediately in tests
    )


@pytest_asyncio.fixture
async def app_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


@pytest_asyncio.fixture
async def mongo_client(settings: Settings) -> AsyncIterator[AsyncIOMotorClient[dict[str, Any]]]:
    client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(
        settings.mongo_url, uuidRepresentation="standard"
    )
    yield client
    client.close()


@pytest_asyncio.fixture
async def es_client(settings: Settings) -> AsyncIterator[AsyncElasticsearch]:
    client = AsyncElasticsearch(settings.es_url)
    yield client
    await client.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_state(
    settings: Settings,
    mongo_client: AsyncIOMotorClient[dict[str, Any]],
    es_client: AsyncElasticsearch,
) -> AsyncIterator[None]:
    """Give every test a blank database and search index.

    The public index name is an alias over uuid-named physical indices, so
    cleanup resolves the alias first and drops the physical indices behind it.
    """
    await mongo_client.drop_database(settings.mongo_db)
    if await es_client.indices.exists_alias(name=settings.es_index):
        aliased = await es_client.indices.get_alias(name=settings.es_index)
        for physical_name in aliased.body:
            await es_client.options(ignore_status=404).indices.delete(index=physical_name)
    else:
        await es_client.options(ignore_status=404).indices.delete(index=settings.es_index)
    yield
