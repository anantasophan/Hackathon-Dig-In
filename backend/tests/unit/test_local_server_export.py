"""Unit tests for backend/local_server/routers/export.py using FastAPI TestClient.

Tests the two export endpoints:
  - POST /api/export   — generate CSV/Excel/PDF file and return download URL
  - GET  /exports/{filename} — serve previously-generated export file

Test coverage:
  - POST with format csv/excel/pdf → 200, status "completed"          (Req 8.1-8.3)
  - POST download_url matches pattern /exports/{filename}.{ext}       (Req 8.4)
  - POST with invalid format → 400                                     (Req 8.5)
  - POST with empty/missing body → 400                                 (Req 8.6)
  - POST CSV metadata comment block in generated file                  (Req 8.7)
  - GET  /exports/{filename} after POST → 200 file response            (Req 8.4)
  - GET  /exports/nonexistent_file_12345.csv → 404                     (Req 8.4)

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from local_server.main import app


# ---------------------------------------------------------------------------
# Module-scoped TestClient
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a module-scoped TestClient wrapping the full FastAPI app.

    Module-scope so the ASGI lifespan (startup event) runs once per
    test module, keeping tests fast.

    Yields:
        A configured :class:`~fastapi.testclient.TestClient` instance.
    """
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared valid request body
# ---------------------------------------------------------------------------

_VALID_BODY: dict = {
    "page": "campaign_overview",
    "format": "csv",
    "filters": [],
    "time_range_start": "2024-08-01",
    "time_range_end": "2024-08-31",
}

# Pattern: /exports/{uuid}.{ext}
_DOWNLOAD_URL_PATTERN = re.compile(
    r"^/exports/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(csv|xlsx|pdf)$"
)


# ===========================================================================
# POST /api/export — format csv  (Requirements 8.1, 8.4, 8.7)
# ===========================================================================


class TestPostExportCsv:
    """POST /api/export with format=csv."""

    def test_csv_returns_200(self, client: TestClient) -> None:
        """Requirement 8.1: POST with format=csv returns HTTP 200."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": "csv"})
        assert response.status_code == 200

    def test_csv_status_completed(self, client: TestClient) -> None:
        """Requirement 8.1: response body contains status='completed'."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "csv"}).json()
        assert body.get("status") == "completed"

    def test_csv_download_url_present(self, client: TestClient) -> None:
        """Requirement 8.4: response body contains a download_url field."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "csv"}).json()
        assert "download_url" in body

    def test_csv_download_url_pattern(self, client: TestClient) -> None:
        """Requirement 8.4: download_url matches /exports/{uuid}.csv."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "csv"}).json()
        url = body["download_url"]
        assert _DOWNLOAD_URL_PATTERN.match(url), f"URL did not match pattern: {url!r}"
        assert url.endswith(".csv")

    def test_csv_response_has_exactly_two_keys(self, client: TestClient) -> None:
        """Response body has exactly 'status' and 'download_url' keys."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "csv"}).json()
        assert set(body.keys()) == {"status", "download_url"}

    def test_csv_file_contains_metadata_comment(self, client: TestClient) -> None:
        """Requirement 8.7: generated CSV file starts with # metadata comment lines."""
        body = client.post(
            "/api/export",
            json={**_VALID_BODY, "format": "csv", "page": "campaign_overview"},
        ).json()
        download_url = body["download_url"]
        # Fetch the generated file
        file_response = client.get(download_url)
        assert file_response.status_code == 200
        content = file_response.content.decode("utf-8")
        # Must start with # comment lines
        assert content.startswith("#"), "CSV must begin with # metadata comments"
        lines = content.splitlines()
        comment_lines = [ln for ln in lines if ln.startswith("#")]
        assert len(comment_lines) >= 3, "CSV metadata block must have at least 3 # lines"

    def test_csv_metadata_contains_source(self, client: TestClient) -> None:
        """Requirement 8.7: CSV metadata includes '# source:' line."""
        body = client.post(
            "/api/export",
            json={**_VALID_BODY, "format": "csv", "page": "campaign_overview"},
        ).json()
        file_response = client.get(body["download_url"])
        content = file_response.content.decode("utf-8")
        assert "# source:" in content

    def test_csv_metadata_contains_period(self, client: TestClient) -> None:
        """Requirement 8.7: CSV metadata includes '# period:' line with date range."""
        body = client.post(
            "/api/export",
            json={
                **_VALID_BODY,
                "format": "csv",
                "time_range_start": "2024-08-01",
                "time_range_end": "2024-08-31",
            },
        ).json()
        file_response = client.get(body["download_url"])
        content = file_response.content.decode("utf-8")
        assert "# period:" in content
        assert "2024-08-01" in content
        assert "2024-08-31" in content

    def test_csv_metadata_contains_filters(self, client: TestClient) -> None:
        """Requirement 8.7: CSV metadata includes '# filters:' line."""
        body = client.post(
            "/api/export",
            json={**_VALID_BODY, "format": "csv"},
        ).json()
        file_response = client.get(body["download_url"])
        content = file_response.content.decode("utf-8")
        assert "# filters:" in content

    def test_csv_with_filters_reflected_in_metadata(self, client: TestClient) -> None:
        """Requirement 8.7: active filters appear in CSV metadata comment block."""
        body = client.post(
            "/api/export",
            json={
                **_VALID_BODY,
                "format": "csv",
                "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
            },
        ).json()
        file_response = client.get(body["download_url"])
        content = file_response.content.decode("utf-8")
        assert "flag_program" in content


# ===========================================================================
# POST /api/export — format excel  (Requirement 8.2)
# ===========================================================================


class TestPostExportExcel:
    """POST /api/export with format=excel."""

    def test_excel_returns_200(self, client: TestClient) -> None:
        """Requirement 8.2: POST with format=excel returns HTTP 200."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": "excel"})
        assert response.status_code == 200

    def test_excel_status_completed(self, client: TestClient) -> None:
        """Requirement 8.2: response body contains status='completed'."""
        body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "excel"}
        ).json()
        assert body.get("status") == "completed"

    def test_excel_download_url_present(self, client: TestClient) -> None:
        """Requirement 8.4: response body contains a download_url."""
        body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "excel"}
        ).json()
        assert "download_url" in body

    def test_excel_download_url_ends_with_xlsx(self, client: TestClient) -> None:
        """Requirement 8.4: download_url for excel format ends with .xlsx."""
        body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "excel"}
        ).json()
        assert body["download_url"].endswith(".xlsx")

    def test_excel_download_url_pattern(self, client: TestClient) -> None:
        """Requirement 8.4: download_url matches /exports/{uuid}.xlsx."""
        body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "excel"}
        ).json()
        url = body["download_url"]
        assert _DOWNLOAD_URL_PATTERN.match(url), f"URL did not match pattern: {url!r}"


# ===========================================================================
# POST /api/export — format pdf  (Requirement 8.3)
# ===========================================================================


class TestPostExportPdf:
    """POST /api/export with format=pdf."""

    def test_pdf_returns_200(self, client: TestClient) -> None:
        """Requirement 8.3: POST with format=pdf returns HTTP 200."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": "pdf"})
        assert response.status_code == 200

    def test_pdf_status_completed(self, client: TestClient) -> None:
        """Requirement 8.3: response body contains status='completed'."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "pdf"}).json()
        assert body.get("status") == "completed"

    def test_pdf_download_url_present(self, client: TestClient) -> None:
        """Requirement 8.4: response body contains a download_url."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "pdf"}).json()
        assert "download_url" in body

    def test_pdf_download_url_ends_with_pdf(self, client: TestClient) -> None:
        """Requirement 8.4: download_url for pdf format ends with .pdf."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "pdf"}).json()
        assert body["download_url"].endswith(".pdf")

    def test_pdf_download_url_pattern(self, client: TestClient) -> None:
        """Requirement 8.4: download_url matches /exports/{uuid}.pdf."""
        body = client.post("/api/export", json={**_VALID_BODY, "format": "pdf"}).json()
        url = body["download_url"]
        assert _DOWNLOAD_URL_PATTERN.match(url), f"URL did not match pattern: {url!r}"


# ===========================================================================
# POST /api/export — invalid format → 400  (Requirement 8.5)
# ===========================================================================


class TestPostExportInvalidFormat:
    """POST /api/export with an unsupported format value → HTTP 400."""

    def test_format_docx_returns_400(self, client: TestClient) -> None:
        """Requirement 8.5: format='docx' (unsupported) returns HTTP 400."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": "docx"})
        assert response.status_code == 400

    def test_format_txt_returns_400(self, client: TestClient) -> None:
        """Requirement 8.5: format='txt' returns HTTP 400."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": "txt"})
        assert response.status_code == 400

    def test_format_json_returns_400(self, client: TestClient) -> None:
        """Requirement 8.5: format='json' returns HTTP 400."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": "json"})
        assert response.status_code == 400

    def test_format_empty_string_returns_400(self, client: TestClient) -> None:
        """Requirement 8.5: format='' (empty string) returns HTTP 400."""
        response = client.post("/api/export", json={**_VALID_BODY, "format": ""})
        assert response.status_code == 400

    def test_invalid_format_body_has_detail(self, client: TestClient) -> None:
        """Requirement 8.5: 400 response for invalid format contains a detail field."""
        body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "docx"}
        ).json()
        assert "detail" in body

    def test_invalid_format_detail_mentions_format(self, client: TestClient) -> None:
        """Requirement 8.5: error detail mentions the invalid format value."""
        body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "docx"}
        ).json()
        assert "docx" in body["detail"].lower() or "format" in body["detail"].lower()


# ===========================================================================
# POST /api/export — empty / missing body → 400  (Requirement 8.6)
# ===========================================================================


class TestPostExportEmptyBody:
    """POST /api/export with empty or missing body → HTTP 400."""

    def test_empty_body_bytes_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: completely empty body returns HTTP 400."""
        response = client.post(
            "/api/export",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_whitespace_only_body_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: body with only whitespace returns HTTP 400."""
        response = client.post(
            "/api/export",
            content=b"   ",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_empty_json_object_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: empty JSON object {} returns HTTP 400."""
        response = client.post("/api/export", json={})
        assert response.status_code == 400

    def test_missing_format_field_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: body missing 'format' field returns HTTP 400."""
        body = {
            "page": "campaign_overview",
            "filters": [],
            "time_range_start": "2024-08-01",
            "time_range_end": "2024-08-31",
        }
        response = client.post("/api/export", json=body)
        assert response.status_code == 400

    def test_missing_page_field_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: body missing 'page' field returns HTTP 400."""
        body = {
            "format": "csv",
            "filters": [],
            "time_range_start": "2024-08-01",
            "time_range_end": "2024-08-31",
        }
        response = client.post("/api/export", json=body)
        assert response.status_code == 400

    def test_missing_time_range_start_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: body missing 'time_range_start' returns HTTP 400."""
        body = {
            "page": "campaign_overview",
            "format": "csv",
            "filters": [],
            "time_range_end": "2024-08-31",
        }
        response = client.post("/api/export", json=body)
        assert response.status_code == 400

    def test_missing_time_range_end_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: body missing 'time_range_end' returns HTTP 400."""
        body = {
            "page": "campaign_overview",
            "format": "csv",
            "filters": [],
            "time_range_start": "2024-08-01",
        }
        response = client.post("/api/export", json=body)
        assert response.status_code == 400

    def test_invalid_json_body_returns_400(self, client: TestClient) -> None:
        """Requirement 8.6: malformed (non-JSON) body returns HTTP 400."""
        response = client.post(
            "/api/export",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_empty_body_has_detail(self, client: TestClient) -> None:
        """Requirement 8.6: 400 for empty body contains a detail field."""
        response = client.post(
            "/api/export",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert "detail" in response.json()


# ===========================================================================
# GET /exports/{filename} — serve file  (Requirement 8.4)
# ===========================================================================


class TestGetExportFile:
    """GET /exports/{filename} serves the generated export file."""

    def test_get_csv_file_after_post_returns_200(self, client: TestClient) -> None:
        """Requirement 8.4: GET download_url from POST response returns HTTP 200."""
        post_body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "csv"}
        ).json()
        download_url = post_body["download_url"]
        get_response = client.get(download_url)
        assert get_response.status_code == 200

    def test_get_excel_file_after_post_returns_200(self, client: TestClient) -> None:
        """Requirement 8.4: GET of generated xlsx file returns HTTP 200."""
        post_body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "excel"}
        ).json()
        get_response = client.get(post_body["download_url"])
        assert get_response.status_code == 200

    def test_get_pdf_file_after_post_returns_200(self, client: TestClient) -> None:
        """Requirement 8.4: GET of generated pdf file returns HTTP 200."""
        post_body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "pdf"}
        ).json()
        get_response = client.get(post_body["download_url"])
        assert get_response.status_code == 200

    def test_get_csv_file_has_non_empty_content(self, client: TestClient) -> None:
        """GET of generated CSV file returns non-empty file content."""
        post_body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "csv"}
        ).json()
        get_response = client.get(post_body["download_url"])
        assert len(get_response.content) > 0

    def test_get_csv_file_content_is_text(self, client: TestClient) -> None:
        """Generated CSV file can be decoded as UTF-8 text."""
        post_body = client.post(
            "/api/export", json={**_VALID_BODY, "format": "csv"}
        ).json()
        get_response = client.get(post_body["download_url"])
        # Must decode without error
        content = get_response.content.decode("utf-8")
        assert len(content) > 0

    def test_get_nonexistent_file_returns_404(self, client: TestClient) -> None:
        """Requirement 8.4: GET /exports/nonexistent_file_12345.csv returns HTTP 404."""
        response = client.get("/exports/nonexistent_file_12345.csv")
        assert response.status_code == 404

    def test_get_nonexistent_file_has_detail(self, client: TestClient) -> None:
        """404 response for missing export file contains a detail field."""
        response = client.get("/exports/nonexistent_file_12345.csv")
        body = response.json()
        assert "detail" in body

    def test_get_nonexistent_xlsx_returns_404(self, client: TestClient) -> None:
        """GET /exports/nonexistent_file_12345.xlsx also returns HTTP 404."""
        response = client.get("/exports/nonexistent_file_12345.xlsx")
        assert response.status_code == 404

    def test_get_nonexistent_pdf_returns_404(self, client: TestClient) -> None:
        """GET /exports/nonexistent_file_12345.pdf also returns HTTP 404."""
        response = client.get("/exports/nonexistent_file_12345.pdf")
        assert response.status_code == 404


# ===========================================================================
# POST /api/export — filters list scenarios
# ===========================================================================


class TestPostExportFilters:
    """POST /api/export — variations on the filters field."""

    def test_empty_filters_list_returns_200(self, client: TestClient) -> None:
        """Filters field as empty list is valid — returns HTTP 200."""
        response = client.post(
            "/api/export", json={**_VALID_BODY, "filters": []}
        )
        assert response.status_code == 200

    def test_filters_with_one_item_returns_200(self, client: TestClient) -> None:
        """Filters with one valid ActiveFilter item returns HTTP 200."""
        response = client.post(
            "/api/export",
            json={
                **_VALID_BODY,
                "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
            },
        )
        assert response.status_code == 200

    def test_filters_not_a_list_returns_400(self, client: TestClient) -> None:
        """Filters field as non-list (string) returns HTTP 400."""
        response = client.post(
            "/api/export", json={**_VALID_BODY, "filters": "not-a-list"}
        )
        assert response.status_code == 400

    def test_missing_filters_uses_default_empty_list(self, client: TestClient) -> None:
        """Omitting 'filters' field uses default empty list — returns HTTP 200."""
        body_without_filters = {
            k: v for k, v in _VALID_BODY.items() if k != "filters"
        }
        response = client.post("/api/export", json=body_without_filters)
        # filters defaults to [] when not provided
        assert response.status_code == 200
