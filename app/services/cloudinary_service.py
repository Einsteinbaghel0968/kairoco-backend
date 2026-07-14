"""
Cloudinary integration — replaces Google Drive for property photos.

For each property submission:
  1. Upload every image to Cloudinary under folder "kairoco/{property_id}".
  2. Collect each image's secure URL.
  3. Return a comma-separated string of URLs to store in the Sheet row.
"""

import cloudinary
import cloudinary.uploader

from app.config import get_settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    _configured = True


def upload_property_images(property_id: str, images: list[tuple[str, bytes, str]]) -> list[str]:
    """
    images: list of (filename, content_bytes, mime_type)
    Returns a list of secure URLs, one per uploaded image (empty list if none).
    """
    _ensure_configured()

    urls: list[str] = []
    for filename, content, _mime_type in images:
        result = cloudinary.uploader.upload(
            content,
            folder=f"kairoco/{property_id}",
            public_id=filename.rsplit(".", 1)[0],
            overwrite=True,
        )
        urls.append(result["secure_url"])

    return urls