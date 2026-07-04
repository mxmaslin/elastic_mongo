"""Domain errors. The API layer maps them onto HTTP status codes."""


class DomainError(Exception):
    """Base class for all domain-level errors."""


class DomainValidationError(DomainError):
    """An invariant or a value-object constraint was violated."""


class TitleNotFoundError(DomainError):
    def __init__(self, title_id: str) -> None:
        super().__init__(f"Title {title_id!r} not found")
        self.title_id = title_id


class ConcurrencyConflictError(DomainError):
    """Optimistic-concurrency check failed: the aggregate was modified concurrently."""


class WatchlistLimitExceededError(DomainError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Watchlist cannot hold more than {limit} items")
        self.limit = limit


class SearchUnavailableError(DomainError):
    """The search backend is unreachable; the catalog itself stays available."""
