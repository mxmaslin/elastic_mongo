"""Pydantic request/response schemas and domain mapping helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from stream_catalog.application.commands import CreateTitleCommand, UpdateTitleCommand
from stream_catalog.domain.entities import Episode, Season, Title
from stream_catalog.domain.search import SearchHit, SearchResultPage, SearchSort
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleType

# --- requests ---------------------------------------------------------------


class EpisodeIn(BaseModel):
    number: int
    name: str
    runtime_minutes: int | None = None


class SeasonIn(BaseModel):
    number: int
    episodes: list[EpisodeIn] = Field(default_factory=list)


class TitleCreateRequest(BaseModel):
    name: str
    type: TitleType
    description: str = ""
    genres: list[str] = Field(min_length=1)
    release_year: int
    cast: list[str] = Field(default_factory=list)
    rating: float | None = None
    seasons: list[SeasonIn] = Field(default_factory=list)

    def to_command(self) -> CreateTitleCommand:
        return CreateTitleCommand(
            name=self.name,
            type=self.type,
            description=self.description,
            genres=[Genre(genre) for genre in self.genres],
            release_year=ReleaseYear(self.release_year),
            cast=self.cast,
            rating=Rating(self.rating) if self.rating is not None else None,
            seasons=_seasons_to_domain(self.seasons),
        )


class TitleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    genres: list[str] | None = None
    release_year: int | None = None
    cast: list[str] | None = None
    rating: float | None = None
    seasons: list[SeasonIn] | None = None

    def to_command(self) -> UpdateTitleCommand:
        return UpdateTitleCommand(
            name=self.name,
            description=self.description,
            genres=[Genre(genre) for genre in self.genres] if self.genres is not None else None,
            release_year=(
                ReleaseYear(self.release_year) if self.release_year is not None else None
            ),
            cast=self.cast,
            rating=Rating(self.rating) if self.rating is not None else None,
            seasons=_seasons_to_domain(self.seasons) if self.seasons is not None else None,
        )


def _seasons_to_domain(seasons: list[SeasonIn]) -> list[Season]:
    return [
        Season(
            number=season.number,
            episodes=[
                Episode(
                    number=episode.number,
                    name=episode.name,
                    runtime_minutes=episode.runtime_minutes,
                )
                for episode in season.episodes
            ],
        )
        for season in seasons
    ]


# --- responses ---------------------------------------------------------------


class EpisodeOut(BaseModel):
    number: int
    name: str
    runtime_minutes: int | None


class SeasonOut(BaseModel):
    number: int
    episodes: list[EpisodeOut]


class TitleResponse(BaseModel):
    id: str
    name: str
    type: TitleType
    description: str
    genres: list[str]
    release_year: int
    cast: list[str]
    rating: float | None
    seasons: list[SeasonOut]
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_domain(cls, title: Title) -> TitleResponse:
        return cls(
            id=title.id.value,
            name=title.name,
            type=title.type,
            description=title.description,
            genres=[genre.value for genre in title.genres],
            release_year=title.release_year.value,
            cast=list(title.cast),
            rating=title.rating.value if title.rating is not None else None,
            seasons=[
                SeasonOut(
                    number=season.number,
                    episodes=[
                        EpisodeOut(
                            number=episode.number,
                            name=episode.name,
                            runtime_minutes=episode.runtime_minutes,
                        )
                        for episode in season.episodes
                    ],
                )
                for season in title.seasons
            ],
            created_at=title.created_at,
            updated_at=title.updated_at,
            version=title.version,
        )


class TitlePageResponse(BaseModel):
    items: list[TitleResponse]
    total: int
    offset: int
    limit: int


class SearchHitResponse(BaseModel):
    id: str
    name: str
    type: TitleType
    release_year: int
    rating: float | None
    genres: list[str]
    score: float | None
    highlights: dict[str, list[str]]

    @classmethod
    def from_domain(cls, hit: SearchHit) -> SearchHitResponse:
        return cls(
            id=hit.title_id,
            name=hit.name,
            type=hit.type,
            release_year=hit.release_year,
            rating=hit.rating,
            genres=list(hit.genres),
            score=hit.score,
            highlights={field: list(fragments) for field, fragments in hit.highlights.items()},
        )


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_domain(cls, page: SearchResultPage, *, offset: int, limit: int) -> SearchResponse:
        return cls(
            hits=[SearchHitResponse.from_domain(hit) for hit in page.hits],
            total=page.total,
            offset=offset,
            limit=limit,
        )


class WatchlistItemResponse(BaseModel):
    title_id: str
    added_at: datetime
    title: TitleResponse | None


class WatchlistResponse(BaseModel):
    user_id: str
    items: list[WatchlistItemResponse]


class WatchlistMutationResponse(BaseModel):
    changed: bool


class ReindexResponse(BaseModel):
    indexed: int


class ErrorResponse(BaseModel):
    detail: str


SortParam = Annotated[SearchSort, Field(description="Sort order for search results")]
