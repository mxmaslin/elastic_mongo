"""Administrative endpoints.

The reindex endpoint is unauthenticated in this demo; in production it
belongs behind an internal gateway / RBAC (see README, "Production notes").
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from stream_catalog.api.dependencies import get_reindex_service
from stream_catalog.api.schemas import ReindexResponse
from stream_catalog.application.reindex_service import ReindexService

router = APIRouter(prefix="/v1/admin", tags=["admin"])

ReindexDep = Annotated[ReindexService, Depends(get_reindex_service)]


@router.post("/reindex", response_model=ReindexResponse)
async def reindex(reindex_service: ReindexDep) -> ReindexResponse:
    indexed = await reindex_service.reindex_all()
    return ReindexResponse(indexed=indexed)
