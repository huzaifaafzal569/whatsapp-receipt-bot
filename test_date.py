import re
import pytz
from datetime import datetime

patterns={'date': r'(\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b' # DD/MM/YYYY
        r'|\b\d{1,2}[-/](?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*[-/]\d{2,4}\b' # <-- NEW HYBRID FORMAT
        r'|\b(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)?[,]?\s*\d{1,2}\s*(?:de\s+)?(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*\s*(?:de\s+)?\d{4})'}


cleaned_text="""5/11/2025 . 10:00 h
"""

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

            Receipt_Date = formatted_date
            print(Receipt_Date)
        except Exception as e:
            # logger.warning(f"Date parsing failed: {e}")
            Receipt_Date = date_str
else:
    argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    current_date = datetime.now(argentina_tz).strftime("%Y-%m-%d")
    Receipt_Date = current_date
    print(Receipt_Date)