"""
Shared Google API authentication.

Single service account, single key file, used for both Sheets and Drive.
"""

from functools import lru_cache

from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource

from app.config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@lru_cache
def get_service_account_credentials() -> service_account.Credentials:
    settings = get_settings()
    return service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )


@lru_cache
def get_sheets_service() -> Resource:
    return build("sheets", "v4", credentials=get_service_account_credentials(), cache_discovery=False)


@lru_cache
def get_drive_service() -> Resource:
    return build("drive", "v3", credentials=get_service_account_credentials(), cache_discovery=False)