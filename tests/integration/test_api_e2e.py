"""End-to-end API tests: FastAPI + MongoDB + Elasticsearch."""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

MOVIE_PAYLOAD: dict[str, Any] = {
    "name": "Inception",
    "type": "movie",
    "description": "A thief steals corporate secrets through dream-sharing technology.",
    "genres": ["Sci-Fi", "thriller"],
    "release_year": 2010,
    "cast": ["Leonardo DiCaprio"],
    "rating": 8.8,
}

SERIES_PAYLOAD: dict[str, Any] = {
    "name": "Dark",
    "type": "series",
    "description": "Family secrets across time in a small German town.",
    "genres": ["mystery", "drama"],
    "release_year": 2017,
    "seasons": [
        {"number": 1, "episodes": [{"number": 1, "name": "Secrets", "runtime_minutes": 51}]},
        {"number": 2, "episodes": []},
    ],
}


async def _create(client: AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post("/v1/titles", json=payload)
    assert response.status_code == 201, response.text
    return dict(response.json())


class TestTitlesCrud:
    async def test_create_and_get(self, app_client: AsyncClient) -> None:
        created = await _create(app_client, MOVIE_PAYLOAD)
        assert created["genres"] == ["sci-fi", "thriller"]  # normalized

        response = await app_client.get(f"/v1/titles/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Inception"

    async def test_validation_error_maps_to_422(self, app_client: AsyncClient) -> None:
        bad = {**MOVIE_PAYLOAD, "release_year": 1700}
        response = await app_client.post("/v1/titles", json=bad)
        assert response.status_code == 422

    async def test_movie_with_seasons_rejected(self, app_client: AsyncClient) -> None:
        bad = {**MOVIE_PAYLOAD, "seasons": SERIES_PAYLOAD["seasons"]}
        response = await app_client.post("/v1/titles", json=bad)
        assert response.status_code == 422
        assert "movie cannot have seasons" in response.json()["detail"]

    async def test_update_and_version_bump(self, app_client: AsyncClient) -> None:
        created = await _create(app_client, MOVIE_PAYLOAD)
        response = await app_client.put(
            f"/v1/titles/{created['id']}", json={"name": "Inception (Director's Cut)"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Inception (Director's Cut)"
        assert body["version"] == created["version"] + 1

    async def test_delete_then_404(self, app_client: AsyncClient) -> None:
        created = await _create(app_client, MOVIE_PAYLOAD)
        assert (await app_client.delete(f"/v1/titles/{created['id']}")).status_code == 204
        assert (await app_client.get(f"/v1/titles/{created['id']}")).status_code == 404

    async def test_list_pagination(self, app_client: AsyncClient) -> None:
        for number in range(3):
            await _create(app_client, {**MOVIE_PAYLOAD, "name": f"Movie {number}"})
        response = await app_client.get("/v1/titles", params={"offset": 1, "limit": 2})
        body = response.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2


class TestSearchApi:
    async def test_full_text_search_after_create(self, app_client: AsyncClient) -> None:
        await _create(app_client, MOVIE_PAYLOAD)
        await _create(app_client, SERIES_PAYLOAD)

        response = await app_client.get("/v1/search/titles", params={"q": "dream thief"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        assert body["hits"][0]["name"] == "Inception"

    async def test_filters(self, app_client: AsyncClient) -> None:
        await _create(app_client, MOVIE_PAYLOAD)
        await _create(app_client, SERIES_PAYLOAD)

        response = await app_client.get(
            "/v1/search/titles",
            params={"genre": ["mystery"], "type": "series", "year_from": 2015},
        )
        body = response.json()
        assert [hit["name"] for hit in body["hits"]] == ["Dark"]

    async def test_deleted_title_leaves_search(self, app_client: AsyncClient) -> None:
        created = await _create(app_client, MOVIE_PAYLOAD)
        await app_client.delete(f"/v1/titles/{created['id']}")
        response = await app_client.get("/v1/search/titles", params={"q": "Inception"})
        assert response.json()["total"] == 0


class TestWatchlistApi:
    async def test_add_get_remove_flow(self, app_client: AsyncClient) -> None:
        created = await _create(app_client, MOVIE_PAYLOAD)
        user = f"user-{uuid.uuid4().hex[:6]}"

        put_response = await app_client.put(f"/v1/users/{user}/watchlist/{created['id']}")
        assert put_response.json() == {"changed": True}
        # idempotent second PUT
        assert (await app_client.put(f"/v1/users/{user}/watchlist/{created['id']}")).json() == {
            "changed": False
        }

        get_response = await app_client.get(f"/v1/users/{user}/watchlist")
        body = get_response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["title"]["name"] == "Inception"

        delete_response = await app_client.delete(f"/v1/users/{user}/watchlist/{created['id']}")
        assert delete_response.json() == {"changed": True}
        assert (await app_client.get(f"/v1/users/{user}/watchlist")).json()["items"] == []

    async def test_adding_unknown_title_is_404(self, app_client: AsyncClient) -> None:
        response = await app_client.put(
            f"/v1/users/user-1/watchlist/{uuid.uuid4()}",
        )
        assert response.status_code == 404


class TestAdminAndHealth:
    async def test_reindex_restores_search(self, app_client: AsyncClient) -> None:
        await _create(app_client, MOVIE_PAYLOAD)
        await _create(app_client, SERIES_PAYLOAD)

        response = await app_client.post("/v1/admin/reindex")
        assert response.status_code == 200
        assert response.json()["indexed"] == 2

        search = await app_client.get("/v1/search/titles")
        assert search.json()["total"] == 2

    async def test_health_endpoints(self, app_client: AsyncClient) -> None:
        assert (await app_client.get("/health/live")).json() == {"status": "ok"}
        ready = await app_client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json() == {"mongodb": "ok", "elasticsearch": "ok"}
