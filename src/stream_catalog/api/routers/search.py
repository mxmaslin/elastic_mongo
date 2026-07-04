"""Search endpoints (Elasticsearch-backed)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from stream_catalog.api.dependencies import get_search_service
from stream_catalog.api.schemas import SearchResponse
from stream_catalog.application.search_service import SearchService
from stream_catalog.domain.search import SearchFilters, SearchQuery, SearchSort
from stream_catalog.domain.value_objects import Genre, TitleType

router = APIRouter(prefix="/v1/search", tags=["search"])

SearchDep = Annotated[SearchService, Depends(get_search_service)]


@router.get("/titles", response_model=SearchResponse)
async def search_titles(
    search: SearchDep,
    q: Annotated[str | None, Query(max_length=200, description="Full-text query")] = None,
    genre: Annotated[list[str] | None, Query(description="Filter: genre (repeatable)")] = None,
    type: Annotated[TitleType | None, Query(description="Filter: movie or series")] = None,
    year_from: Annotated[int | None, Query(ge=1888, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=1888, le=2100)] = None,
    sort: Annotated[SearchSort, Query()] = SearchSort.RELEVANCE,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SearchResponse:
    query = SearchQuery(
        text=q,
        filters=SearchFilters(
            genres=tuple(Genre(value) for value in genre) if genre else (),
            type=type,
            year_from=year_from,
            year_to=year_to,
        ),
        sort=sort,
        offset=offset,
        limit=limit,
    )
    page = await search.search_titles(query)
    return SearchResponse.from_domain(page, offset=offset, limit=limit)
