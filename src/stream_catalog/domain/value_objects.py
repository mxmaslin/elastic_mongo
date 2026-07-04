"""Value objects: immutable, self-validating primitives of the domain."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from stream_catalog.domain.errors import DomainValidationError

FIRST_FILM_YEAR = 1888  # Roundhay Garden Scene
MAX_RELEASE_YEAR = 2100
MIN_GENRE_LENGTH = 2
MAX_GENRE_LENGTH = 32
MAX_RATING = 10.0


class TitleType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


@dataclass(frozen=True, slots=True)
class TitleId:
    value: str

    def __post_init__(self) -> None:
        try:
            uuid.UUID(self.value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise DomainValidationError(f"Title id must be a UUID, got {self.value!r}") from exc

    @classmethod
    def new(cls) -> TitleId:
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Genre:
    """Normalized (lowercase, trimmed) genre name, e.g. ``drama`` or ``sci-fi``."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not (MIN_GENRE_LENGTH <= len(normalized) <= MAX_GENRE_LENGTH) or not all(
            ch.isalpha() or ch in " -" for ch in normalized
        ):
            raise DomainValidationError(f"Invalid genre: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ReleaseYear:
    value: int

    def __post_init__(self) -> None:
        if not FIRST_FILM_YEAR <= self.value <= MAX_RELEASE_YEAR:
            raise DomainValidationError(
                f"Release year must be within {FIRST_FILM_YEAR}..{MAX_RELEASE_YEAR},"
                f" got {self.value}"
            )

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class Rating:
    """Average rating on a 0..10 scale, stored with one-decimal precision."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= MAX_RATING:
            raise DomainValidationError(f"Rating must be within 0..10, got {self.value}")
        object.__setattr__(self, "value", round(self.value, 1))

    def __float__(self) -> float:
        return self.value
