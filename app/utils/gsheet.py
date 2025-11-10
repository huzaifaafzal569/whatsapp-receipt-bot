
# # # gsheet.py

# # import logging
# # import os
# # import json
# # from google.oauth2 import service_account
# # from googleapiclient.discovery import build
# # from typing import List

# # logger = logging.getLogger(__name__)

# # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# # def get_credentials():
# #     google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
# #     if not google_creds_json:
# #         raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")
    
# #     service_account_info = json.loads(google_creds_json)
# #     creds = service_account.Credentials.from_service_account_info(
# #         service_account_info, scopes=SCOPES
# #     )
# #     return creds


# # def write_row(spreadsheet_id: str, row_values: List[str], sheet_range: str = "botnogal!A2"):
# #     creds = get_credentials()
# #     service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

# #     sheet_name = sheet_range.split("!")[0]

# #     # Define headers according to your data order
# #     headers = [
# #         "Receipt_Date", "Amount", "Sender_Name", "Sender_CUIT",
# #         "Receiver_CUIT", "Transaction_Number", "Destination_Bank",
# #         "WhatsApp_Group", "Receipt_Sent_Time", "Image_Link"
# #     ]

# #     # Check if headers already exist in the first row
# #     result = service.spreadsheets().values().get(
# #         spreadsheetId=spreadsheet_id,
# #         range=f"{sheet_name}!A1:J1"
# #     ).execute()

# #     values = result.get('values', [])
# #     if not values:  # If first row is empty, write headers
# #         header_body = {'values': [headers]}
# #         service.spreadsheets().values().update(
# #             spreadsheetId=spreadsheet_id,
# #             range=f"{sheet_name}!A1",
# #             valueInputOption='USER_ENTERED',
# #             body=header_body
# #         ).execute()
# #         logger.info("✅ Headers added to Google Sheet.")

# #     # Now append the actual row starting from A2
# #     body = {'values': [row_values]}
# #     result = service.spreadsheets().values().append(
# #         spreadsheetId=spreadsheet_id,
# #         range=f"{sheet_name}!A2",
# #         valueInputOption='USER_ENTERED',
# #         insertDataOption='INSERT_ROWS',
# #         body=body
# #     ).execute()

# #     logger.info(f"✅ Row appended to Google Sheet: {result.get('updates', {})}")
# #     return result


# import logging
# import os
# import json
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from typing import List

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

# SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# def get_credentials():
#     google_creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
#     if not google_creds_json:
#         raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT environment variable")
    
#     service_account_info = json.loads(google_creds_json)
#     creds = service_account.Credentials.from_service_account_info(
#         service_account_info, scopes=SCOPES
#     )
#     return creds

# def write_row(spreadsheet_id: str, row_values: List[str], sheet_base_name: str = "botnogal", max_rows: int = 1000):
#     """
#     Append a row to a Google Sheet.
#     If the current sheet exceeds max_rows, create a new sheet with incremented index.
#     """
#     creds = get_credentials()
#     service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

#     # List all sheets
#     spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
#     sheets = spreadsheet.get("sheets", [])

#     # Find latest sheet with base name
#     index = 0
#     latest_sheet_name = sheet_base_name
#     for s in sheets:
#         title = s["properties"]["title"]
#         if title == sheet_base_name:
#             latest_sheet_name = sheet_base_name
#         elif title.startswith(f"{sheet_base_name}_"):
#             try:
#                 num = int(title.split("_")[-1])
#                 if num > index:
#                     index = num
#                     latest_sheet_name = title
#             except ValueError:
#                 continue

#     # Check number of rows
#     result = service.spreadsheets().values().get(
#         spreadsheetId=spreadsheet_id,
#         range=f"{latest_sheet_name}!A:A"
#     ).execute()
#     num_rows = len(result.get("values", []))

#     if num_rows >= max_rows:
#         # Create a new sheet with incremented index
#         index += 1
#         latest_sheet_name = f"{sheet_base_name}_{index}"
#         service.spreadsheets().batchUpdate(
#             spreadsheetId=spreadsheet_id,
#             body={"requests": [{"addSheet": {"properties": {"title": latest_sheet_name}}}]}
#         ).execute()
#         logger.info(f"✅ Created new sheet: {latest_sheet_name}")

#         # Write headers in the new sheet
#         headers = [
#             "Receipt_Date", "Amount", "Sender_CUIT",
#             "Receiver_CUIT", "Transaction_Number", "Destination_Bank",
#             "WhatsApp_Group", "Receipt_Sent_Time", "Image_Link"
#         ]
#         service.spreadsheets().values().update(
#             spreadsheetId=spreadsheet_id,
#             range=f"{latest_sheet_name}!A1",
#             valueInputOption="USER_ENTERED",
#             body={"values": [headers]}
#         ).execute()
#         logger.info(f"✅ Headers added to new sheet: {latest_sheet_name}")

#     # Append data
#     body = {"values": [row_values]}
#     result = service.spreadsheets().values().append(
#         spreadsheetId=spreadsheet_id,
#         range=f"{latest_sheet_name}!A2",
#         valueInputOption="USER_ENTERED",
#         insertDataOption="INSERT_ROWS",
#         body=body
#     ).execute()

#     logger.info(f"✅ Row appended to sheet {latest_sheet_name}: {result.get('updates', {})}")
#     return result





import logging
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

def write_row(spreadsheet_id: str, row_values: List[str], sheet_base_name: str = "botnogal", max_rows: int = 1000):
    """
    Append a row to a Google Sheet.
    If the current sheet exceeds max_rows, create a new sheet with incremented index.
    Always ensures headers exist in the first row.
    """
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    # List all sheets
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet.get("sheets", [])

    # Find latest sheet with base name
    index = 0
    latest_sheet_name = sheet_base_name
    for s in sheets:
        title = s["properties"]["title"]
        if title == sheet_base_name:
            latest_sheet_name = sheet_base_name
        elif title.startswith(f"{sheet_base_name}_"):
            try:
                num = int(title.split("_")[-1])
                if num > index:
                    index = num
                    latest_sheet_name = title
            except ValueError:
                continue

    # Headers
    headers = [
        "Receipt_Date", "Amount", "Sender_CUIT", "Transaction_Number",'Supplier', "Destination_Bank",
        "WhatsApp_Group", "Receipt_Sent_Time", "Image_Link"
    ]

    # Check if sheet is empty or missing headers
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{latest_sheet_name}!A1:Z1"
        ).execute()
        first_row = result.get("values", [])
    except Exception:
        first_row = []

    if not first_row or first_row[0] != headers:
        # Write headers
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{latest_sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [headers]}
        ).execute()
        logger.info(f"✅ Headers added to sheet: {latest_sheet_name}")

    # Check number of rows to see if new sheet is needed
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{latest_sheet_name}!A:A"
    ).execute()
    num_rows = len(result.get("values", []))

    if num_rows >= max_rows:
        # Create a new sheet with incremented index
        index += 1
        latest_sheet_name = f"{sheet_base_name}_{index}"
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": latest_sheet_name}}}]}
        ).execute()
        logger.info(f"✅ Created new sheet: {latest_sheet_name}")

        # Write headers in the new sheet
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{latest_sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [headers]}
        ).execute()
        logger.info(f"✅ Headers added to new sheet: {latest_sheet_name}")

    # Append data starting from row 2
    body = {"values": [row_values]}
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{latest_sheet_name}!A2",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

    logger.info(f"✅ Row appended to sheet {latest_sheet_name}: {result.get('updates', {})}")
    return result
