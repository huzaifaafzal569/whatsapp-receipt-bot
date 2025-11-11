from app.utils.drive import upload_file_and_get_link, get_drive_service, get_or_create_folder
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
import pytz
from datetime import datetime

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



# Supplier detection
SUPPLIERS = [
    "Transgestiona",
    "Prestigio pagos",
    "Plataforma de pago",
    "Aurinegros",
    "Cobro Express",
    "Cobro Sur Sa",
    "CLAN SRL",
    "RAZ Y CIA",
    "Cobro sur"
]
DEFAULT_SUPPLIER = "Other"

def detect_supplier(text: str) -> str:
    text_lower = text.lower()
    for supplier in SUPPLIERS:
        if supplier.lower() in text_lower:
            return supplier
        elif supplier.lower() not in text_lower and "cuidad" in text_lower:
            return "Transgestiona"
    return DEFAULT_SUPPLIER

FOLDER_GROUPS = {
    "Prestigio": ["Transgestiona", "Prestigio pagos", "Plataforma de pago", "Aurinegros", "Cobro Sur Sa", "Cobro sur"],
    "Cobro_Express": ["Cobro Express"],
    "Clan": ["CLAN SRL"],
    "Open": ["RAZ Y CIA"],
    "Others": []  # This will catch all others
}

def get_folder_for_supplier(supplier_name: str) -> str:
    """Return the folder name for a given supplier."""
    if not supplier_name:
        return "Others"
    supplier_lower = supplier_name.lower()
    for folder, suppliers in FOLDER_GROUPS.items():
        for s in suppliers:
            if s.lower() in supplier_lower:
                return folder
    return "Others"


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

    # --- Detect supplier ---
    supplier = detect_supplier(cleaned_text)
    logger.info(f"Detected supplier: {supplier}")

    # --- Upload to Drive ---
    DRIVE_PARENT_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
    try:
        drive_service = get_drive_service()
        folder_name = get_folder_for_supplier(supplier)
        image_link = upload_file_and_get_link(
            local_path=image_path,
            dest_name=os.path.basename(image_path),
            supplier_folder=folder_name  # now points to the correct folder group
    )
    except Exception as e:
        logger.warning(f"Drive upload failed: {e}")
        image_link = None

    # 6. Data Extraction
    extracted_data = {
    'Receipt_Date': None,
    'Amount': None,
    'Sender_CUIT': None,
    'Receiver_CUIT': None,
    'Transaction_Number': None,
    'Destination_Bank': None,
    'Supplier': supplier,
    'WhatsApp_Group': metadata.get('group_name', 'Direct Chat'),
    'Receipt_Sent_Time': metadata.get('sent_at'),
    'image_URL': metadata.get('image_url')
    
    }
#    

    # ---------- DESTINO / CBU / CVU BANK DETECTION ----------
    extracted_data['Destination_Bank'] = None
    cleaned_lower = cleaned_text.lower()

    # mapping from detected code -> bank name
    destino_map = {
        "007": "Galicia",
        "285": "Macro",
        "191": "Credicoop Nueva",
        "053": "Agil Pagos",        # normalize 0000053 -> take last 3 as '053'
        "044": "Hipotecario",
        "011": "Nacion",
        "029": "Ciudad",
        "072": "Santander",
    }

    def norm_code(code: str) -> str:
        code = re.sub(r'\D', '', code or "")  # remove non-digits
        # Agil Pagos special case (e.g., 0000053...)
        if code.startswith("00000") and len(code) >= 7:
            return code[5:8]  # take digits 6,7,8
        # General case: take first 3 digits
        if len(code) >= 3:
            return code[:3]
        # If code is shorter than 3 digits, pad with zeros
        return code.zfill(3) 

    # 1) Try explicit "destino" followed by short code (1–7 digits)
    m = re.search(r'destino[:\s]*([0-9]{1,7})', cleaned_lower)
    if m:
        code_raw = m.group(1)
        code = norm_code(code_raw)
        extracted_data['Destination_Bank'] = destino_map.get(code)
        logger.info(f"destino match -> raw:{code_raw} normalized:{code} bank:{extracted_data['Destination_Bank']}")

    # 2) If not found, look for a 22-digit CBU/CVU and extract its first 3 digits (common case)
    if not extracted_data['Destination_Bank']:
        m = re.search(r'(?:CBU|CVU)[:\s]*([0-9]{22})', cleaned_lower)
        if m:
            cbu = m.group(1)
            bank_code = cbu[:3]  # first 3 digits of CBU are the bank code
            code = norm_code(bank_code)
            extracted_data['Destination_Bank'] = destino_map.get(code)
            logger.info(f"22-digit CBU found -> bank_code:{bank_code} normalized:{code} bank:{extracted_data['Destination_Bank']}")

    # 3) If still not found, try cbu/cvu with any digits and take first 3 digits
    if not extracted_data['Destination_Bank']:
        m = re.search(r'(?:CBU|CVU)[:\s]*([0-9]{3,7})', cleaned_lower)
        if m:
            code_raw = m.group(1)
            code = norm_code(code_raw)
            extracted_data['Destination_Bank'] = destino_map.get(code)
            logger.info(f"short cbu/cvu match -> raw:{code_raw} normalized:{code} bank:{extracted_data['Destination_Bank']}")
    bank_name_patterns = ["Hipotecario", "Santander", "Galicia", "Provincia", "Macro",
                                "BBVA", "ICBC", "Ciudad", "Credicoop", "Agil Pagos", "Nacion"]
    # 4) Fallback: text-based bank detection (your existing list)
    if not extracted_data['Destination_Bank']:
                # SAFE:
        before, sep, after_para = cleaned_lower.partition("para")
        if sep:  # only proceed if 'para' exists
            for b in bank_name_patterns:
                if b.lower() in after_para:
                    extracted_data['Destination_Bank'] = b
                    logger.info(f"text match -> bank:{b}")
                    break

    # 5) Special rule you wanted: if supplier == "Cobro Express" and no 'para' use Agil Pagos
    if not extracted_data['Destination_Bank']:
        if extracted_data.get('Supplier', '').lower()=="cobro express buenos aires sa" or extracted_data.get('Supplier', '').lower()=="cobro express":
            extracted_data['Destination_Bank'] = "Agil Pagos"
            logger.info("No 'para' and supplier Cobro Express -> set Agil Pagos")

    if not extracted_data['Destination_Bank']:
        before, sep, after_para = cleaned_lower.partition("para")
        if sep:

            # 1️⃣ Try to find a 22-digit CBU/CVU in the "after para" text
            m = re.search(r'(?:CVU|CBU)[:\s]*([0-9]{22})', after_para, re.IGNORECASE)
            if m:
                cbu = m.group(1)
                bank_code = cbu[:3]
                code = norm_code(bank_code)
                extracted_data['Destination_Bank'] = destino_map.get(code)
                logger.info(f"'para' section 22-digit CBU found -> bank_code:{bank_code} normalized:{code} bank:{extracted_data['Destination_Bank']}")
    
    if not extracted_data['Destination_Bank']:
        if extracted_data.get('Supplier', '').lower()=="transgestiona" or extracted_data.get('Supplier', '').lower()=="transgestiona S A":
            extracted_data['Destination_Bank'] = "Ciudad"
            logger.info("No 'para' and supplier Cobro Express -> set Agil Pagos")

    

        # 2️⃣ Otherwise, search in full text
    if not extracted_data['Destination_Bank']:
        for b in bank_name_patterns:
            if b.lower() in cleaned_lower:
                extracted_data['Destination_Bank'] = b
                break

    logger.info(f"Final Destination_Bank: {extracted_data.get('Destination_Bank')}")

    patterns = {
    # Date: handles both numeric and Spanish text dates
    'date': r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)?[,]?\s*\d{1,2}\s*(?:de\s+)?(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*\s*(?:de\s+)?\d{4})',
    
    # Amount: prevents picking large numbers (filters via \$ or before “Motivo”)
    # 'amount': r'(?:\$|PESOS|IMPORTE|MONTO|TOTAL|PAGO)\s*[:$]?\s*([\d.,]+)',
    'amount': r'(?:\$|PESOS|IMPORTE|MONTO|TOTAL|PAGO)\s*[:$]?\s*(\d+(?:[.,]\d+)+)',

    
    # CUIT: same as before
    #
    
    # 'cuit': r'(?:CUIT|CUIL|DNI|origen|ORIGEN|N[úu]m\s*Doc)?[:\s\n]*([\d\-]{11,15})',
    'cuit': r'(?:CUIT|CUIL|DNI|origen|ORIGEN|N[úu]m\s*Doc)[:\s\n]*([0-9\-]{11,15})',

    # Operation/Transaction number: looks for Mercado Pago references and large IDs
    
    # 'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n|control|comprobante|transacci[oó]n)\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([\s\S]*?([0-9]+)',
    # 'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n|control|comprobante|transacci[oó]n)\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([\s\S]*?)(\d+)'
    # 'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n|control|comprobante|transacci[oó]n)\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([\d\s\n]+)'
    # 'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n|control|comprobante|transacci[oó]n)'
    # r'(?:\s*(?:or|o)?\s*CTRL)?'
    # r'\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([A-Z0-9\s\n]+)',
    'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n|control|comprobante|transacci[oó]n|operation)'
    r'(?:\s*(?:or|o)?\s*CTRL)?'
    r'\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([A-Za-z0-9\s\n]+)',

    'numeric_op': r'(?:n[uú]mero\s+de\s+operaci[oó]n\s+de\s+Mercado\s*Pago)\s*[:\-]?\s*([0-9]+)',
    # 'numeric_op': r'(?:n[uú]mero\s+de\s+operaci[oó]n\s+de\s+Mercado\s*Pago|referen[cñ]ia|control|transacci[oó]n|identificaci[oó]n|operation)\s*[:\-]?\s*([0-9]+?)',
    # 'alphanumeric_op': r'(?:c[oó]digo\s+de\s+identificaci[oó]n|referencia|control|comprobante|transacci[oó]n|operation)\s*[:\-]?\s*([A-Za-z0-9\s\n]+)',
    'alphanumeric_op': r'(?:C[oó]digo\s+de\s+transacci[oó]n|C[oó]digo\s+de\s+identificaci[oó]n|referencia|control|transacci[oó]n|operation|C[oó]mprobante)\s*[:\-]?\s*([A-Za-z0-9\s\n\-]+?)' # Note the non-greedy '?'
                      r'(?=\s*(?:Fecha|Hora|CBU|CUIL|De|Para|Importe|\$|Tipo|Concepto|Referencia))',
    'referencia_op': r'referen[cñ]ia\s*[:\-]?\s*[\s\n]{0,10}\s*([A-Za-z0-9\s\n\-]+?)',



    # 'operation': r'(?:operaci[oó]n|referencia|c[oó]digo|identificaci[oó]n|comprobante)\s*(?:de\s+)?(?:Mercado\s*Pago)?\s*[:\-]?\s*([0-9]+)'
    }
#    

    if date_match := re.search(patterns['date'], cleaned_text, re.I):
        date_str = date_match.group(1).strip().lower()
        # Convert Spanish month names to numbers
        months = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "setiembre": "09", "octubre": "10",
            "noviembre": "11", "diciembre": "12",
            "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05",
            "jun": "06", "jul": "07", "ago": "08", "sep": "09", "oct": "10",
            "nov": "11", "dic": "12"
        }

        # Try to normalize date
        try:
            # Example: "06 de noviembre de 2025"
            parts = re.findall(r"(\d{1,2})\D+(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*\D+(\d{4})", date_str)
            if parts:
                day, month_abbr, year = parts[0]
                month = months.get(month_abbr, "01")
                formatted_date = f"{year}-{month}-{int(day):02d}"
            else:
                # fallback for numeric formats like 06/11/2025 or 6-11-25
                d = re.findall(r"\d{1,2}", date_str)
                y = re.findall(r"\d{2,4}", date_str)
                if len(d) >= 2 and y:
                    day = d[0]
                    month = d[1]
                    year = y[-1]
                    if len(year) == 2:
                        year = f"20{year}"
                    formatted_date = f"{year}-{int(month):02d}-{int(day):02d}"
                else:
                    formatted_date = date_str

            extracted_data['Receipt_Date'] = formatted_date
        except Exception as e:
            logger.warning(f"Date parsing failed: {e}")
            extracted_data['Receipt_Date'] = date_str
    else:
        argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
        current_date = datetime.now(argentina_tz).strftime("%Y-%m-%d")
        extracted_data['Receipt_Date'] = current_date
        logger.info(f"No date found — using current Argentina date: {current_date}")
    
    

    if amount_match := re.search(patterns['amount'], cleaned_text, re.I):
        extracted_data['Amount'] = amount_match.group(1).strip()
    else:
    # Fallback: try to find a standalone numeric pattern like 400,000.00 or 1.234,56
        amount_match = re.search(r'(\d{1,3}(?:[.,]\d{3})+[.,]\d{2})', cleaned_text)
        if amount_match:
            extracted_data['Amount'] = amount_match.group(1).strip()
        else:
            extracted_data['Amount'] = None



    # # --- Sender CUIT ---
    # if 'De' in cleaned_text:
    #     sender_area = cleaned_text.split('De', 1)[-1]
    #     if 'Para' in sender_area:
    #         sender_area = sender_area.split('Para', 1)[0]
    # else:
    #     sender_area = cleaned_text

    # sender_area = re.sub(r'\s+', ' ', sender_area)
    # if sender_match := re.search(patterns['cuit'], sender_area, re.I):
    #     extracted_data['Sender_CUIT'] = re.sub(r'\D', '', sender_match.group(1))
    # else:
    #     extracted_data['Sender_CUIT'] = None

    # --- Sender CUIT Extraction ---9
    sender_area = cleaned_text
    if 'De' in cleaned_text:
        sender_area = cleaned_text.split('De', 1)[-1]
        if 'Para' in sender_area:
            sender_area = sender_area.split('Para', 1)[0]
    # sender_area = re.sub(r'\s+', ' ', cleaned_text.split('De', 1)[-1].split('Para', 1)[0] if 'De' in cleaned_text else cleaned_text)
    sender_area = re.sub(r'\s+', ' ', sender_area)
    # if sender_match := re.search(patterns['cuit'], sender_area, re.I):
    if sender_match := re.search(patterns['cuit'], sender_area, re.I | re.S):
        cuit_digits = re.sub(r'\D', '', sender_match.group(1))
        # validate length = 11
        if len(cuit_digits) == 11:
            if 'De' in cleaned_text or cuit_digits.startswith('2'):
                extracted_data['Sender_CUIT'] = cuit_digits
            else:
                extracted_data['Sender_CUIT'] = None   
        else:
            extracted_data['Sender_CUIT'] = None
    else:
        extracted_data['Sender_CUIT'] = None

    # receiver_area = re.sub(r'\s+', ' ', cleaned_text.split('Para', 1)[-1] if 'Para' in cleaned_text else cleaned_text)
    # if receiver_match := re.search(patterns['cuit'], receiver_area, re.I):
    #     cuit_digits = re.sub(r'\D', '', sender_match.group(1))
    #     # validate length = 11
    #     if len(cuit_digits) == 11:
    #         extracted_data['Sender_CUIT'] = cuit_digits
    #     else:
    #         extracted_data['Sender_CUIT'] = None




    # else:
    #     extracted_data['Sender_CUIT'] = None
    #     r_id = re.sub(r'\D', '', receiver_match.group(1))
    #     if r_id and r_id != extracted_data.get('Sender_CUIT'):
    #         extracted_data['Receiver_CUIT'] = r_id
    #     else:
    #         extracted_data['Receiver_CUIT'] = None
    # else:
    #     extracted_data['Receiver_CUIT'] = None
    

    # --- Transaction / Operation Number ---
    if op_match := re.search(patterns['numeric_op'], cleaned_text, re.I | re.S):
        op_value = op_match.group(1).strip()
        if op_value:
            extracted_data['Transaction_Number'] = op_value[-6:].lower() if len(op_value) >= 6 else op_value.lower()
    elif op_match := re.search(patterns['alphanumeric_op'], cleaned_text, re.I | re.S):
        op_value = op_match.group(1).strip().replace('-', '').replace(' ', '')
        if op_value:
            extracted_data['Transaction_Number'] = op_value[-6:].lower() if len(op_value) >= 6 else op_value.lower()

    elif op_match := re.search(patterns['referencia_op'], cleaned_text, re.I | re.S):
    # Tier 2: Referencia (Requires cleanup for spaces/hyphens since it can be mixed)
        op_value = op_match.group(1).strip().replace('-', '').replace(' ', '')
        if op_value:
            extracted_data['Transaction_Number'] = op_value[-6:].lower() if len(op_value) >= 6 else op_value.lower()
    else:
        extracted_data['Transaction_Number'] = None

    # Add WhatsApp metadata placeholders (filled by main.py)
    extracted_data['WhatsApp_Group'] = metadata.get('group_name')#, 'Direct Chat')
    extracted_data['Receipt_Sent_Time'] = metadata.get('sent_at')
    # extracted_data['image_URL'] = metadata.get('image_url')

    logger.info("Extraction complete")
    logger.info(json.dumps(extracted_data, indent=4))
    

# --- Upload image to Drive and get link ---
    try:
        image_link = upload_file_and_get_link(local_path=image_path, dest_name=os.path.basename(image_path), supplier_folder=folder_name)
        extracted_data['image_URL'] = image_link
    except Exception as e:
        logger.warning(f"Drive upload failed: {e}")
        extracted_data['image_URL'] = None
    # image_link = metadata.get('image_url') or ''
    # --- Build final data row for Sheets ---
    row = {
        'Receipt_Date': extracted_data.get('Date') or extracted_data.get('Receipt_Date') or None,
        'Amount': extracted_data.get('Amount'),
        # 'Sender_Name': extracted_data.get('Sender_Name'),
        'Sender_CUIT': extracted_data.get('Sender_ID') or extracted_data.get('Sender_CUIT'),
        # 'Receiver_CUIT': extracted_data.get('Receiver_ID') or extracted_data.get('Receiver_CUIT'),
        'Transaction_Number': extracted_data.get('Operation_Number') or extracted_data.get('Transaction_Number'),
        'Supplier': extracted_data.get('Supplier'),
        'Destination_Bank': extracted_data.get('Destination_Bank'),
        'WhatsApp_Group': metadata.get('group_name') or metadata.get('from_group') or 'Unknown Group',
        'Receipt_Sent_Time': metadata.get('sent_at') or metadata.get('timestamp') or time.time(),
        'Image_Link': extracted_data.get('image_URL') or ''
    }

    # Map to sheet order (adjust columns / order to match sheet)
    sheet_row = [
        row['Receipt_Date'],
        row['Amount'],
        row['Sender_CUIT'],
        # row['Receiver_CUIT'],
        row['Transaction_Number'],
        row['Supplier'],
        row['Destination_Bank'],
        row['WhatsApp_Group'],
        row['Receipt_Sent_Time'],
        row['Image_Link']
    ]

    # Call sheet writer. Use environment variable SPREADSHEET_ID in container
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1u3M6OKKg08A0SA_Sz-hhDn4aVmbbG27Rl8msOKFFxpI')
    try:
        # write_row(SPREADSHEET_ID, sheet_row, sheet_range="botnogal!A1")
        write_row(spreadsheet_id=SPREADSHEET_ID,row_values=sheet_row,sheet_base_name="botnogal",max_rows=1000  # Optional: change limit per sheet
)
        logger.info("✅ Wrote row to Google Sheets.")
    except Exception as e:
        logger.error(f"Failed to write to Google Sheets: {e}")


    try:
        os.remove(image_path)
        os.remove(text_file)
        logger.info(f"🗑️ Deleted temporary files: {image_path}, {text_file}")
    except Exception as e:
        logger.warning(f"Failed to delete temp files: {e}")
    return extracted_data
    