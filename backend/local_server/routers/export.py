"""Export router for Local Development Server.

Handles POST /api/export (generate and save file locally) and
GET /exports/{filename} (serve generated file). File generators are
adapted from ``lambdas/export_service/handler.py`` without any S3 or
boto3 dependency — files are saved directly to
``backend/local_server/exports/{uuid}.{ext}`` and served as static files.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
"""

from __future__ import annotations

import csv
import io
import pathlib
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from shared.models import ActiveFilter, ExportRequest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_FORMATS: frozenset[str] = frozenset({"pdf", "excel", "csv"})

_FORMAT_EXT: dict[str, str] = {
    "pdf": "pdf",
    "excel": "xlsx",
    "csv": "csv",
}

# Absolute path to the exports directory (sibling of this file's package root)
_EXPORTS_DIR: pathlib.Path = (
    pathlib.Path(__file__).parent.parent / "exports"
)


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

    The CSV contains a metadata comment block at the top (Req 8.7), followed
    by a header row and placeholder data rows that would normally be populated
    from the data source in a full implementation.

    Args:
        request: Parsed export request containing filter metadata.

    Returns:
        UTF-8-encoded CSV bytes.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)

    filter_summary = _filter_summary(request.filters)

    # Metadata comment block (Req 8.7) — #source, #period, #filters
    buf.write(f"# source: {request.page}\n")
    buf.write(
        f"# period: {request.time_range_start} to {request.time_range_end}\n"
    )
    buf.write(f"# filters: {filter_summary}\n")

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

    # Placeholder row — in production this would be real data rows
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
    - ``Metadata``: active filters, time range, and source page (Req 8.2).
    - ``Data``: campaign data columns with placeholder rows.

    Args:
        request: Parsed export request containing filter metadata.

    Returns:
        Raw bytes of the .xlsx workbook.

    Raises:
        ImportError: When openpyxl is not installed.
    """
    try:
        from openpyxl import Workbook  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "Export format 'excel' requires openpyxl. "
            "Run: pip install openpyxl>=3.1.2"
        )

    wb = Workbook()

    # ------------------------------------------------------------------
    # Metadata sheet (Req 8.2)
    # ------------------------------------------------------------------
    ws_meta = wb.active
    ws_meta.title = "Metadata"
    ws_meta.append(["Source Page", request.page])
    ws_meta.append(["Time Range Start", request.time_range_start])
    ws_meta.append(["Time Range End", request.time_range_end])
    ws_meta.append([])  # blank separator row
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
    # Placeholder row — in production populated from real data source
    ws_data.append(
        ["N/A (MVP placeholder)", "N/A", "N/A", "N/A", "N/A", 0, 0, "0.00%"]
    )

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generate_pdf(request: ExportRequest) -> bytes:
    """Generate a PDF export using reportlab.

    Produces a structured document with a title, metadata table (active
    filters, time range, source page — Req 8.2), and a placeholder data
    section.

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
        raise ImportError(
            "Export format 'pdf' requires reportlab. "
            "Run: pip install reportlab>=4.2.0"
        )

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
        [
            "Time Range",
            f"{request.time_range_start} \u2014 {request.time_range_end}",
        ],
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
            "Note: Data rows would be populated from the real data source "
            "in production. This MVP export demonstrates the export mechanism "
            "with metadata.",
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
# Dispatch helper
# ---------------------------------------------------------------------------


def _generate_file(request: ExportRequest) -> bytes:
    """Dispatch to the appropriate file generator for the requested format.

    Args:
        request: Parsed export request.

    Returns:
        Raw file bytes for the requested format.

    Raises:
        ValueError: When the format is not one of ``pdf``, ``excel``,
            ``csv``.
        ImportError: When a required optional dependency (openpyxl,
            reportlab) is not installed.
    """
    if request.format == "csv":
        return _generate_csv(request)
    if request.format == "excel":
        return _generate_excel(request)
    if request.format == "pdf":
        return _generate_pdf(request)
    raise ValueError(f"Unsupported export format: {request.format!r}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---------------------------------------------------------------------------
# 6.2  POST /api/export
# ---------------------------------------------------------------------------


@router.post("/api/export")
async def export_data(request: Request) -> JSONResponse:
    """Generate an export file and return a local download URL.

    Parses the JSON request body manually because ``ExportRequest`` is a
    plain dataclass (not a Pydantic model).

    Request body fields:
        page (str): Identifier of the page/view being exported.
        format (str): Output format — ``"csv"``, ``"excel"``, or ``"pdf"``.
        filters (list): Active filter objects with ``field`` and ``values``.
        time_range_start (str): Start of the exported time range (yyyy-mm-dd).
        time_range_end (str): End of the exported time range (yyyy-mm-dd).

    Returns:
        200 ``{"status": "completed", "download_url": "/exports/{filename}"}``
        400 if body is missing, invalid JSON, missing required fields, or
            format is not one of ``csv``, ``excel``, ``pdf``.
        500 if the file cannot be written to disk.

    Requirements: 8.1-8.6
    """
    # ------------------------------------------------------------------
    # Parse request body
    # ------------------------------------------------------------------

    # Check Content-Length / body presence
    body_bytes = await request.body()
    if not body_bytes or not body_bytes.strip():
        raise HTTPException(status_code=400, detail="Request body is required.")

    try:
        raw: dict = await request.json()
    except Exception:  # noqa: BLE001 — covers all JSON decode errors
        raise HTTPException(
            status_code=400,
            detail="Request body must be valid JSON.",
        )

    if not isinstance(raw, dict) or not raw:
        raise HTTPException(status_code=400, detail="Request body is required.")

    # ------------------------------------------------------------------
    # Validate required fields
    # ------------------------------------------------------------------

    page: str | None = raw.get("page")
    if not page or not str(page).strip():
        raise HTTPException(
            status_code=400,
            detail="Field 'page' is required and must be non-empty.",
        )

    fmt: str | None = raw.get("format")
    if not fmt or not str(fmt).strip():
        raise HTTPException(
            status_code=400,
            detail="Field 'format' is required and must be non-empty.",
        )
    fmt = str(fmt).strip()

    # Validate format value
    if fmt not in _VALID_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported export format '{fmt}'. "
                f"Must be one of: {', '.join(sorted(_VALID_FORMATS))}"
            ),
        )

    time_range_start: str | None = raw.get("time_range_start")
    if not time_range_start or not str(time_range_start).strip():
        raise HTTPException(
            status_code=400,
            detail="Field 'time_range_start' is required and must be non-empty.",
        )

    time_range_end: str | None = raw.get("time_range_end")
    if not time_range_end or not str(time_range_end).strip():
        raise HTTPException(
            status_code=400,
            detail="Field 'time_range_end' is required and must be non-empty.",
        )

    # Parse filters list (may be empty list — that is valid)
    raw_filters = raw.get("filters", [])
    if not isinstance(raw_filters, list):
        raise HTTPException(
            status_code=400,
            detail="Field 'filters' must be a JSON array.",
        )

    filters: list[ActiveFilter] = []
    for item in raw_filters:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=400,
                detail="Each item in 'filters' must be a JSON object with 'field' and 'values'.",
            )
        field_name = item.get("field", "")
        values = item.get("values", [])
        if not isinstance(values, list):
            values = [values]
        filters.append(ActiveFilter(field=str(field_name), values=[str(v) for v in values]))

    # ------------------------------------------------------------------
    # Build ExportRequest dataclass
    # ------------------------------------------------------------------

    export_request = ExportRequest(
        page=str(page).strip(),
        format=fmt,  # type: ignore[arg-type]
        filters=filters,
        time_range_start=str(time_range_start).strip(),
        time_range_end=str(time_range_end).strip(),
    )

    # ------------------------------------------------------------------
    # Generate file bytes
    # ------------------------------------------------------------------

    file_bytes = _generate_file(export_request)

    # ------------------------------------------------------------------
    # Persist file to exports directory
    # ------------------------------------------------------------------

    ext = _FORMAT_EXT[fmt]
    filename = f"{uuid.uuid4()}.{ext}"

    try:
        _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        target_path: pathlib.Path = _EXPORTS_DIR / filename
        target_path.write_bytes(file_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write export file: {exc}",
        ) from exc

    # ------------------------------------------------------------------
    # Return response
    # ------------------------------------------------------------------

    return JSONResponse(
        status_code=200,
        content={
            "status": "completed",
            "download_url": f"/exports/{filename}",
        },
    )


# ---------------------------------------------------------------------------
# 6.3  GET /exports/{filename}
# ---------------------------------------------------------------------------


@router.get("/exports/{filename}", include_in_schema=False)
async def serve_export(filename: str) -> FileResponse:
    """Serve a previously generated export file.

    Path parameter:
        filename: Name of the file inside the exports directory.

    Returns:
        FileResponse with the file contents.
        404 if the file does not exist.

    Requirements: 8.4
    """
    file_path: pathlib.Path = _EXPORTS_DIR / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Export file not found",
        )

    return FileResponse(path=str(file_path), filename=filename)
