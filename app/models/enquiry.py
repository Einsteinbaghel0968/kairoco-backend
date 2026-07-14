"""Pydantic models for property-seeker enquiries."""

from pydantic import BaseModel, EmailStr, Field


class EnquirySubmission(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=30)
    email: EmailStr
    budget: str = Field(..., min_length=1, max_length=100)
    bedrooms_wanted: int = Field(..., ge=0, le=50)
    area: str = Field(..., min_length=1, max_length=200)


class EnquirySubmissionResponse(BaseModel):
    id: str
    message: str = "Thank you — we'll be in touch about properties matching your needs."
