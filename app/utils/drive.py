# import logging
# import os
# import json
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
# from typing import Optional

# logger = logging.getLogger(__name__)

# SCOPES = ['https://www.googleapis.com/auth/drive']

# def get_drive_service():
#     """Load credentials from environment variable instead of a file."""
#     google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
#     if not google_creds_json:
#         raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")

#     service_account_info = json.loads(google_creds_json)
#     creds = service_account.Credentials.from_service_account_info(
#         service_account_info, scopes=SCOPES
#     )
#     return build('drive', 'v3', credentials=creds, cache_discovery=False)


# def upload_file_and_get_link(local_path: str, dest_name: Optional[str] = None) -> str:
#     """
#     Upload a local file to Google Drive and return a shareable link.
#     Sets permission to 'anyone with the link can view'.
#     """
#     service = get_drive_service()
#     file_metadata = {
#     'name': dest_name or os.path.basename(local_path),
#     'parents': ['1K9QHRll3PibvO6oHEnJj9Dhcv8jsS1qv']
# }
#     media = MediaFileUpload(local_path, resumable=True)

#     created = service.files().create(
#         body=file_metadata,
#         media_body=media,
#         fields='id, webViewLink'
#     ).execute()

#     file_id = created.get('id')

#     # Make file accessible by anyone with link
#     service.permissions().create(
#         fileId=file_id,
#         body={'role': 'reader', 'type': 'anyone'}
#     ).execute()

#     file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
#     link = file_info.get('webViewLink')

#     logger.info(f'Uploaded file to Drive: {link}')
#     return link



import os
import logging
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# The scope for uploading files to your own Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Only allows access to files created by the app

# Environment variables expected:
# GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN, GOOGLE_REFRESH_TOKEN, DRIVE_FOLDER_ID (optional)

def get_drive_service():
    """Create Google Drive service using personal OAuth credentials."""
    token_info = {
        "token": os.getenv("GOOGLE_TOKEN"),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "token_uri": "https://oauth2.googleapis.com/token"
    }

    if not all(token_info.values()):
        raise ValueError("Missing one or more OAuth credentials in environment variables")

    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return service

def upload_file_and_get_link(local_path: str, dest_name: Optional[str] = None) -> str:
    """
    Upload a local file to the client's personal Google Drive and return a shareable link.
    If DRIVE_FOLDER_ID is set, upload to that folder; otherwise, upload to root.
    """
    service = get_drive_service()
    file_metadata = {'name': dest_name or os.path.basename(local_path)}

    folder_id = os.getenv("DRIVE_FOLDER_ID")
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(local_path, resumable=True)

    try:
        created_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        file_id = created_file.get('id')

        # Make file accessible by anyone with the link
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()

        file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
        link = file_info.get('webViewLink')
        logger.info(f"Uploaded file to Drive: {link}")
        return link

    except Exception as e:
        logger.error(f"Failed to upload file to Drive: {e}")
        return ""
