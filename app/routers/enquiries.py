"""Property-seeker enquiry endpoint."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models.enquiry import EnquirySubmission, EnquirySubmissionResponse
from app.services import sheets_service

logger = logging.getLogger("kairoco.enquiries")

router = APIRouter(prefix="/api/enquiries", tags=["enquiries"])


@router.post("/submit", response_model=EnquirySubmissionResponse)
async def submit_enquiry(payload: EnquirySubmission):
    try:
        enquiry_id = await run_in_threadpool(sheets_service.generate_next_enquiry_id)
    except Exception as exc:
        logger.exception("Failed to generate enquiry ID")
        raise HTTPException(status_code=502, detail="Couldn't save your enquiry. Please try again.") from exc

    try:
        await run_in_threadpool(
            sheets_service.append_enquiry_row,
            enquiry_id=enquiry_id,
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            budget=payload.budget,
            bedrooms_wanted=payload.bedrooms_wanted,
            area=payload.area,
        )
    except Exception as exc:
        logger.exception("Failed to store enquiry %s", enquiry_id)
        raise HTTPException(status_code=502, detail="Couldn't save your enquiry. Please try again.") from exc

    return EnquirySubmissionResponse(id=enquiry_id)
