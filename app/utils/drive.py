
# app/utils/drive.py

import os
import logging
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# The scope for uploading files to your own Drive
SCOPES = ['https://www.googleapis.com/auth/drive']  # Only allows access to files created by the app

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

def get_or_create_folder(service, parent_folder_id: str, folder_name: str) -> str:
    """
    Get the folder ID for a given folder name under the parent folder.
    If it doesn't exist, create it.
    """
    query = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{folder_name}' and '{parent_folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
        logger.info(f"✅ Folder already exists: {folder_name} ({folder_id})")
        return folder_id

    # Folder not found, create it
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    folder_id = folder.get("id")
    logger.info(f"✅ Created new folder: {folder_name} ({folder_id})")
    return folder_id

def upload_file_and_get_link(local_path: str, dest_name: Optional[str] = None, supplier_folder: Optional[str] = None) -> str:
    """
    Upload a local file to Google Drive.
    - supplier_folder: name of supplier folder; creates if not exist.
    Returns shareable link.
    """
    service = get_drive_service()
    parent_folder_id = os.getenv("DRIVE_FOLDER_ID")  # Root parent folder
    folder_id = parent_folder_id

    if supplier_folder:
        folder_id = get_or_create_folder(service, parent_folder_id, supplier_folder)

    file_metadata = {'name': dest_name or os.path.basename(local_path)}
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

        link = created_file.get('webViewLink')
        logger.info(f"Uploaded file to Drive: {link}")
        return link

    except Exception as e:
        logger.error(f"Failed to upload file to Drive: {e}")
        return ""



# def upload_file_and_get_link(local_path: str, dest_name: Optional[str] = None) -> str:
#     """
#     Upload a local file to the client's personal Google Drive and return a shareable link.
#     If DRIVE_FOLDER_ID is set, upload to that folder; otherwise, upload to root.
#     """
#     service = get_drive_service()
#     file_metadata = {'name': dest_name or os.path.basename(local_path)}

#     folder_id = os.getenv("DRIVE_FOLDER_ID")
#     if folder_id:
#         file_metadata['parents'] = [folder_id]

#     media = MediaFileUpload(local_path, resumable=True)

#     try:
#         created_file = service.files().create(
#             body=file_metadata,
#             media_body=media,
#             fields='id, webViewLink'
#         ).execute()
#         file_id = created_file.get('id')

#         # Make file accessible by anyone with the link
#         service.permissions().create(
#             fileId=file_id,
#             body={'role': 'reader', 'type': 'anyone'}
#         ).execute()

#         file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
#         link = file_info.get('webViewLink')
#         logger.info(f"Uploaded file to Drive: {link}")
#         return link

#     except Exception as e:
#         logger.error(f"Failed to upload file to Drive: {e}")
#         return ""
