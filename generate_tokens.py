import os
import json
import io
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.oauth2.credentials
import logging

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a local .env file
load_dotenv()

# --- Configuration (Read from .env) ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# The SCOPES list should be the same as what your application uses (e.g., in tasks.py)
# If you don't have a SCOPES variable in your .env, define it here:
# SCOPES = os.getenv("GOOGLE_SCOPES", "https://www.googleapis.com/auth/drive").split(',') 
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

if not CLIENT_ID or not CLIENT_SECRET:
    logger.error("❌ GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in .env file.")
    exit(1)

# --- Construct Credentials Data in Memory ---
# We create a dictionary that mimics the structure of a Google client_secret.json 
# for an "installed" (desktop) application.
client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        # The following URIs are standard for desktop/CLI/local server flows
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}

logger.info(f"Using Client ID: {CLIENT_ID}")
logger.info(f"Requested Scopes: {', '.join(SCOPES)}")


def generate_new_token():
    """Generates a new refresh token by starting a local server flow."""
    # Use StringIO to read the in-memory client_config dictionary as if it were a file
    client_config_file = io.StringIO(json.dumps(client_config))

    # Initialize the flow from the in-memory config
    flow = InstalledAppFlow.from_client_config(
        client_config=client_config,
        scopes=SCOPES
    )

    # Run the local server flow to handle the OAuth dance
    # port=0 means the OS picks a free port
    # access_type='offline' is CRUCIAL to get a permanent refresh token
    # prompt='consent' forces the consent screen, ensuring a new token is issued
    credentials = flow.run_local_server(
        port=0,
        access_type='offline',
        prompt='consent'
    )

    # Convert the credentials object to a JSON string
    creds_json = credentials.to_json()
    creds_data = json.loads(creds_json)

    print("\n" + "="*50)
    print("      ✅ NEW CREDENTIALS GENERATED SUCCESSFULLY      ")
    print("="*50)
    print("  ⭐ COPY THIS REFRESH TOKEN TO YOUR RENDER SECRET  ")
    print("="*50)
    
    # Print the specific refresh token
    refresh_token = creds_data.get('refresh_token', 'ERROR: Refresh token not found!')
    print(f"REFRESH_TOKEN: {refresh_token}")
    print("="*50)
    print("\nFull Credentials JSON:")
    print(json.dumps(creds_data, indent=2))
    print("--------------------------------------------------")

    # Save to a file for backup
    with open('new_token.json', 'w') as f:
        json.dump(creds_data, f, indent=2)

    logger.info("\n✅ Refresh token successfully generated.")
    logger.info("   The full credentials file has been saved to 'new_token.json'.")
    logger.info("   Now, copy the REFRESH_TOKEN value above and update your Render environment variable.")


if __name__ == '__main__':
    generate_new_token()