import re


patterns = {'amount': r'(?:\$|PESOS|IMPORTE|MONTO|TOTAL|PAGO)\s*[:$]?\s*(\d+(?:[.,]\d+)+)'}
def normalize_amount(text, force_two_decimals=False):
    """
    Normaliza importes detectados por OCR:
    - Detecta coma o punto final + 2 dígitos como parte decimal.
    - Devuelve número con coma decimal y puntos de miles.
    Ejemplo: "$ 754528.27" -> "754.528,27"
    """
    if text is None:
        return None

    s = str(text).strip()
    s = re.sub(r'[^\d\.,\s]', '', s)   # dejar solo dígitos, puntos, comas y espacios
    s = s.strip()

    # Buscar si termina con . o , y exactamente 2 dígitos
    m = re.search(r'([.,])(\d{2})\s*$', s)
    if m:
        decimals = m.group(2)
        prefix = s[:m.start(1)]
        integer_digits = re.sub(r'[^0-9]', '', prefix)  # eliminar separadores
        if integer_digits == '':
            integer_digits = '0'
        # Formatear con puntos de miles
        integer_with_dots = f"{int(integer_digits):,}".replace(",", ".")
        return f"{integer_with_dots},{decimals}"
    else:
        # No hay parte decimal válida
        digits = re.sub(r'[^0-9]', '', s)
        if digits == '':
            return ''
        if force_two_decimals:
            formatted = f"{int(digits):,}".replace(",", ".")
            return f"{formatted},00"
        return f"{int(digits):,}".replace(",", ".")

text = """fast 
$300.091,39"""
Amount="None"

if amount_match := re.search(patterns['amount'], text, re.I):
        # extracted_data['Amount'] = amount_match.group(1).strip()
        raw_amount = amount_match.group(1).strip()
        Amount = normalize_amount(raw_amount)
        print(Amount)
else:
# Fallback: try to find a standalone numeric pattern like 400,000.00 or 1.234,56
    amount_match = re.search(r'(\d{1,3}(?:[.,]\d{3})+[.,]\d{2})', text)
    if amount_match:
        raw_amount = amount_match.group(1).strip()
        # APPLY FORMATTING HERE:
        Amount = normalize_amount(raw_amount)
        print(Amount)
    else:
        Amount = None

# 🔍 Ejemplos de prueba
