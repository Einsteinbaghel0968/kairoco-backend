"""
Google Sheets integration.

Handles:
  - Ensuring header rows exist
  - Generating unique IDs (Property IDs / testimonial IDs)
  - Appending new submission rows
  - Reading testimonials and filtering for Status == "Approved"

All calls here are synchronous (the underlying googleapiclient is
synchronous) — routers are responsible for running these in a threadpool
via `fastapi.concurrency.run_in_threadpool` so the event loop isn't blocked.

--------------------------------------------------------------------------
CONCURRENCY NOTE (fixed 2026-07):
Property IDs used to be "row count + 1", generated in one call and then
written in a later call (Drive photo upload happens in between). Two
submissions landing in that gap could compute the same row count and get
the same Property ID — duplicate IDs in the sheet.

Fix: ID generation no longer depends on row count at all (timestamp +
random suffix, generated instantly, no lock needed across the gap). The
row's sequence number ("S.No." column, cosmetic only) is computed AND
written inside a single locked append call, so there's no time gap where
it can go stale. This also means the fix holds even across multiple
gunicorn worker processes for the ID itself; the S.No. counter is still
per-process (see note on get_lock below) but is purely cosmetic, so a
rare skipped/duplicate S.No. under multi-worker load is not a data
integrity problem the way a duplicate Property ID was.
--------------------------------------------------------------------------
"""

import random
import string
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.services.google_auth import get_sheets_service
from app.utils.id_generator import get_lock

MAX_PHOTO_COLUMNS = 6

PROPERTIES_HEADER = [
    "S.No.", "Property ID", "Submission Date", "Status", "Full Name", "Email",
    "Phone", "Property Address", "Bedrooms", "Guests", "Features",
    "Smoking Allowed", "Pets Allowed",
] + [f"Photo {i}" for i in range(1, MAX_PHOTO_COLUMNS + 1)]

TESTIMONIALS_HEADER = ["ID", "Date", "Name", "Company", "Message", "Status"]

CONTRACTORS_HEADER = ["S.No.", "Date", "Full Name", "Contractor ID", "Property ID"]

ENQUIRIES_HEADER = ["ID", "Date", "Full Name", "Phone", "Email", "Budget", "Bedrooms Wanted", "Area"]


def _values(sheet_id: str, range_: str) -> list[list[Any]]:
    service: Any = get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])


def _append(sheet_id: str, range_: str, row: list[Any]) -> None:
    service: Any = get_sheets_service()
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def ensure_header(sheet_id: str, sheet_name: str, header: list[str]) -> None:
    """Writes the header row if the sheet is currently empty. Safe to call every startup."""
    existing = _values(sheet_id, f"{sheet_name}!A1:Z1")
    if not existing:
        service: Any = get_sheets_service()
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [header]},
        ).execute()


def _next_sequence_number_locked(sheet_id: str, sheet_name: str) -> int:
    """
    Next row number = number of existing data rows (excluding header) + 1.
    Caller MUST already hold the relevant lock, and MUST call this
    immediately before the corresponding _append — no gap in between —
    or the count can go stale. Cosmetic counter only; never use this
    value as a uniqueness guarantee for an ID.
    """
    rows = _values(sheet_id, f"{sheet_name}!A2:A")
    return len(rows) + 1


def _new_public_id(prefix: str) -> str:
    """
    Timestamp + random suffix. Generated instantly, no sheet read, no lock
    needed — safe to call at any point in a request (e.g. before a slow
    Drive upload) without risking a collision with a concurrent request.
    """
    stamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{stamp}-{suffix}"


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def generate_next_property_id() -> str:
    """
    Call this as early as you like (e.g. before the Drive photo upload) —
    it's collision-safe on its own, no lock, no sheet read.
    """
    return _new_public_id("PROP")


def append_property_row(
    *,
    property_id: str,
    full_name: str,
    email: str,
    phone: str,
    property_address: str,
    bedrooms: int,
    guests: int,
    features: str,
    smoking_allowed: str,
    pets_allowed: str,
    photo_urls: list[str],
) -> int:
    """
    Computes the row's S.No. and appends in one locked step. Returns the
    S.No. assigned (cosmetic — do not use it as a durable identifier;
    use property_id for that).

    Each photo URL becomes its own cell, written as a Sheets HYPERLINK()
    formula so it displays as a short clickable "img1", "img2", ... label
    instead of the raw URL. Only the first MAX_PHOTO_COLUMNS photos get a
    column; extras beyond that are silently dropped (design limit, not a
    bug) — raise MAX_PHOTO_COLUMNS in this file if you need more.
    """
    settings = get_settings()
    lock = get_lock("properties")
    with lock:
        seq = _next_sequence_number_locked(
            settings.GOOGLE_SHEET_PROPERTIES_ID, settings.PROPERTIES_SHEET_NAME
        )

        photo_cells = []
        for i in range(MAX_PHOTO_COLUMNS):
            if i < len(photo_urls):
                url = photo_urls[i].replace('"', '""')  # escape quotes for the formula
                photo_cells.append(f'=HYPERLINK("{url}","img{i + 1}")')
            else:
                photo_cells.append("")

        row = [
            seq,
            property_id,
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "Pending",
            full_name,
            email,
            phone,
            property_address,
            bedrooms,
            guests,
            features,
            smoking_allowed,
            pets_allowed,
        ] + photo_cells
        _append(settings.GOOGLE_SHEET_PROPERTIES_ID, f"{settings.PROPERTIES_SHEET_NAME}!A:S", row)
        return seq


# ---------------------------------------------------------------------------
# Testimonials
# ---------------------------------------------------------------------------

def generate_next_testimonial_id() -> str:
    """Collision-safe, no lock, no sheet read — same reasoning as property IDs."""
    return _new_public_id("TST")


def append_testimonial_row(*, testimonial_id: str, name: str, company: str, message: str) -> None:
    settings = get_settings()
    row = [
        testimonial_id,
        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        name,
        company,
        message,
        "Pending",
    ]
    _append(settings.GOOGLE_SHEET_TESTIMONIALS_ID, f"{settings.TESTIMONIALS_SHEET_NAME}!A:F", row)


def get_approved_testimonials() -> list[dict[str, str]]:
    """
    Reads the testimonials sheet fresh on every call and returns only rows
    where Status == "Approved". Because there's no caching, flipping the
    Status cell in Google Sheets (Pending/Rejected <-> Approved) takes effect
    the next time the frontend fetches this endpoint — no redeploy needed.
    """
    settings = get_settings()
    rows = _values(settings.GOOGLE_SHEET_TESTIMONIALS_ID, f"{settings.TESTIMONIALS_SHEET_NAME}!A2:F")

    approved = []
    for row in rows:
        # Pad short rows so missing trailing columns don't raise IndexError.
        padded = row + [""] * (len(TESTIMONIALS_HEADER) - len(row))
        _id, date, name, company, message, status = padded[:6]
        if status.strip().lower() == "approved":
            approved.append({"name": name, "company": company, "message": message, "date": date})
    return approved


# ---------------------------------------------------------------------------
# Contractors
# ---------------------------------------------------------------------------

def property_id_exists(property_id: str) -> bool:
    """Checks column B (Property ID) of the Properties sheet for a match."""
    settings = get_settings()
    rows = _values(settings.GOOGLE_SHEET_PROPERTIES_ID, f"{settings.PROPERTIES_SHEET_NAME}!B2:B")
    existing_ids = {row[0].strip().upper() for row in rows if row}
    return property_id.strip().upper() in existing_ids


def append_contractor_row(*, full_name: str, contractor_id: str, property_id: str) -> str:
    """Already atomic (seq computed + appended inside one locked block) — unchanged."""
    settings = get_settings()
    lock = get_lock("contractors")
    with lock:
        seq = _next_sequence_number_locked(
            settings.GOOGLE_SHEET_CONTRACTORS_ID, settings.CONTRACTORS_SHEET_NAME
        )
        row = [
            seq,
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            full_name,
            contractor_id,
            property_id,
        ]
        _append(settings.GOOGLE_SHEET_CONTRACTORS_ID, f"{settings.CONTRACTORS_SHEET_NAME}!A:E", row)
        return str(seq)


# ---------------------------------------------------------------------------
# Enquiries (property seekers)
# ---------------------------------------------------------------------------

def generate_next_enquiry_id() -> str:
    """Collision-safe, no lock, no sheet read — same reasoning as property IDs."""
    return _new_public_id("ENQ")


def append_enquiry_row(
    *,
    enquiry_id: str,
    full_name: str,
    phone: str,
    email: str,
    budget: str,
    bedrooms_wanted: int,
    area: str,
) -> None:
    settings = get_settings()
    row = [
        enquiry_id,
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        full_name,
        phone,
        email,
        budget,
        bedrooms_wanted,
        area,
    ]
    _append(settings.GOOGLE_SHEET_ENQUIRIES_ID, f"{settings.ENQUIRIES_SHEET_NAME}!A:H", row)