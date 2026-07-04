"""Aggregates and entities of the catalog bounded context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from stream_catalog.domain.errors import (
    DomainValidationError,
    WatchlistLimitExceededError,
)
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleId, TitleType

MAX_NAME_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 5000
MAX_GENRES = 8
MAX_CAST = 50
MAX_CAST_MEMBER_LENGTH = 80


def _utc_now() -> datetime:
    # Millisecond precision: BSON datetimes cannot store microseconds, and a
    # domain timestamp that survives a persistence roundtrip must stay equal.
    now = datetime.now(tz=UTC)
    return now.replace(microsecond=now.microsecond - now.microsecond % 1000)


@dataclass(slots=True)
class Episode:
    number: int
    name: str
    runtime_minutes: int | None = None

    def __post_init__(self) -> None:
        if self.number < 1:
            raise DomainValidationError(f"Episode number must be >= 1, got {self.number}")
        self.name = self.name.strip()
        if not self.name:
            raise DomainValidationError("Episode name must not be empty")
        if self.runtime_minutes is not None and self.runtime_minutes <= 0:
            raise DomainValidationError("Episode runtime must be positive")


@dataclass(slots=True)
class Season:
    number: int
    episodes: list[Episode] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.number < 1:
            raise DomainValidationError(f"Season number must be >= 1, got {self.number}")
        numbers = [episode.number for episode in self.episodes]
        if len(numbers) != len(set(numbers)):
            raise DomainValidationError(f"Season {self.number} has duplicate episode numbers")


@dataclass(slots=True)
class Title:
    """Aggregate root: a movie or a series in the catalog.

    ``version`` implements optimistic concurrency; repositories bump it on save.
    """

    id: TitleId
    name: str
    type: TitleType
    description: str
    genres: list[Genre]
    release_year: ReleaseYear
    cast: list[str]
    rating: Rating | None
    seasons: list[Season]
    created_at: datetime
    updated_at: datetime
    version: int = 0

    @classmethod
    def create(
        cls,
        *,
        name: str,
        type: TitleType,
        description: str,
        genres: list[Genre],
        release_year: ReleaseYear,
        cast: list[str] | None = None,
        rating: Rating | None = None,
        seasons: list[Season] | None = None,
        title_id: TitleId | None = None,
    ) -> Title:
        now = _utc_now()
        title = cls(
            id=title_id or TitleId.new(),
            name=name,
            type=type,
            description=description,
            genres=genres,
            release_year=release_year,
            cast=cast or [],
            rating=rating,
            seasons=seasons or [],
            created_at=now,
            updated_at=now,
        )
        title._validate()
        return title

    def update_details(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        genres: list[Genre] | None = None,
        release_year: ReleaseYear | None = None,
        cast: list[str] | None = None,
        rating: Rating | None = None,
        seasons: list[Season] | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if genres is not None:
            self.genres = genres
        if release_year is not None:
            self.release_year = release_year
        if cast is not None:
            self.cast = cast
        if rating is not None:
            self.rating = rating
        if seasons is not None:
            self.seasons = seasons
        self._validate()
        self.updated_at = _utc_now()

    def _validate(self) -> None:
        self.name = self.name.strip()
        if not 1 <= len(self.name) <= MAX_NAME_LENGTH:
            raise DomainValidationError("Title name must be 1..300 characters")
        self.description = self.description.strip()
        if len(self.description) > MAX_DESCRIPTION_LENGTH:
            raise DomainValidationError("Description must be at most 5000 characters")
        if not 1 <= len(self.genres) <= MAX_GENRES:
            raise DomainValidationError("Title must have 1..8 genres")
        if len({genre.value for genre in self.genres}) != len(self.genres):
            raise DomainValidationError("Genres must be unique")
        self.cast = [member.strip() for member in self.cast]
        if len(self.cast) > MAX_CAST:
            raise DomainValidationError("Cast must have at most 50 members")
        if any(not member or len(member) > MAX_CAST_MEMBER_LENGTH for member in self.cast):
            raise DomainValidationError("Cast members must be 1..80 characters")
        if self.type is TitleType.MOVIE and self.seasons:
            raise DomainValidationError("A movie cannot have seasons")
        season_numbers = [season.number for season in self.seasons]
        if len(season_numbers) != len(set(season_numbers)):
            raise DomainValidationError("Season numbers must be unique")


@dataclass(frozen=True, slots=True)
class WatchlistItem:
    title_id: TitleId
    added_at: datetime


@dataclass(slots=True)
class Watchlist:
    """Aggregate root: a per-user list of titles to watch.

    Invariants: no duplicate titles, bounded size. ``add`` is idempotent so the
    API can expose it with PUT semantics.
    """

    MAX_ITEMS = 500

    user_id: str
    items: list[WatchlistItem] = field(default_factory=list)
    version: int = 0

    def __post_init__(self) -> None:
        self.user_id = self.user_id.strip()
        if not self.user_id:
            raise DomainValidationError("Watchlist user id must not be empty")

    def add(self, title_id: TitleId, *, now: datetime | None = None) -> bool:
        """Add a title; return False if it is already present (idempotent)."""
        if self.contains(title_id):
            return False
        if len(self.items) >= self.MAX_ITEMS:
            raise WatchlistLimitExceededError(self.MAX_ITEMS)
        self.items.append(WatchlistItem(title_id=title_id, added_at=now or _utc_now()))
        return True

    def remove(self, title_id: TitleId) -> bool:
        """Remove a title; return False if it was not present (idempotent)."""
        before = len(self.items)
        self.items = [item for item in self.items if item.title_id != title_id]
        return len(self.items) < before

    def contains(self, title_id: TitleId) -> bool:
        return any(item.title_id == title_id for item in self.items)
