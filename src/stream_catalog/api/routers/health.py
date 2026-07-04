"""Liveness and readiness probes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from stream_catalog.api.dependencies import Container, get_container

router = APIRouter(prefix="/health", tags=["health"])

ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(container: ContainerDep, response: Response) -> dict[str, str]:
    checks: dict[str, str] = {}
    try:
        await container.mongo_client.admin.command("ping")
        checks["mongodb"] = "ok"
    except Exception:  # readiness must not raise, report degraded state instead
        checks["mongodb"] = "unavailable"
    checks["elasticsearch"] = "ok" if await container.es_client.ping() else "unavailable"
    if any(value != "ok" for value in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
