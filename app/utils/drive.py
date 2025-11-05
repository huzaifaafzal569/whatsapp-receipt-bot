import logging
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from typing import Optional

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """Load credentials from environment variable instead of a file."""
    google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if not google_creds_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")

    service_account_info = json.loads(google_creds_json)
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def upload_file_and_get_link(local_path: str, dest_name: Optional[str] = None) -> str:
    """
    Upload a local file to Google Drive and return a shareable link.
    Sets permission to 'anyone with the link can view'.
    """
    service = get_drive_service()
    file_metadata = {
    'name': dest_name or os.path.basename(local_path),
    'parents': ['1K9QHRll3PibvO6oHEnJj9Dhcv8jsS1qv']
}
    media = MediaFileUpload(local_path, resumable=True)

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    file_id = created.get('id')

    # Make file accessible by anyone with link
    service.permissions().create(
        fileId=file_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
    link = file_info.get('webViewLink')

    logger.info(f'Uploaded file to Drive: {link}')
    return link
