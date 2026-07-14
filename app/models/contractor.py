"""Pydantic models for the contractor form-ID system."""

from pydantic import BaseModel, Field


class ContractorSubmission(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    contractor_id: str = Field(..., min_length=1, max_length=100)
    property_id: str = Field(..., min_length=1, max_length=50)


class ContractorSubmissionResponse(BaseModel):
    id: str
    message: str = "Thank you — your contractor ID has been submitted."
