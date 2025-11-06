from app.utils.drive import upload_file_and_get_link
from app.utils.gsheet import write_row
from celery import Celery
import cv2
import numpy as np
from paddleocr import PaddleOCR
import os
import re
import logging
import json
from typing import Dict, Any, Optional, List
import time
import base64
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Celery
# app = Celery('tasks', broker='redis://redis:6379/0')
BROKER_URL = os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))
app = Celery('tasks', broker=BROKER_URL)

# PaddleOCR initialization with retries
def initialize_paddle_ocr(max_retries=3, delay=5):
    """Initialize PaddleOCR with retries"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting PaddleOCR initialization (attempt {attempt + 1}/{max_retries})...")
            engine = PaddleOCR(
                use_angle_cls=False,
                lang='es',
                # use_gpu=False,
                # show_log=False,
                # enable_mkldnn=True  # Better CPU performance
            )
            logger.info("✅ PaddleOCR engine initialized successfully")
            return engine
        except Exception as e:
            logger.error(f"❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    return None

# Global OCR engine initialization
ocr_engine = initialize_paddle_ocr()

if ocr_engine is None:
    logger.error("❌ FATAL: Failed to initialize PaddleOCR after all retries")
    
# Lazy initialization as fallback
def get_ocr_engine():
    """Get or initialize OCR engine"""
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = initialize_paddle_ocr()
    return ocr_engine

def extract_text_from_result(page_results: List[Any]) -> List[str]:
    """
    Extract text lines from a single page's PaddleOCR result structure.
    """
    text_lines = []
    if not isinstance(page_results, list): return text_lines
    for line_data in page_results:
        try:
            if isinstance(line_data, (list, tuple)) and len(line_data) >= 2 and isinstance(line_data[1], (list, tuple)):
                text = line_data[1][0]
                if text and isinstance(text, str):
                    text_lines.append(text.strip())
        except Exception:
            continue
    return text_lines

def preprocess_image_for_ocr(path: str) -> Optional[np.ndarray]:
    """Load image and return the raw BGR NumPy array for OCR."""
    try:
        img = cv2.imread(path)
        if img is None:
            return None
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        return img 
    except Exception as e:
        logger.error(f"Image loading/preprocessing failed: {e}")
        return None

def normalize_amount(raw_amount: str) -> str:
    """Normalize amount string to a standard integer format."""
    norm = raw_amount.strip().replace(" ", "")
    norm = re.sub(r'[\$£€]', '', norm)
    # Simple strategy: remove all non-digits, assuming the user only wants the integer part
    return re.sub(r'[^0-9]', '', norm)


@app.task
def process_receipt(image_base64: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Process receipt image and extract structured data."""
    
    ocr_engine=get_ocr_engine()
    if ocr_engine is None:
        logger.error("❌ OCR Engine is None. Initialization failed globally.")
        return {}
    
    # Create a temp file to store the decoded image
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        image_path = tmp.name
        tmp.write(base64.b64decode(image_base64))
    
    logger.info(f"✅ Temporary image created: {image_path}")
        
    if not os.path.exists(image_path):
        logger.error(f"File not found: {image_path}")
        return {}

    logger.info(f"Processing {image_path}...")
    
    # 2. Preprocess image
    preprocessed_img = preprocess_image_for_ocr(image_path)
    if preprocessed_img is None:
        logger.error(f"Failed to load or preprocess image: {image_path}")
        return {}

    # 3. OCR extraction
    result = []
    try:
        logger.info("Running OCR on image...")
        result = ocr_engine.ocr(image_path)
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {str(e)}", exc_info=True)
        return {}
        
    # 4. Extract and Clean Text
    text_lines = []
    if isinstance(result, list):
    # New format (dict-based)
        if len(result) > 0 and isinstance(result[0], dict) and "rec_texts" in result[0]:
            text_lines = result[0]["rec_texts"]
        else:
        # Fallback for older list-based format
            for page_result in result:
                text_lines.extend(extract_text_from_result(page_result))
    
    # This is the "purest data" you requested: all lines of text separated by newlines
    full_text = "\n".join(text_lines) 
    cleaned_text = re.sub(r'\s+', ' ', full_text).strip() 
    
    logger.info(f"OCR text extracted ({len(text_lines)} lines): {full_text[:300]}...")
    
    # 5. Save the "purest data" (plain text)
    try:
        text_file = image_path.rsplit(".", 1)[0] + ".txt"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(full_text)
        logger.info(f"Saved OCR text (purest data) to {text_file}")
    except Exception as e:
        logger.warning(f"Failed to save text file: {e}")

    # 6. Data Extraction
    extracted_data = {
    'Receipt_Date': None,
    'Amount': None,
    'Sender_CUIT': None,
    'Receiver_CUIT': None,
    'Transaction_Number': None,
    'Destination_Bank': None,
    'WhatsApp_Group': metadata.get('group_name', 'Direct Chat'),
    'Receipt_Sent_Time': metadata.get('sent_at'),
    'image_URL': metadata.get('image_url')
    
    }
    bank_name_patterns = ["Hipotecario", "Santander", "Galicia", "Provincia", "Macro", "BBVA", "ICBC", "Ciudad"]
    bank_number_patterns = [
    r'CBU[:\s]*([0-9]{22})',
    r'CVU[:\s]*([0-9]{22})',
    r'Destino[:\s]*([0-9]{22})'
]

    extracted_data['Destination_Bank'] = None

# 1️⃣ Try to find bank name first
    for b in bank_name_patterns:
        if b.lower() in cleaned_text.lower():
            extracted_data['Destination_Bank'] = b
            break

# 2️⃣ If no bank name found, look for CBU/CVU number
    if not extracted_data['Destination_Bank']:
        for pattern in bank_number_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                extracted_data['Destination_Bank'] = match.group(1).strip()
                break

    patterns = {
    # Date: handles both numeric and Spanish text dates
    'date': r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)?[,]?\s*\d{1,2}\s*(?:de\s+)?(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*\s*(?:de\s+)?\d{4})',
    
    # Amount: prevents picking large numbers (filters via \$ or before “Motivo”)
    'amount': r'(?:\$|PESOS|IMPORTE|MONTO|TOTAL|PAGO)\s*[:$]?\s*([\d.,]+)',
    
    # CUIT: same as before
    'cuit': r'(?:CUIT|CUIL|DNI|N[úu]m\s*Doc)[:\s]*([0-9]{2}[-]?[0-9]{8}[-]?[0-9]{1})',
    
    # Operation/Transaction number: looks for Mercado Pago references and large IDs
    'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n)\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([A-Z0-9]{6,})',
    }
#     patterns = {
#     'date': r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)?[,]?\s*\d{1,2}\s*(?:de\s+)?(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*\s*(?:de\s+)?\d{4})',
#     'amount': r'(?:[MB]onto|PESOS|IMPORTE|MONEDA|TOTAL|PAGO|Banto1?)\s*[:$]?\s*([\d.,]+)',
#     'cuit': r'(?:CUIT|CUIL|DNI|N[úu]m|identificaci[oó]n)[:.\s]*([0-9]{7,11})',
#     'operation': r'(?:[Nn]\s*de\s*[oc]peraci[oó]n|operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n)\s*[:\-]?\s*([A-Z0-9]{6,})',
# }

    if date_match := re.search(patterns['date'], cleaned_text, re.I):
        date_str = date_match.group(1)
        date_str = (date_str.replace(',', '')
                            .replace(' de ', '/')
                            .replace(' ', '/'))
        extracted_data['Receipt_Date'] = date_str.strip()

    if amount_match := re.search(patterns['amount'], cleaned_text, re.I):
        extracted_data['Amount'] = amount_match.group(1).strip()
    else:
    # Fallback: try to find a standalone numeric pattern like 400,000.00 or 1.234,56
        amount_match = re.search(r'(\d{1,3}(?:[.,]\d{3})+[.,]\d{2})', cleaned_text)
        if amount_match:
            extracted_data['Amount'] = amount_match.group(1).strip()
        else:
            extracted_data['Amount'] = None

    # --- Sender CUIT Extraction ---9
    sender_area = cleaned_text.split('De', 1)[-1].split('Para', 1)[0] if 'De' in cleaned_text else cleaned_text
    if sender_match := re.search(patterns['cuit'], sender_area, re.I):
        extracted_data['Sender_CUIT'] = sender_match.group(1).replace('-', '')
    else:
        extracted_data['Sender_CUIT'] = None

    # --- Receiver CUIT Extraction ---
    receiver_area = cleaned_text.split('Para', 1)[-1] if 'Para' in cleaned_text else cleaned_text
    if receiver_match := re.search(patterns['cuit'], receiver_area, re.I):
        r_id = receiver_match.group(1).replace('-', '')
        if r_id and r_id != extracted_data.get('Sender_CUIT'):
            extracted_data['Receiver_CUIT'] = r_id
        else:
            extracted_data['Receiver_CUIT'] = None
    else:
        extracted_data['Receiver_CUIT'] = None

    # --- Transaction / Operation Number ---
    if op_match := re.search(patterns['operation'], cleaned_text, re.I):
        extracted_data['Transaction_Number'] = op_match.group(1).strip().replace('-', '')
    else:
        extracted_data['Transaction_Number'] = None

    # Add WhatsApp metadata placeholders (filled by main.py)
    extracted_data['WhatsApp_Group'] = metadata.get('group_name')#, 'Direct Chat')
    extracted_data['Receipt_Sent_Time'] = metadata.get('sent_at')
    extracted_data['image_URL'] = metadata.get('image_url')

    logger.info("Extraction complete")
    logger.info(json.dumps(extracted_data, indent=4))
    

# --- Upload image to Drive and get link ---
    # try:
    #     image_link = upload_file_and_get_link(filename)
    # except Exception as e:
    #     logger.warning(f"Drive upload failed: {e}")
    #     image_link = None
    image_link = metadata.get('image_url') or ''
    # --- Build final data row for Sheets ---
    row = {
        'Receipt_Date': extracted_data.get('Date') or extracted_data.get('Receipt_Date') or None,
        'Amount': extracted_data.get('Amount'),
        # 'Sender_Name': extracted_data.get('Sender_Name'),
        'Sender_CUIT': extracted_data.get('Sender_ID') or extracted_data.get('Sender_CUIT'),
        'Receiver_CUIT': extracted_data.get('Receiver_ID') or extracted_data.get('Receiver_CUIT'),
        'Transaction_Number': extracted_data.get('Operation_Number') or extracted_data.get('Transaction_Number'),
        'Destination_Bank': extracted_data.get('Destination_Bank'),
        'WhatsApp_Group': metadata.get('group_name') or metadata.get('from_group') or 'Unknown Group',
        'Receipt_Sent_Time': metadata.get('sent_at') or metadata.get('timestamp') or time.time(),
        'Image_Link': image_link or ''
    }

    # Map to sheet order (adjust columns / order to match sheet)
    sheet_row = [
        row['Receipt_Date'],
        row['Amount'],
        row['Sender_CUIT'],
        row['Receiver_CUIT'],
        row['Transaction_Number'],
        row['Destination_Bank'],
        row['WhatsApp_Group'],
        row['Receipt_Sent_Time'],
        row['Image_Link']
    ]

    # Call sheet writer. Use environment variable SPREADSHEET_ID in container
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', 'YOUR_SPREADSHEET_ID')
    try:
        write_row(SPREADSHEET_ID, sheet_row, sheet_range="botnogal!A1")
        logger.info("✅ Wrote row to Google Sheets.")
    except Exception as e:
        logger.error(f"Failed to write to Google Sheets: {e}")
    return extracted_data
    # # 7. Pattern Matching...
    # if date_match := re.search(patterns['date'], cleaned_text, re.I):
    #     extracted_data['Date'] = date_match.group(1).replace(' de ', '/').replace(' ', '/')

    # if amount_match := re.search(patterns['amount'], cleaned_text, re.I):
    #     extracted_data['Amount'] = normalize_amount(amount_match.group(1))

    # sender_area = cleaned_text.split('De', 1)[-1].split('Para', 1)[0] if 'De' in cleaned_text else cleaned_text
    # if sender_match := re.search(patterns['cuit'], sender_area, re.I):
    #     extracted_data['Sender_ID'] = sender_match.group(1).replace('-', '')

    # receiver_area = cleaned_text.split('Para', 1)[-1] if 'Para' in cleaned_text else cleaned_text
    # if receiver_match := re.search(patterns['cuit'], receiver_area, re.I):
    #     r_id = receiver_match.group(1).replace('-', '')
    #     if r_id and r_id != extracted_data['Sender_ID']:
    #         extracted_data['Receiver_ID'] = r_id

    # if op_match := re.search(patterns['operation'], cleaned_text, re.I):
    #     extracted_data['Operation_Number'] = op_match.group(1).strip().replace('-', '')

    # logger.info("Extraction complete")
    # logger.info(json.dumps(extracted_data, indent=4))
    # return extracted_data