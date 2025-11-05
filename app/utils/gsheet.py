# import logging
# import os
# import json
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from typing import List

# logger = logging.getLogger(__name__)

# SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# def get_credentials():
#     # Load credentials from environment variable
#     google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
#     if not google_creds_json:
#         raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")
    
#     service_account_info = json.loads(google_creds_json)
#     creds = service_account.Credentials.from_service_account_info(
#         service_account_info, scopes=SCOPES
#     )
#     return creds


# def write_row(spreadsheet_id: str, row_values: List[str], sheet_range: str = "botnogal!A1"):
#     creds = get_credentials()
#     service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

#     body = {'values': [row_values]}
#     result = service.spreadsheets().values().append(
#         spreadsheetId=spreadsheet_id,
#         range=sheet_range,
#         valueInputOption='USER_ENTERED',
#         body=body
#     ).execute()

#     logger.info(f'Appended row to sheet: {result.get("updates", {})}')
#     return result


import logging
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials():
    google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if not google_creds_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")
    
    service_account_info = json.loads(google_creds_json)
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return creds


def write_row(spreadsheet_id: str, row_values: List[str], sheet_range: str = "botnogal!A2"):
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    sheet_name = sheet_range.split("!")[0]

    # Define headers according to your data order
    headers = [
        "Receipt_Date", "Amount", "Sender_Name", "Sender_CUIT",
        "Receiver_CUIT", "Transaction_Number", "Destination_Bank",
        "WhatsApp_Group", "Receipt_Sent_Time", "Image_Link"
    ]

    # Check if headers already exist in the first row
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:J1"
    ).execute()

    values = result.get('values', [])
    if not values:  # If first row is empty, write headers
        header_body = {'values': [headers]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption='USER_ENTERED',
            body=header_body
        ).execute()
        logger.info("✅ Headers added to Google Sheet.")

    # Now append the actual row starting from A2
    body = {'values': [row_values]}
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A2",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

    logger.info(f"✅ Row appended to Google Sheet: {result.get('updates', {})}")
    return result
