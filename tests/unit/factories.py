"""Test data builders."""

from __future__ import annotations

from stream_catalog.domain.entities import Episode, Season, Title
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleType


def make_title(
    *,
    name: str = "Inception",
    type: TitleType = TitleType.MOVIE,
    description: str = "A thief who steals corporate secrets through dream-sharing.",
    genres: list[str] | None = None,
    release_year: int = 2010,
    cast: list[str] | None = None,
    rating: float | None = 8.8,
    seasons: list[Season] | None = None,
) -> Title:
    return Title.create(
        name=name,
        type=type,
        description=description,
        genres=[Genre(genre) for genre in (genres or ["sci-fi", "thriller"])],
        release_year=ReleaseYear(release_year),
        cast=cast if cast is not None else ["Leonardo DiCaprio", "Marion Cotillard"],
        rating=Rating(rating) if rating is not None else None,
        seasons=seasons or [],
    )


def make_series(*, name: str = "Dark", seasons_count: int = 2) -> Title:
    seasons = [
        Season(
            number=number,
            episodes=[Episode(number=1, name="Pilot", runtime_minutes=50)],
        )
        for number in range(1, seasons_count + 1)
    ]
    return make_title(
        name=name,
        type=TitleType.SERIES,
        genres=["mystery", "drama"],
        release_year=2017,
        seasons=seasons,
    )
