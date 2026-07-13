"""FastAPI application entry point for the Local Development Server.

Registers CORSMiddleware, includes campaign and export routers, defines
the health-check endpoint, prints a startup log to stdout, and overrides
the default 404 handler with a JSON response.

Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from local_server.routers import ai_recommendations, campaigns, export

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(title="Local Dev Server")

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Campaigns router: all routes defined relative to /api
app.include_router(campaigns.router, prefix="/api")

# Export router: defines /api/export (POST) and /exports/{filename} (GET)
# internally — include without an additional prefix so both paths resolve
# correctly.
app.include_router(export.router)

# AI Recommendations router: defines /api/ai/recommendations (POST)
app.include_router(ai_recommendations.router, prefix="/api")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return server liveness status.

    Returns:
        A dict with ``status`` and ``mode`` fields confirming the server
        is running in local-dev mode.

    Examples:
        GET /health → {"status": "ok", "mode": "local-dev"}
    """
    return {"status": "ok", "mode": "local-dev"}


# ---------------------------------------------------------------------------
# 404 handler — override FastAPI's default HTML response with JSON
# ---------------------------------------------------------------------------


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a JSON 404 response for any unrecognised path.

    FastAPI's built-in 404 response returns HTML.  This handler replaces
    it with a JSON body so that API clients always receive a consistent
    content type.

    Args:
        request: The incoming HTTP request (unused but required by FastAPI).
        exc: The exception that triggered this handler (unused).

    Returns:
        A ``JSONResponse`` with HTTP 404 and body ``{"detail": "Not found"}``.
    """
    return JSONResponse(status_code=404, content={"detail": "Not found"})


# ---------------------------------------------------------------------------
# Startup event — print available endpoints to stdout
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_log() -> None:
    """Print a startup banner listing all available endpoints to stdout.

    Called automatically by FastAPI/uvicorn when the ASGI lifespan starts.
    The log is written to stdout so it appears in the terminal when the
    developer runs ``uvicorn local_server.main:app --reload --port 8000``.
    """
    print("=== Local Dev Server started on http://localhost:8000 ===")
    print("Available endpoints:")
    print("  GET  /health")
    print("  GET  /api/campaigns/overview")
    print("  POST /api/campaigns/comparison")
    print("  GET  /api/campaigns/time-analysis/{campaign_id}")
    print("  GET  /api/campaigns/regional/{campaign_id}")
    print("  GET  /api/campaigns/customer-criteria/{campaign_id}")
    print("  POST /api/campaigns/similar")
    print("  POST /api/export")
    print("  GET  /exports/{filename}")
    print("  POST /api/ai/recommendations")
