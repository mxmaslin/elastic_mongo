"""FastAPI dependencies resolving services from the application container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from elasticsearch import AsyncElasticsearch
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient

from stream_catalog.application.catalog_service import CatalogService
from stream_catalog.application.reindex_service import ReindexService
from stream_catalog.application.search_service import SearchService
from stream_catalog.application.watchlist_service import WatchlistService


@dataclass(slots=True)
class Container:
    mongo_client: AsyncIOMotorClient[dict[str, Any]]
    es_client: AsyncElasticsearch
    catalog: CatalogService
    search: SearchService
    watchlists: WatchlistService
    reindex: ReindexService


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


def get_catalog_service(request: Request) -> CatalogService:
    return get_container(request).catalog


def get_search_service(request: Request) -> SearchService:
    return get_container(request).search


def get_watchlist_service(request: Request) -> WatchlistService:
    return get_container(request).watchlists


def get_reindex_service(request: Request) -> ReindexService:
    return get_container(request).reindex
