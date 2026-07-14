"""Contractor form-ID submission endpoint."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models.contractor import ContractorSubmission, ContractorSubmissionResponse
from app.services import sheets_service

logger = logging.getLogger("kairoco.contractors")

router = APIRouter(prefix="/api/contractors", tags=["contractors"])


@router.post("/submit", response_model=ContractorSubmissionResponse)
async def submit_contractor(payload: ContractorSubmission):
    try:
        exists = await run_in_threadpool(sheets_service.property_id_exists, payload.property_id)
    except Exception as exc:
        logger.exception("Failed to verify property ID")
        raise HTTPException(status_code=502, detail="Couldn't verify that Property ID. Please try again.") from exc

    if not exists:
        raise HTTPException(status_code=404, detail="That Property ID wasn't found. Double-check the code your client gave you.")

    try:
        row_id = await run_in_threadpool(
            sheets_service.append_contractor_row,
            full_name=payload.full_name,
            contractor_id=payload.contractor_id,
            property_id=payload.property_id,
        )
    except Exception as exc:
        logger.exception("Failed to store contractor submission")
        raise HTTPException(status_code=502, detail="Couldn't save your submission. Please try again.") from exc

    return ContractorSubmissionResponse(id=row_id)
