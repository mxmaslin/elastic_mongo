"""Aggregate invariants: Title and Watchlist."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from stream_catalog.domain import entities
from stream_catalog.domain.entities import Episode, Season, Watchlist
from stream_catalog.domain.errors import (
    DomainValidationError,
    WatchlistLimitExceededError,
)
from stream_catalog.domain.value_objects import Genre, ReleaseYear, TitleId
from tests.unit.factories import make_series, make_title


class TestTitle:
    def test_create_movie(self) -> None:
        title = make_title()
        assert title.version == 0
        assert title.created_at == title.updated_at

    def test_movie_cannot_have_seasons(self) -> None:
        with pytest.raises(DomainValidationError, match="movie cannot have seasons"):
            make_title(seasons=[Season(number=1)])

    def test_series_with_seasons(self) -> None:
        series = make_series(seasons_count=3)
        assert [season.number for season in series.seasons] == [1, 2, 3]

    def test_duplicate_season_numbers_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="Season numbers must be unique"):
            make_title(
                type=make_series().type,
                seasons=[Season(number=1), Season(number=1)],
            )

    def test_duplicate_episode_numbers_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="duplicate episode numbers"):
            Season(
                number=1,
                episodes=[Episode(number=1, name="A"), Episode(number=1, name="B")],
            )

    def test_name_is_trimmed_and_required(self) -> None:
        title = make_title(name="  Dune  ")
        assert title.name == "Dune"
        with pytest.raises(DomainValidationError):
            make_title(name="   ")

    def test_duplicate_genres_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="Genres must be unique"):
            make_title(genres=["drama", "Drama"])

    def test_update_details_bumps_updated_at_and_validates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        title = make_title()
        later = datetime.now(tz=UTC) + timedelta(seconds=5)
        monkeypatch.setattr(entities, "_utc_now", lambda: later)
        title.update_details(name="Interstellar", release_year=ReleaseYear(2014))
        assert title.name == "Interstellar"
        assert title.updated_at > title.created_at
        with pytest.raises(DomainValidationError):
            title.update_details(genres=[Genre("drama")] * 2)


class TestWatchlist:
    def test_add_is_idempotent(self) -> None:
        watchlist = Watchlist(user_id="user-1")
        title_id = TitleId.new()
        assert watchlist.add(title_id) is True
        assert watchlist.add(title_id) is False
        assert len(watchlist.items) == 1

    def test_remove_is_idempotent(self) -> None:
        watchlist = Watchlist(user_id="user-1")
        title_id = TitleId.new()
        watchlist.add(title_id)
        assert watchlist.remove(title_id) is True
        assert watchlist.remove(title_id) is False

    def test_limit_enforced(self) -> None:
        watchlist = Watchlist(user_id="user-1")
        for _ in range(Watchlist.MAX_ITEMS):
            watchlist.add(TitleId.new())
        with pytest.raises(WatchlistLimitExceededError):
            watchlist.add(TitleId.new())

    def test_empty_user_id_rejected(self) -> None:
        with pytest.raises(DomainValidationError):
            Watchlist(user_id="   ")
