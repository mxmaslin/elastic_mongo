"""Search model shared between the application layer and the search port."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from stream_catalog.domain.errors import DomainValidationError
from stream_catalog.domain.value_objects import Genre, TitleType

MAX_QUERY_LENGTH = 200
MAX_PAGE_SIZE = 100
MAX_RESULT_WINDOW = 10_000  # Elasticsearch default from+size window


class SearchSort(StrEnum):
    RELEVANCE = "relevance"
    RATING_DESC = "rating_desc"
    YEAR_DESC = "year_desc"
    YEAR_ASC = "year_asc"


@dataclass(frozen=True, slots=True)
class SearchFilters:
    genres: tuple[Genre, ...] = ()
    type: TitleType | None = None
    year_from: int | None = None
    year_to: int | None = None

    def __post_init__(self) -> None:
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise DomainValidationError("year_from must not be greater than year_to")


@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str | None = None
    filters: SearchFilters = field(default_factory=SearchFilters)
    sort: SearchSort = SearchSort.RELEVANCE
    offset: int = 0
    limit: int = 20

    def __post_init__(self) -> None:
        if self.text is not None:
            text = self.text.strip()
            if len(text) > MAX_QUERY_LENGTH:
                raise DomainValidationError("Search text must be at most 200 characters")
            object.__setattr__(self, "text", text or None)
        if not 1 <= self.limit <= MAX_PAGE_SIZE:
            raise DomainValidationError("limit must be within 1..100")
        if self.offset < 0 or self.offset + self.limit > MAX_RESULT_WINDOW:
            raise DomainValidationError("offset is out of the allowed pagination window")


@dataclass(frozen=True, slots=True)
class SearchHit:
    title_id: str
    name: str
    type: TitleType
    release_year: int
    rating: float | None
    genres: tuple[str, ...]
    score: float | None
    highlights: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchResultPage:
    hits: tuple[SearchHit, ...]
    total: int
