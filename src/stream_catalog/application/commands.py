"""Input models (commands) for the catalog use cases."""

from __future__ import annotations

from dataclasses import dataclass, field

from stream_catalog.domain.entities import Season
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleType


@dataclass(frozen=True, slots=True)
class CreateTitleCommand:
    name: str
    type: TitleType
    description: str
    genres: list[Genre]
    release_year: ReleaseYear
    cast: list[str] = field(default_factory=list)
    rating: Rating | None = None
    seasons: list[Season] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateTitleCommand:
    """Partial update: ``None`` fields are left unchanged."""

    name: str | None = None
    description: str | None = None
    genres: list[Genre] | None = None
    release_year: ReleaseYear | None = None
    cast: list[str] | None = None
    rating: Rating | None = None
    seasons: list[Season] | None = None
