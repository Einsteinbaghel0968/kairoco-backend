"""Property submission endpoints."""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import EmailStr

from app.models.property import PropertySubmissionResponse, PropertyStatus, YesNo
from app.services import cloudinary_service, email_service, sheets_service
from app.utils.validators import validate_and_read_images

logger = logging.getLogger("kairoco.properties")

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.post("/submit", response_model=PropertySubmissionResponse)
async def submit_property(
    full_name: str = Form(..., min_length=1, max_length=200),
    email: EmailStr = Form(...),
    phone: str = Form(..., min_length=5, max_length=30),
    property_address: str = Form(..., min_length=1, max_length=500),
    bedrooms: int = Form(..., ge=0, le=50),
    guests: int = Form(..., ge=0, le=100),
    features: str = Form("", max_length=2000),
    smoking_allowed: YesNo = Form(...),
    pets_allowed: YesNo = Form(...),
    images: list[UploadFile] = File(default=[]),
):
    # FastAPI + Pydantic have already validated every field above (types,
    # lengths, email format, Yes/No enum) before this line runs — invalid
    # input never reaches the Drive/Sheets/email calls below.

    # 2. Validate + read uploaded images into memory.
    validated_images = await validate_and_read_images(images)

    # 3. Generate the next sequential Property ID (KC-00001, KC-00002, ...).
    try:
        property_id = await run_in_threadpool(sheets_service.generate_next_property_id)
    except Exception as exc:
        logger.exception("Failed to generate property ID")
        raise HTTPException(
            status_code=502,
            detail="We couldn't process your submission right now. Please try again shortly.",
        ) from exc
    # 4. Upload all images to Cloudinary, get back their URLs.
    try:
        photo_urls = await run_in_threadpool(
            cloudinary_service.upload_property_images, property_id, validated_images
        )
    except Exception as exc:
        logger.exception("Cloudinary upload failed for %s", property_id)
        raise HTTPException(
            status_code=502,
            detail="We couldn't upload your property photos right now. Please try again shortly.",
        ) from exc

    # 5. Save the submission as one row in the master Google Sheet (Status = Pending).
    try:
        await run_in_threadpool(
            sheets_service.append_property_row,
            property_id=property_id,
            full_name=full_name,
            email=email,
            phone=phone,
            property_address=property_address,
            bedrooms=bedrooms,
            guests=guests,
            features=features,
            smoking_allowed=smoking_allowed.value,
            pets_allowed=pets_allowed.value,
            photo_urls=photo_urls,
        )
    except Exception as exc:
        logger.exception("Sheets append failed for %s", property_id)
        raise HTTPException(
            status_code=502,
            detail="Your photos were uploaded but we couldn't save your submission. Please contact us with your reference.",
        ) from exc

    # 6. Fire off email notifications. Failures here are logged, not fatal —
    #    the submission itself already succeeded.
    await run_in_threadpool(
        email_service.send_admin_notification,
        property_id=property_id,
        full_name=full_name,
        email=email,
        phone=phone,
        property_address=property_address,
        bedrooms=bedrooms,
        guests=guests,
        features=features,
        smoking_allowed=smoking_allowed.value,
        pets_allowed=pets_allowed.value,
        drive_folder_link=", ".join(photo_urls) if photo_urls else "No photos uploaded",
    )
    await run_in_threadpool(
        email_service.send_owner_confirmation,
        owner_email=email,
        owner_name=full_name,
        property_id=property_id,
    )

    return PropertySubmissionResponse(
        property_id=property_id,
        status=PropertyStatus.pending,
        drive_folder_link=", ".join(photo_urls) if photo_urls else None,
    )