"""Unit tests for backend/local_server/main.py using FastAPI TestClient.

Covers:
- GET /health → 200 with correct body (Requirement 1.4)
- Unknown path → 404 JSON response (Requirement 1.5)
- CORS header present on GET /health response (Requirement 1.6)
- Preflight OPTIONS request → 200 with CORS headers (Requirement 1.7)

Requirements: 1.4, 1.5, 1.6, 1.7
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from local_server.main import app


# ---------------------------------------------------------------------------
# Shared client fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a TestClient wrapping the FastAPI app.

    Module-scope so the ASGI lifespan (startup event) runs once per
    test session.
    """
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /health — Requirement 1.4
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """GET /health must return 200 with the correct JSON body."""

    def test_status_code_is_200(self, client: TestClient) -> None:
        """Requirement 1.4: health endpoint returns HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_body_has_status_ok(self, client: TestClient) -> None:
        """Requirement 1.4: body contains ``status: "ok"``."""
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_body_has_mode_local_dev(self, client: TestClient) -> None:
        """Requirement 1.4: body contains ``mode: "local-dev"``."""
        response = client.get("/health")
        assert response.json()["mode"] == "local-dev"

    def test_body_exact_shape(self, client: TestClient) -> None:
        """Requirement 1.4: body is exactly ``{"status": "ok", "mode": "local-dev"}``."""
        response = client.get("/health")
        assert response.json() == {"status": "ok", "mode": "local-dev"}

    def test_content_type_is_json(self, client: TestClient) -> None:
        """Health endpoint must return application/json content type."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Unknown paths → 404 JSON — Requirement 1.5
# ---------------------------------------------------------------------------


class TestNotFoundHandler:
    """Requests to undefined paths must return HTTP 404 with a JSON body."""

    def test_unknown_path_returns_404(self, client: TestClient) -> None:
        """Requirement 1.5: undefined path returns HTTP 404."""
        response = client.get("/unknown-path")
        assert response.status_code == 404

    def test_unknown_path_returns_json(self, client: TestClient) -> None:
        """Requirement 1.5: 404 response body is valid JSON."""
        response = client.get("/unknown-path")
        # Should not raise
        body = response.json()
        assert isinstance(body, dict)

    def test_unknown_path_body_has_detail(self, client: TestClient) -> None:
        """Requirement 1.5: 404 JSON body contains a ``detail`` field."""
        response = client.get("/unknown-path")
        assert "detail" in response.json()

    def test_unknown_path_detail_value(self, client: TestClient) -> None:
        """Requirement 1.5: ``detail`` field value is ``"Not found"``."""
        response = client.get("/unknown-path")
        assert response.json()["detail"] == "Not found"

    def test_deeply_nested_unknown_path_returns_404(self, client: TestClient) -> None:
        """Requirement 1.5: deeply-nested undefined paths also return 404 JSON."""
        response = client.get("/api/does/not/exist")
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"

    def test_unknown_post_path_returns_404(self, client: TestClient) -> None:
        """Requirement 1.5: undefined path for POST method also returns 404 JSON."""
        response = client.post("/totally-unknown", json={})
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_404_content_type_is_json(self, client: TestClient) -> None:
        """Requirement 1.5: 404 response content type must be application/json."""
        response = client.get("/does-not-exist")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# CORS headers on GET /health — Requirement 1.6
# ---------------------------------------------------------------------------


class TestCorsHeaders:
    """CORS ``Access-Control-Allow-Origin: *`` must appear on responses."""

    def test_cors_header_present_on_health(self, client: TestClient) -> None:
        """Requirement 1.6: CORS allow-origin header is present on GET /health."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert "access-control-allow-origin" in response.headers

    def test_cors_header_value_is_wildcard(self, client: TestClient) -> None:
        """Requirement 1.6: CORS allow-origin value must be ``*``."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.headers["access-control-allow-origin"] == "*"

    def test_cors_header_present_on_404_response(self, client: TestClient) -> None:
        """Requirement 1.6: CORS header must also appear on 404 responses."""
        response = client.get(
            "/unknown-path",
            headers={"Origin": "http://localhost:3000"},
        )
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"


# ---------------------------------------------------------------------------
# Preflight OPTIONS → 200 — Requirement 1.7
# ---------------------------------------------------------------------------


class TestPreflightOptions:
    """CORS preflight OPTIONS requests must be answered with HTTP 200."""

    def test_preflight_health_returns_200(self, client: TestClient) -> None:
        """Requirement 1.7: OPTIONS preflight to /health returns 200."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200

    def test_preflight_health_has_allow_origin(self, client: TestClient) -> None:
        """Requirement 1.7: preflight response includes allow-origin header."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers

    def test_preflight_health_has_allow_methods(self, client: TestClient) -> None:
        """Requirement 1.7: preflight response includes allow-methods header."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-methods" in response.headers

    def test_preflight_api_path_returns_200(self, client: TestClient) -> None:
        """Requirement 1.7: OPTIONS preflight to /api/campaigns/overview returns 200."""
        response = client.options(
            "/api/campaigns/overview",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200

    def test_preflight_api_path_has_allow_headers(self, client: TestClient) -> None:
        """Requirement 1.7: preflight response includes allow-headers header."""
        response = client.options(
            "/api/campaigns/overview",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert "access-control-allow-headers" in response.headers

    def test_preflight_post_endpoint_returns_200(self, client: TestClient) -> None:
        """Requirement 1.7: OPTIONS preflight to a POST endpoint returns 200."""
        response = client.options(
            "/api/campaigns/comparison",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
