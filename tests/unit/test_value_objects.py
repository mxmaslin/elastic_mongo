"""Value-object validation rules."""

from __future__ import annotations

import pytest

from stream_catalog.domain.errors import DomainValidationError
from stream_catalog.domain.value_objects import Genre, Rating, ReleaseYear, TitleId


class TestTitleId:
    def test_new_generates_valid_uuid(self) -> None:
        title_id = TitleId.new()
        assert TitleId(title_id.value) == title_id

    @pytest.mark.parametrize("raw", ["", "not-a-uuid", "1234"])
    def test_rejects_non_uuid(self, raw: str) -> None:
        with pytest.raises(DomainValidationError):
            TitleId(raw)


class TestGenre:
    def test_normalizes_case_and_whitespace(self) -> None:
        assert Genre("  Sci-Fi ").value == "sci-fi"

    @pytest.mark.parametrize("raw", ["", "a", "x" * 33, "drama!", "123"])
    def test_rejects_invalid(self, raw: str) -> None:
        with pytest.raises(DomainValidationError):
            Genre(raw)

    def test_equality_after_normalization(self) -> None:
        assert Genre("Drama") == Genre("drama")


class TestReleaseYear:
    @pytest.mark.parametrize("year", [1888, 2026, 2100])
    def test_accepts_valid_years(self, year: int) -> None:
        assert ReleaseYear(year).value == year

    @pytest.mark.parametrize("year", [1887, 2101, 0, -5])
    def test_rejects_out_of_range(self, year: int) -> None:
        with pytest.raises(DomainValidationError):
            ReleaseYear(year)


class TestRating:
    def test_rounds_to_one_decimal(self) -> None:
        assert Rating(8.86).value == 8.9
        assert Rating(8.84).value == 8.8

    @pytest.mark.parametrize("value", [-0.1, 10.1])
    def test_rejects_out_of_range(self, value: float) -> None:
        with pytest.raises(DomainValidationError):
            Rating(value)
