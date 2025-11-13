
# main.py

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
from datetime import datetime
import pytz

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



# @app.post("/webhook")
# async def webhook_receiver(request: Request):
#     """Handle image/PDF receipt webhook (from listener)"""
#     try:
#         data = await request.json()
#         logger.info(f"Received webhook: {json.dumps(data, indent=2)}")

#         # --- 1. Common Metadata Generation ---
#         # Generate metadata BEFORE the logic splits
#         sent_at_str = data.get("sent_at")
#         sent_at_formatted = sent_at_str # Default to raw string
        
#         # Safe time conversion logic (keeping your robust implementation)
#         if sent_at_str:
#             try:
#                 if sent_at_str.endswith("Z"):
#                     sent_at_str = sent_at_str.replace("Z", "")
                
#                 # Check for sub-second precision
#                 time_format = "%Y-%m-%dT%H:%M:%S.%f" if '.' in sent_at_str else "%Y-%m-%dT%H:%M:%S"
#                 utc_time = datetime.strptime(sent_at_str, time_format)
#                 utc_time = utc_time.replace(tzinfo=pytz.UTC)
                
#                 argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
#                 argentina_time = utc_time.astimezone(argentina_tz)
#                 sent_at_formatted = argentina_time.strftime("%Y-%m-%d %H:%M:%S")
#             except Exception as e:
#                 logger.error(f"Failed to convert sent_at: {e}")

#         # Basic metadata, including the new flags
#         metadata = {
#             "group_name": data.get("group_name", "Unknown Group"),
#             "message_id": data.get("message_id", "N/A"),
#             "sender": data.get("sender_jid"),
#             "sent_at": sent_at_formatted,
#             "skip_ocr": data.get("skip_ocr", False),  # <-- Capture the flag
#             "file_type": data.get("file_type")       # <-- Capture file type (e.g., 'PDF')
#         }

#         # --- 2. NEW LOGIC: PDF/Skip OCR Path (IMMEDIATE RETURN) ---
#         if metadata["skip_ocr"]:
#             # Send None for image_base64 (Optional[str])
#             process_receipt.delay(None, metadata) 
#             logger.info("📄 PDF received (skip_ocr=True). Queued for sheet insertion.")
            
#             return JSONResponse(content={
#                 "status": "success",
#                 "message": f"{metadata['file_type']} received and queued for sheet insertion (OCR skipped).",
#             })
        
#         # --- 3. Image OCR Path (Requires image data) ---
        
#         encoded_image = data.get("image_base64")
#         image_filename = data.get("image_filename")
        
#         if not encoded_image or not image_filename:
#             # This handles cases where skip_ocr is False but no image data is found
#             logger.error("❌ Task called without image data and skip_ocr is False.")
#             raise HTTPException(status_code=400, detail="Missing image data for OCR task.")

#         local_path = os.path.join(INCOMING_DIR, image_filename)
        
#         # Decode and save the image (only for the /files endpoint/local storage)
#         import base64
#         image_bytes = base64.b64decode(encoded_image)
#         with open(local_path, "wb") as f:
#             f.write(image_bytes)
#         logger.info(f"✅ Image saved from Base64: {local_path}")
        
#         # Update metadata for image-specific data
#         file_stats = os.stat(local_path)
#         metadata.update({
#             "timestamp": file_stats.st_ctime,
#             "file_size": file_stats.st_size,
#             "image_url": f"{PUBLIC_URL}/files/{os.path.basename(local_path)}",
#             "image_filename": os.path.basename(local_path)
#         })
        
#         logger.info(f"Metadata: {metadata}")

#         # Queue OCR processing: use the encoded_image directly from the payload (efficient)
#         process_receipt.delay(encoded_image, metadata) 
#         logger.info(f"📤 Queued OCR task for {local_path}")

#         return JSONResponse(content={
#             "status": "success",
#             "message": "Image processed successfully and queued for OCR.",
#             "filename": os.path.basename(local_path)
#         })

#     except HTTPException:
#         # Re-raise explicit HTTP exceptions
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal server error")

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
        sent_at_str = data.get("sent_at")
        if sent_at_str:
            try:
        # Handle both "T" and "Z" formats safely
                if sent_at_str.endswith("Z"):
                    sent_at_str = sent_at_str.replace("Z", "")
                utc_time = datetime.strptime(sent_at_str, "%Y-%m-%dT%H:%M:%S.%f")
                utc_time = utc_time.replace(tzinfo=pytz.UTC)
        
                argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
                argentina_time = utc_time.astimezone(argentina_tz)
        
        # Format cleanly without T or timezone offset
                sent_at_formatted = argentina_time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.error(f"Failed to convert sent_at: {e}")
                sent_at_formatted = sent_at_str
        else:
            sent_at_formatted = None
        metadata = {
            "group_name": data.get("group_name", "Unknown Group"),
            "message_id": data.get("message_id", "N/A"),
            "sender": data.get("sender_jid"),
            "timestamp": file_stats.st_ctime,
            "file_size": file_stats.st_size,
            "sent_at": sent_at_formatted,
            # "skip_ocr": data.get("skip_ocr", False),
            "image_url": f"{PUBLIC_URL}/files/{os.path.basename(local_path)}",
            "image_filename": os.path.basename(local_path)
        }

        # Changes for pdf

        # if metadata["skip_ocr"]:
        #     # If skipping, image_base64 is NOT present or is None.
        #     # We pass None/empty string and the metadata to Celery.
        #     # The Celery task process_receipt will handle the rest (inserting empty row).
            
        #     logger.info("📄 PDF detected (skip_ocr=True). Queuing task without image data.")
        #     # Send None for image_base64 as it's not needed/present
        #     process_receipt.delay(None, metadata)

        #     # Changes for pdf

        with open(local_path, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
        logger.info(f"Metadata: {metadata}")

        # Queue OCR processing
        process_receipt.delay(encoded_image, metadata)
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
