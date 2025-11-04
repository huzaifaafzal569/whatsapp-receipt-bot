import logging
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials():
    # Load credentials from environment variable
    google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if not google_creds_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")
    
    service_account_info = json.loads(google_creds_json)
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return creds


def write_row(spreadsheet_id: str, row_values: List[str], sheet_range: str = 'Processed!A1'):
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    body = {'values': [row_values]}
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()

    logger.info(f'Appended row to sheet: {result.get("updates", {})}')
    return result
