"""Testimonial submission + public (approved-only) listing endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models.testimonial import (
    PublicTestimonial,
    TestimonialStatus,
    TestimonialSubmission,
    TestimonialSubmissionResponse,
)
from app.services import sheets_service

logger = logging.getLogger("kairoco.testimonials")

router = APIRouter(prefix="/api/testimonials", tags=["testimonials"])


@router.post("/submit", response_model=TestimonialSubmissionResponse)
async def submit_testimonial(payload: TestimonialSubmission):
    try:
        testimonial_id = await run_in_threadpool(sheets_service.generate_next_testimonial_id)
    except Exception as exc:
        logger.exception("Failed to generate testimonial ID")
        raise HTTPException(status_code=502, detail="Couldn't save your testimonial. Please try again.") from exc

    try:
        await run_in_threadpool(
            sheets_service.append_testimonial_row,
            testimonial_id=testimonial_id,
            name=payload.full_name,
            company=payload.company,
            message=payload.message,
        )
    except Exception as exc:
        logger.exception("Failed to store testimonial %s", testimonial_id)
        raise HTTPException(status_code=502, detail="Couldn't save your testimonial. Please try again.") from exc

    return TestimonialSubmissionResponse(id=testimonial_id, status=TestimonialStatus.pending)


@router.get("", response_model=list[PublicTestimonial])
async def list_approved_testimonials():
    """
    Public endpoint used by the website's Testimonials section.

    Reads the sheet fresh on every request — flipping a row's Status between
    Pending/Approved/Rejected in Google Sheets takes effect on the very next
    call, with no caching, redeploy, or webhook required.
    """
    try:
        rows = await run_in_threadpool(sheets_service.get_approved_testimonials)
    except Exception as exc:
        logger.exception("Failed to read testimonials sheet")
        raise HTTPException(
            status_code=502,
            detail="Couldn't load testimonials right now. Please try again shortly.",
        ) from exc
    return [PublicTestimonial(**row) for row in rows]
