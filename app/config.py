"""
Central application configuration.

All secrets and environment-specific values are loaded from a `.env` file
(see `.env.example`) via pydantic-settings. Nothing here is hard-coded, and
nothing here is ever sent to the frontend.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    APP_NAME: str = "Kairo Co Backend"
    ENVIRONMENT: str = "development"  # development | production

    # --- CORS ---
    # Comma-separated list in .env, e.g. "https://kairoco.co.uk,https://www.kairoco.co.uk"
    FRONTEND_ORIGINS: str = "http://localhost:5173"

    # --- Google API ---
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "service_account.json"
    GOOGLE_DRIVE_PARENT_FOLDER_ID: str  # "Property Photos" root folder in Drive
    GOOGLE_SHEET_PROPERTIES_ID: str     # Spreadsheet ID for property submissions
    GOOGLE_SHEET_TESTIMONIALS_ID: str   # Spreadsheet ID for testimonials
    GOOGLE_SHEET_CONTRACTORS_ID: str    # Spreadsheet ID for contractor form-ID submissions
    GOOGLE_SHEET_ENQUIRIES_ID: str      # Spreadsheet ID for property-seeker enquiries

    # --- Cloudinary (property photos) ---
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    PROPERTIES_SHEET_NAME: str = "Properties"
    TESTIMONIALS_SHEET_NAME: str = "Testimonials"
    CONTRACTORS_SHEET_NAME: str = "Contractors"
    ENQUIRIES_SHEET_NAME: str = "Enquiries"

    # --- Email (Gmail SMTP) ---
    GMAIL_ADDRESS: str
    GMAIL_APP_PASSWORD: str
    ADMIN_EMAIL: str = "admin@kairoco.co.uk"

    # --- Uploads ---
    MAX_UPLOAD_MB: int = 10
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/webp"

    @property
    def frontend_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_image_types_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_IMAGE_TYPES.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the .env file is only parsed once per process."""
    return Settings()