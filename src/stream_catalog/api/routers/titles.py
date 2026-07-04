"""Catalog CRUD endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from stream_catalog.api.dependencies import get_catalog_service
from stream_catalog.api.schemas import (
    TitleCreateRequest,
    TitlePageResponse,
    TitleResponse,
    TitleUpdateRequest,
)
from stream_catalog.application.catalog_service import CatalogService
from stream_catalog.domain.value_objects import TitleId

router = APIRouter(prefix="/v1/titles", tags=["titles"])

CatalogDep = Annotated[CatalogService, Depends(get_catalog_service)]


@router.post("", response_model=TitleResponse, status_code=status.HTTP_201_CREATED)
async def create_title(request: TitleCreateRequest, catalog: CatalogDep) -> TitleResponse:
    title = await catalog.create_title(request.to_command())
    return TitleResponse.from_domain(title)


@router.get("", response_model=TitlePageResponse)
async def list_titles(
    catalog: CatalogDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TitlePageResponse:
    titles, total = await catalog.list_titles(offset=offset, limit=limit)
    return TitlePageResponse(
        items=[TitleResponse.from_domain(title) for title in titles],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{title_id}", response_model=TitleResponse)
async def get_title(title_id: str, catalog: CatalogDep) -> TitleResponse:
    title = await catalog.get_title(TitleId(title_id))
    return TitleResponse.from_domain(title)


@router.put("/{title_id}", response_model=TitleResponse)
async def update_title(
    title_id: str, request: TitleUpdateRequest, catalog: CatalogDep
) -> TitleResponse:
    title = await catalog.update_title(TitleId(title_id), request.to_command())
    return TitleResponse.from_domain(title)


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_title(title_id: str, catalog: CatalogDep) -> None:
    await catalog.delete_title(TitleId(title_id))
