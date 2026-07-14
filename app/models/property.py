"""Pydantic models for property submissions."""

from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class YesNo(str, Enum):
    yes = "Yes"
    no = "No"


class PropertyStatus(str, Enum):
    pending = "Pending"
    under_review = "Under Review"
    approved = "Approved"
    rejected = "Rejected"


class PropertySubmissionForm(BaseModel):
    """
    Mirrors the multipart form fields sent by the frontend.
    Used for validation before we touch Drive/Sheets/email.
    """
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=30)
    property_address: str = Field(..., min_length=1, max_length=500)
    bedrooms: int = Field(..., ge=0, le=50)
    guests: int = Field(..., ge=0, le=100)
    features: str = Field(default="", max_length=2000)
    smoking_allowed: YesNo
    pets_allowed: YesNo


class PropertySubmissionResponse(BaseModel):
    property_id: str
    status: PropertyStatus
    drive_folder_link: str | None = None
    message: str = "Property submitted successfully."