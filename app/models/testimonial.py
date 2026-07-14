"""Pydantic models for the testimonial system."""

from enum import Enum
from pydantic import BaseModel, Field


class TestimonialStatus(str, Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"


class TestimonialSubmission(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)


class TestimonialSubmissionResponse(BaseModel):
    id: str
    status: TestimonialStatus
    message: str = "Thank you — your testimonial has been submitted for review."


class PublicTestimonial(BaseModel):
    """What the website is allowed to see — Approved entries only, no admin metadata."""
    name: str
    company: str = ""
    message: str
    date: str
