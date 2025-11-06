




#new Code 

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from app.tasks import process_receipt
from dotenv import load_dotenv
import uvicorn
import requests
import os
import json
import logging
from typing import Dict, Any

# ------------------- Setup -------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://127.0.0.1:8000")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
os.makedirs(INCOMING_DIR, exist_ok=True)

WHATSAPP_API_VERSION = "v20.0"
WHATSAPP_GRAPH_URL = "https://graph.facebook.com"

app = FastAPI()

# Serve files (local + cloud)
app.mount("/files", StaticFiles(directory=INCOMING_DIR), name="files")


# ------------------- Routes -------------------

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/webhook")
async def verify(request: Request):
    """WhatsApp webhook verification"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


async def download_and_save_image(media_id: str, timestamp: str) -> Dict[str, Any]:
    """Download and save image from WhatsApp API"""
    try:
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        media_info_url = f"{WHATSAPP_GRAPH_URL}/{WHATSAPP_API_VERSION}/{media_id}"
        media_info = requests.get(media_info_url, headers=headers).json()

        download_url = media_info["url"]
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()

        filename = f"{INCOMING_DIR}/{timestamp}_{media_id}.jpg"
        with open(filename, "wb") as f:
            f.write(response.content)

        logger.info(f"✅ Image saved successfully: {filename}")
        return {"filename": filename, "size": len(response.content)}

    except Exception as e:
        logger.error(f"❌ Failed to download image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download image")


@app.post("/webhook")
async def webhook_receiver(request: Request):
    """Handle image receipt webhook (from listener or WhatsApp directly)"""
    try:
        data = await request.json()
        logger.info(f"Received webhook: {json.dumps(data, indent=2)}")

        # Check if image is sent as Base64
        if "image_base64" in data:
            image_filename = data.get("image_filename", "unnamed.jpg")
            local_path = os.path.join(INCOMING_DIR, image_filename)

            # Decode and save the image
            import base64
            image_bytes = base64.b64decode(data["image_base64"])
            with open(local_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"✅ Image saved from Base64: {local_path}")

        elif "local_image_path" in data:
            # Fallback (not recommended on Render)
            local_path = data["local_image_path"]
            if not os.path.exists(local_path):
                raise HTTPException(status_code=404, detail="Image file not found")
        else:
            raise HTTPException(status_code=400, detail="No image data provided")

        # Build metadata
        file_stats = os.stat(local_path)
        metadata = {
            "group_name": data.get("group_name", "Unknown Group"),
            "message_id": data.get("message_id", "N/A"),
            "sender": data.get("sender_jid"),
            "timestamp": file_stats.st_ctime,
            "file_size": file_stats.st_size,
            "sent_at": data.get("sent_at"),
            "image_url": f"{PUBLIC_URL}/files/{os.path.basename(local_path)}"
        }

        logger.info(f"Metadata: {metadata}")

        # Queue OCR processing
        process_receipt.delay(local_path, metadata)
        logger.info(f"📤 Queued OCR task for {local_path}")

        return JSONResponse(content={
            "status": "success",
            "message": "Image processed successfully",
            "filename": local_path
        })

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# @app.post("/webhook")
# async def webhook_receiver(request: Request):
#     """Handle image receipt webhook (from listener or WhatsApp directly)"""
#     try:
#         data = await request.json()
#         logger.info(f"Received webhook: {json.dumps(data, indent=2)}")

#         local_image_path = data["local_image_path"]
#         sender = data["sender_jid"]
#         # app.mount("/files", StaticFiles(directory="/app/incoming"), name="files")
#         if not os.path.exists(local_image_path):
#             raise HTTPException(status_code=404, detail="Image file not found")

#         file_stats = os.stat(local_image_path)
#         image_filename = data.get("image_filename")
#         image_url = f"{PUBLIC_URL}/files/{image_filename}" if image_filename else None

#         metadata = {
#             "group_name": data.get("group_name", "Unknown Group"),
#             "message_id": data.get("message_id", "N/A"),
#             "sender": sender,
#             "timestamp": file_stats.st_ctime,
#             "file_size": file_stats.st_size,
#             "sent_at": data.get("sent_at"),
#             "image_url": image_url
#         }

#         logger.info(f"Metadata: {metadata}")

#         process_receipt.delay(local_image_path, metadata)
#         logger.info(f"📤 Queued OCR task for {local_image_path}")

#         return JSONResponse(content={
#             "status": "success",
#             "message": "Image processed successfully",
#             "filename": local_image_path
#         })

#     except KeyError as e:
#         raise HTTPException(status_code=400, detail=f"Missing key: {str(e)}")
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")


# if __name__ == "__main__":
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
