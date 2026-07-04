"""Per-user watchlist endpoints (idempotent PUT/DELETE)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from stream_catalog.api.dependencies import get_watchlist_service
from stream_catalog.api.schemas import (
    TitleResponse,
    WatchlistItemResponse,
    WatchlistMutationResponse,
    WatchlistResponse,
)
from stream_catalog.application.watchlist_service import WatchlistService
from stream_catalog.domain.value_objects import TitleId

router = APIRouter(prefix="/v1/users/{user_id}/watchlist", tags=["watchlist"])

WatchlistDep = Annotated[WatchlistService, Depends(get_watchlist_service)]


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(user_id: str, watchlists: WatchlistDep) -> WatchlistResponse:
    watchlist, titles = await watchlists.get_watchlist(user_id)
    titles_by_id = {title.id.value: title for title in titles}
    return WatchlistResponse(
        user_id=watchlist.user_id,
        items=[
            WatchlistItemResponse(
                title_id=item.title_id.value,
                added_at=item.added_at,
                title=(
                    TitleResponse.from_domain(titles_by_id[item.title_id.value])
                    if item.title_id.value in titles_by_id
                    else None
                ),
            )
            for item in watchlist.items
        ],
    )


@router.put("/{title_id}", response_model=WatchlistMutationResponse)
async def add_to_watchlist(
    user_id: str, title_id: str, watchlists: WatchlistDep
) -> WatchlistMutationResponse:
    changed = await watchlists.add_title(user_id, TitleId(title_id))
    return WatchlistMutationResponse(changed=changed)


@router.delete("/{title_id}", response_model=WatchlistMutationResponse)
async def remove_from_watchlist(
    user_id: str, title_id: str, watchlists: WatchlistDep
) -> WatchlistMutationResponse:
    changed = await watchlists.remove_title(user_id, TitleId(title_id))
    return WatchlistMutationResponse(changed=changed)
