"""Application factory and lifespan wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from stream_catalog.api.dependencies import Container
from stream_catalog.api.errors import register_error_handlers
from stream_catalog.api.routers import admin, health, search, titles, watchlists
from stream_catalog.application.catalog_service import CatalogService
from stream_catalog.application.reindex_service import ReindexService
from stream_catalog.application.search_service import SearchService
from stream_catalog.application.watchlist_service import WatchlistService
from stream_catalog.config import Settings
from stream_catalog.domain.errors import SearchUnavailableError
from stream_catalog.infrastructure.elasticsearch.search_index import EsTitleSearchIndex
from stream_catalog.infrastructure.mongo.title_repository import MongoTitleRepository
from stream_catalog.infrastructure.mongo.watchlist_repository import MongoWatchlistRepository

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mongo_client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(
            app_settings.mongo_url,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard",
        )
        es_client = AsyncElasticsearch(app_settings.es_url, request_timeout=10)

        database = mongo_client[app_settings.mongo_db]
        titles_repo = MongoTitleRepository(database)
        watchlists_repo = MongoWatchlistRepository(database)
        search_index = EsTitleSearchIndex(
            es_client,
            index_name=app_settings.es_index,
            refresh_on_write=app_settings.es_refresh_on_write,
            retry_attempts=app_settings.es_retry_attempts,
            retry_base_delay=app_settings.es_retry_base_delay,
        )

        await titles_repo.ensure_indexes()
        try:
            await search_index.ensure_ready()
        except SearchUnavailableError:
            # Do not crash the API: the catalog works without search, and the
            # readiness probe reports the degraded state.
            logger.warning("Elasticsearch unavailable at startup; search is degraded")

        app.state.container = Container(
            mongo_client=mongo_client,
            es_client=es_client,
            catalog=CatalogService(titles_repo, search_index),
            search=SearchService(search_index),
            watchlists=WatchlistService(watchlists_repo, titles_repo),
            reindex=ReindexService(titles_repo, search_index),
        )
        try:
            yield
        finally:
            await es_client.close()
            mongo_client.close()

    app = FastAPI(
        title="Stream Catalog API",
        description=(
            "Media catalog & search demo: MongoDB as the source of truth, "
            "Elasticsearch for full-text search, DDD layering."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    register_error_handlers(app)
    app.include_router(titles.router)
    app.include_router(search.router)
    app.include_router(watchlists.router)
    app.include_router(admin.router)
    app.include_router(health.router)
    return app


app = create_app()
