"""Mapping between domain aggregates and MongoDB documents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from stream_catalog.domain.entities import Episode, Season, Title, Watchlist, WatchlistItem
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleId, TitleType


def _as_utc(value: datetime) -> datetime:
    """MongoDB stores naive UTC datetimes; restore tzinfo on the way out."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def title_to_document(title: Title) -> dict[str, Any]:
    return {
        "_id": title.id.value,
        "name": title.name,
        "type": title.type.value,
        "description": title.description,
        "genres": [genre.value for genre in title.genres],
        "release_year": title.release_year.value,
        "cast": list(title.cast),
        "rating": title.rating.value if title.rating is not None else None,
        "seasons": [
            {
                "number": season.number,
                "episodes": [
                    {
                        "number": episode.number,
                        "name": episode.name,
                        "runtime_minutes": episode.runtime_minutes,
                    }
                    for episode in season.episodes
                ],
            }
            for season in title.seasons
        ],
        "created_at": title.created_at,
        "updated_at": title.updated_at,
        "version": title.version,
    }


def title_from_document(document: dict[str, Any]) -> Title:
    return Title(
        id=TitleId(document["_id"]),
        name=document["name"],
        type=TitleType(document["type"]),
        description=document["description"],
        genres=[Genre(genre) for genre in document["genres"]],
        release_year=ReleaseYear(document["release_year"]),
        cast=list(document["cast"]),
        rating=Rating(document["rating"]) if document["rating"] is not None else None,
        seasons=[
            Season(
                number=season["number"],
                episodes=[
                    Episode(
                        number=episode["number"],
                        name=episode["name"],
                        runtime_minutes=episode["runtime_minutes"],
                    )
                    for episode in season["episodes"]
                ],
            )
            for season in document["seasons"]
        ],
        created_at=_as_utc(document["created_at"]),
        updated_at=_as_utc(document["updated_at"]),
        version=document["version"],
    )


def watchlist_to_document(watchlist: Watchlist) -> dict[str, Any]:
    return {
        "_id": watchlist.user_id,
        "items": [
            {"title_id": item.title_id.value, "added_at": item.added_at} for item in watchlist.items
        ],
        "version": watchlist.version,
    }


def watchlist_from_document(document: dict[str, Any]) -> Watchlist:
    return Watchlist(
        user_id=document["_id"],
        items=[
            WatchlistItem(
                title_id=TitleId(item["title_id"]),
                added_at=_as_utc(item["added_at"]),
            )
            for item in document["items"]
        ],
        version=document["version"],
    )
