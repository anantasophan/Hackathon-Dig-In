"""Export Service Lambda handler.

Handles POST /api/campaigns/export — generates PDF, Excel, or CSV export
files containing active filter metadata and placeholder data, uploads the
file to S3, and returns a presigned download URL valid for 15 minutes.

NOTE (MVP): ExportRequest contains filter metadata only, NOT actual data rows.
The actual data would normally be fetched from Athena at export time. For MVP
this handler demonstrates the full export mechanism (format generation, S3
upload, presigned URL) with filter/metadata content in the export file.
The actual Athena data fetch is intentionally deferred to a post-MVP iteration.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
import uuid
from dataclasses import asdict
from typing import Any

import boto3
from botocore.exceptions import ClientError

from shared.models import ActiveFilter, ExportRequest, ExportResponse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TIMEOUT_SECONDS: float = 30.0
_PRESIGNED_URL_TTL_SECONDS: int = 900  # 15 minutes
_DEFAULT_EXPORT_BUCKET: str = "campaign-exports"

_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}

_VALID_FORMATS: frozenset[str] = frozenset({"pdf", "excel", "csv"})

_FORMAT_EXT: dict[str, str] = {
    "pdf": "pdf",
    "excel": "xlsx",
    "csv": "csv",
}

_FORMAT_CONTENT_TYPE: dict[str, str] = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _ok(body: dict[str, Any]) -> dict[str, Any]:
    """Return a 200 Lambda proxy response with *body* serialised as JSON.

    Args:
        body: Dict to serialise into the response body.

    Returns:
        API Gateway Lambda proxy response dict.
    """
    return {
        "statusCode": 200,
        "headers": _HEADERS,
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> dict[str, Any]:
    """Return an error Lambda proxy response.

    Args:
        status_code: HTTP status code (e.g. 400, 408, 500).
        message: Human-readable error description.

    Returns:
        API Gateway Lambda proxy response dict.
    """
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps({"message": message}),
    }


# ---------------------------------------------------------------------------
# Filter summary helper
# ---------------------------------------------------------------------------


def _filter_summary(filters: list[ActiveFilter]) -> str:
    """Build a compact human-readable filter summary string.

    Args:
        filters: List of active filters applied to the export.

    Returns:
        Semicolon-separated string of ``field=value1,value2`` pairs,
        or ``"none"`` when the filter list is empty.
    """
    if not filters:
        return "none"
    parts: list[str] = []
    for f in filters:
        values_str = ",".join(str(v) for v in f.values)
        parts.append(f"{f.field}={values_str}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# File generators
# ---------------------------------------------------------------------------


def _generate_csv(request: ExportRequest) -> bytes:
    """Generate a CSV export from the request metadata.

    The CSV contains a metadata comment block at the top, followed by a
    header row and placeholder data rows that would normally be populated
    from Athena in a full implementation.

    Args:
        request: Parsed export request containing filter metadata.

    Returns:
        UTF-8-encoded CSV bytes.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)

    filter_summary = _filter_summary(request.filters)

    # Metadata comment block (Req 8.2)
    buf.write(
        f"# Source: {request.page}, "
        f"Period: {request.time_range_start} to {request.time_range_end}, "
        f"Filters: {filter_summary}\n"
    )

    # Header row
    writer.writerow(
        [
            "nama_program",
            "flag_program",
            "media_blasting",
            "jenis_leads",
            "wilayah",
            "total_leads",
            "total_take_up",
            "take_up_rate",
        ]
    )

    # Placeholder row — in production this would be Athena result rows
    writer.writerow(
        [
            "N/A (MVP placeholder)",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            0,
            0,
            "0.00%",
        ]
    )

    return buf.getvalue().encode("utf-8")


def _generate_excel(request: ExportRequest) -> bytes:
    """Generate an Excel (.xlsx) export using openpyxl.

    Creates two sheets:
    - ``Metadata``: active filters, time range, and source page.
    - ``Data``: campaign data columns with placeholder rows.

    Args:
        request: Parsed export request containing filter metadata.

    Returns:
        Raw bytes of the .xlsx workbook.

    Raises:
        ImportError: When openpyxl is not installed.
    """
    try:
        import openpyxl  # noqa: PLC0415
        from openpyxl import Workbook  # noqa: PLC0415
    except ImportError:
        raise ImportError("Export format requires additional dependencies")

    wb = Workbook()

    # ------------------------------------------------------------------
    # Metadata sheet (Req 8.2)
    # ------------------------------------------------------------------
    ws_meta = wb.active
    ws_meta.title = "Metadata"
    ws_meta.append(["Source Page", request.page])
    ws_meta.append(["Time Range Start", request.time_range_start])
    ws_meta.append(["Time Range End", request.time_range_end])
    ws_meta.append([])  # blank row
    ws_meta.append(["Active Filters"])
    ws_meta.append(["Field", "Values"])
    for f in request.filters:
        ws_meta.append([f.field, ", ".join(str(v) for v in f.values)])

    # ------------------------------------------------------------------
    # Data sheet
    # ------------------------------------------------------------------
    ws_data = wb.create_sheet("Data")
    headers = [
        "nama_program",
        "flag_program",
        "media_blasting",
        "jenis_leads",
        "wilayah",
        "total_leads",
        "total_take_up",
        "take_up_rate",
    ]
    ws_data.append(headers)
    # Placeholder row — in production populated from Athena
    ws_data.append(
        ["N/A (MVP placeholder)", "N/A", "N/A", "N/A", "N/A", 0, 0, "0.00%"]
    )

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generate_pdf(request: ExportRequest) -> bytes:
    """Generate a PDF export using reportlab.

    Produces a structured document with a title, metadata table (active
    filters, time range, source page), and a placeholder data section.

    Args:
        request: Parsed export request containing filter metadata.

    Returns:
        Raw PDF bytes.

    Raises:
        ImportError: When reportlab is not installed.
    """
    try:
        from reportlab.lib import colors  # noqa: PLC0415
        from reportlab.lib.pagesizes import A4  # noqa: PLC0415
        from reportlab.lib.styles import getSampleStyleSheet  # noqa: PLC0415
        from reportlab.lib.units import cm  # noqa: PLC0415
        from reportlab.platypus import (  # noqa: PLC0415
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise ImportError("Export format requires additional dependencies")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Campaign Insight Export", styles["Title"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Metadata section (Req 8.2)
    elements.append(Paragraph("Export Metadata", styles["Heading2"]))
    meta_data = [
        ["Source Page", request.page],
        ["Time Range", f"{request.time_range_start} — {request.time_range_end}"],
        ["Active Filters", _filter_summary(request.filters)],
    ]
    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("WORDWRAP", (1, 0), (1, -1), True),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Data section header
    elements.append(Paragraph("Campaign Data", styles["Heading2"]))
    elements.append(
        Paragraph(
            "Note: Data rows would be populated from Athena in production. "
            "This MVP export demonstrates the export mechanism with metadata.",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    # Data table with placeholder row
    data_headers = [
        "Campaign",
        "Program",
        "Channel",
        "Leads",
        "Take Up",
        "Rate",
    ]
    data_rows = [
        data_headers,
        ["N/A (MVP placeholder)", "N/A", "N/A", "0", "0", "0.00%"],
    ]
    data_table = Table(data_rows)
    data_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(data_table)

    doc.build(elements)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _generate_file(request: ExportRequest) -> bytes:
    """Dispatch to the appropriate file generator for the requested format.

    Args:
        request: Parsed export request.

    Returns:
        Raw file bytes for the requested format.

    Raises:
        ValueError: When the format is not one of ``pdf``, ``excel``, ``csv``.
        ImportError: When a required optional dependency is not installed.
    """
    if request.format == "csv":
        return _generate_csv(request)
    if request.format == "excel":
        return _generate_excel(request)
    if request.format == "pdf":
        return _generate_pdf(request)
    raise ValueError(f"Unsupported export format: {request.format!r}")


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for Export Service endpoint.

    ``POST /api/campaigns/export``

    Expected body::

        {
            "page": "campaign_overview",
            "format": "pdf" | "excel" | "csv",
            "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
            "time_range_start": "2024-01-01",
            "time_range_end": "2024-03-31"
        }

    Flow:
    1. Parse and validate JSON body → ExportRequest (400 on error).
    2. Start 30-second timeout timer (Req 8.4).
    3. Generate file bytes in the requested format.
    4. Check elapsed time; return 408 if > 30 s.
    5. Upload file to S3 and generate a 15-minute presigned URL.
    6. On any failure: cleanup partial S3 object, return 500 (Req 8.5).

    Args:
        event: API Gateway Lambda proxy event dict.
        context: Lambda context object (unused).

    Returns:
        API Gateway Lambda proxy response dict with HTTP status and JSON body.
        Possible status codes:

        - ``200`` – success; body contains ``download_url``.
        - ``400`` – missing/invalid request body or unsupported format.
        - ``408`` – export timed out (> 30 s) (Req 8.4).
        - ``500`` – generation or S3 upload failed (Req 8.5).
    """
    # ------------------------------------------------------------------
    # 1. Parse JSON body → ExportRequest
    # ------------------------------------------------------------------
    raw_body = event.get("body")
    if not raw_body:
        return _error(400, "Request body is required.")

    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        return _error(400, "Request body must be valid JSON.")

    try:
        filters_raw: list[dict[str, Any]] = payload.get("filters", [])
        filters = [
            ActiveFilter(field=f["field"], values=f.get("values", []))
            for f in filters_raw
        ]
        request = ExportRequest(
            page=str(payload["page"]),
            format=payload["format"],
            filters=filters,
            time_range_start=str(payload["time_range_start"]),
            time_range_end=str(payload["time_range_end"]),
        )
    except (KeyError, TypeError) as exc:
        return _error(400, f"Invalid request body: missing or malformed field — {exc}")

    # ------------------------------------------------------------------
    # 2. Validate format
    # ------------------------------------------------------------------
    if request.format not in _VALID_FORMATS:
        return _error(
            400,
            f"Unsupported export format {request.format!r}. "
            f"Must be one of: {', '.join(sorted(_VALID_FORMATS))}.",
        )

    # ------------------------------------------------------------------
    # 3. Start timeout timer (Req 8.4)
    # ------------------------------------------------------------------
    start_time: float = time.monotonic()

    def _elapsed() -> float:
        return time.monotonic() - start_time

    def _timed_out() -> bool:
        return _elapsed() > _TIMEOUT_SECONDS

    # ------------------------------------------------------------------
    # 4. Generate file content
    # ------------------------------------------------------------------
    try:
        file_bytes = _generate_file(request)
    except ImportError as exc:
        return _error(500, str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Export generation failed: {exc}")

    # ------------------------------------------------------------------
    # 5. Timeout check after generation (Req 8.4)
    # ------------------------------------------------------------------
    if _timed_out():
        response_obj = ExportResponse(
            status="timeout",
            error_message=(
                f"Export timed out after {_TIMEOUT_SECONDS:.0f} seconds. "
                "Please retry or reduce the scope of the export."
            ),
        )
        return {
            "statusCode": 408,
            "headers": _HEADERS,
            "body": json.dumps(asdict(response_obj)),
        }

    # ------------------------------------------------------------------
    # 6. Upload to S3 and generate presigned URL (Req 8.1, 8.3)
    # ------------------------------------------------------------------
    bucket = os.environ.get("EXPORT_BUCKET", _DEFAULT_EXPORT_BUCKET)
    ext = _FORMAT_EXT[request.format]
    s3_key = f"{uuid.uuid4()}.{ext}"
    content_type = _FORMAT_CONTENT_TYPE[request.format]

    s3 = boto3.client("s3")

    try:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
        )
    except ClientError as exc:
        # No partial object to clean up — put_object is atomic; return 500.
        return _error(500, f"S3 upload failed: {exc.response['Error']['Message']}")
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"S3 upload failed: {exc}")

    # Timeout check after upload
    if _timed_out():
        # Clean up the uploaded object since we cannot deliver it in time
        try:
            s3.delete_object(Bucket=bucket, Key=s3_key)
        except Exception:  # noqa: BLE001
            pass  # Best-effort cleanup; do not mask the timeout error
        response_obj = ExportResponse(
            status="timeout",
            error_message=(
                f"Export timed out after {_TIMEOUT_SECONDS:.0f} seconds. "
                "Please retry or reduce the scope of the export."
            ),
        )
        return {
            "statusCode": 408,
            "headers": _HEADERS,
            "body": json.dumps(asdict(response_obj)),
        }

    # Generate presigned URL valid for 15 minutes (900 s) (Req 8.3)
    try:
        presigned_url: str = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=_PRESIGNED_URL_TTL_SECONDS,
        )
    except ClientError as exc:
        # Upload succeeded but presigned URL generation failed; clean up.
        try:
            s3.delete_object(Bucket=bucket, Key=s3_key)
        except Exception:  # noqa: BLE001
            pass  # noqa: BLE001 — best-effort cleanup
        return _error(
            500,
            f"Failed to generate presigned URL: {exc.response['Error']['Message']}",
        )
    except Exception as exc:  # noqa: BLE001
        try:
            s3.delete_object(Bucket=bucket, Key=s3_key)
        except Exception:  # noqa: BLE001
            pass  # noqa: BLE001 — best-effort cleanup
        return _error(500, f"Failed to generate presigned URL: {exc}")

    # ------------------------------------------------------------------
    # 7. Return success response (Req 8.3)
    # ------------------------------------------------------------------
    response_obj = ExportResponse(
        status="completed",
        download_url=presigned_url,
    )
    return _ok(asdict(response_obj))
