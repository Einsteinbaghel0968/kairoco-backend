"""
Kairo Co backend — FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload

Run in production (e.g. Hostinger VPS) with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
(see README.md for a systemd + nginx example)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import contractors, enquiries, properties, testimonials
from app.services.sheets_service import (
    CONTRACTORS_HEADER,
    ENQUIRIES_HEADER,
    PROPERTIES_HEADER,
    TESTIMONIALS_HEADER,
    ensure_header,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kairoco")

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Kairo Co property submissions and testimonials.",
    version="1.0.0",
)

# CORS is restricted to the configured frontend origin(s) only — see FRONTEND_ORIGINS in .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(testimonials.router)
app.include_router(contractors.router)
app.include_router(enquiries.router)


@app.on_event("startup")
def on_startup() -> None:
    """Make sure both Google Sheets have their header row — safe/idempotent."""
    try:
        ensure_header(settings.GOOGLE_SHEET_PROPERTIES_ID, settings.PROPERTIES_SHEET_NAME, PROPERTIES_HEADER)
        ensure_header(settings.GOOGLE_SHEET_TESTIMONIALS_ID, settings.TESTIMONIALS_SHEET_NAME, TESTIMONIALS_HEADER)
        ensure_header(settings.GOOGLE_SHEET_CONTRACTORS_ID, settings.CONTRACTORS_SHEET_NAME, CONTRACTORS_HEADER)
        ensure_header(settings.GOOGLE_SHEET_ENQUIRIES_ID, settings.ENQUIRIES_SHEET_NAME, ENQUIRIES_HEADER)
        logger.info("Google Sheets headers verified.")
    except Exception:
        logger.exception(
            "Could not verify Google Sheet headers on startup — check "
            "GOOGLE_SERVICE_ACCOUNT_FILE and sheet sharing permissions."
        )


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}