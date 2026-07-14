"""Validation helpers for uploaded property images."""

from fastapi import HTTPException, UploadFile

from app.config import get_settings


async def validate_and_read_images(images: list[UploadFile]) -> list[tuple[str, bytes, str]]:
    """
    Validates content type and size for each uploaded image, then reads them
    into memory. Raises HTTPException(400) on the first invalid file.

    Returns a list of (filename, content_bytes, mime_type) ready for upload
    to Google Drive.
    """
    settings = get_settings()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    allowed_types = settings.allowed_image_types_list

    validated: list[tuple[str, bytes, str]] = []

    for image in images:
        if image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{image.content_type}' for '{image.filename}'. "
                       f"Allowed types: {', '.join(allowed_types)}",
            )

        content = await image.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"'{image.filename}' exceeds the {settings.MAX_UPLOAD_MB}MB size limit.",
            )

        validated.append((image.filename or "photo.jpg", content, image.content_type))

    return validated
