"""
Google Drive integration.
 
For each property submission:
  1. Create a folder named after the Property ID inside the configured
     parent "Property Photos" folder.
  2. Upload every submitted image into that folder.
  3. Grant "anyone with the link can view" so Kairo Co staff can open the
     folder link stored in Google Sheets without needing their own Drive
     permissions configured per-file.
  4. Return the folder's webViewLink.
"""
import io
from typing import Any
 
from googleapiclient.http import MediaIoBaseUpload
 
from app.config import get_settings
from app.services.google_auth import get_drive_service
 
 
def create_property_folder(property_id: str) -> str:
    """Creates a folder named e.g. 'KC-00047' under the Drive parent folder. Returns the new folder's ID."""
    settings = get_settings()
    drive: Any = get_drive_service()
 
    file_metadata = {
        "name": property_id,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [settings.GOOGLE_DRIVE_PARENT_FOLDER_ID],
    }
    folder = drive.files().create(body=file_metadata, fields="id").execute()
    return folder["id"]
 
 
def upload_image_to_folder(folder_id: str, filename: str, content: bytes, mime_type: str) -> str:
    """Uploads a single image into the given folder. Returns the new file's ID."""
    drive: Any = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    file_metadata = {"name": filename, "parents": [folder_id]}
    uploaded = drive.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return uploaded["id"]
 
 
def make_folder_shareable(folder_id: str) -> str:
    """Grants anyone-with-the-link read access and returns the folder's webViewLink."""
    drive: Any = get_drive_service()
    drive.permissions().create(
        fileId=folder_id,
        body={"role": "reader", "type": "anyone"},
        fields="id",
    ).execute()

    folder = drive.files().get(fileId=folder_id, fields="webViewLink").execute()
    return folder["webViewLink"]
 
 
def create_folder_and_upload_images(property_id: str, images: list[tuple[str, bytes, str]]) -> str:
    """
    Full helper used by the properties router:
      images: list of (filename, content_bytes, mime_type)
    Returns the shareable Drive folder link.
    """
    folder_id = create_property_folder(property_id)
    for filename, content, mime_type in images:
        upload_image_to_folder(folder_id, filename, content, mime_type)
    return make_folder_shareable(folder_id)