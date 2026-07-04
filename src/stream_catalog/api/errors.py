"""Mapping of domain errors onto HTTP responses."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from stream_catalog.domain.errors import (
    ConcurrencyConflictError,
    DomainValidationError,
    SearchUnavailableError,
    TitleNotFoundError,
    WatchlistLimitExceededError,
)

_STATUS_BY_ERROR: list[tuple[type[Exception], int]] = [
    (TitleNotFoundError, HTTPStatus.NOT_FOUND),
    (DomainValidationError, HTTPStatus.UNPROCESSABLE_ENTITY),
    (ConcurrencyConflictError, HTTPStatus.CONFLICT),
    (WatchlistLimitExceededError, HTTPStatus.CONFLICT),
    (SearchUnavailableError, HTTPStatus.SERVICE_UNAVAILABLE),
]


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR:

        def handler(
            request: Request, exc: Exception, status_code: int = status_code
        ) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        app.add_exception_handler(error_type, handler)
