

import re

# The pattern you provided (using re.S | re.I for DotAll and IgnoreCase)
pattern = {
    'alphanumeric_op': r'(?:C[oó]digo\s+de\s+transacci[oó]n|C[oó]digo\s+de\s+identificaci[oó]n|referencia|control|id Op.|transacci[oó]n|operation|C[oó]mprobante)\s*[:\-]?\s*'
                       r'(?=[A-Za-z0-9\s\n\-]*[A-Za-z])(?=[A-Za-z0-9\s\n\-]*[0-9])'
                       r'([A-Za-z0-9\s\n\-]{20,36})',
    'numeric_op': r'(?:n°?\s+de\s+operaci[oó]n|n[uú]mero\s+de\s+operaci[oó]n\s+de\s+Mercado\s*Pago|nro\.|n°?\s*control|referencia|transacti[oó]n|n°?\s*c[oó]mprobante)'
                        r'\s*[:\-]?[\s\n]{0,10}([0-9]+)',
    'referencia_op':r'referen[cñ]ia\s*[:\-]?\s*[\s\n]{0,10}\s*([A-Za-z0-9\s\n\-]+?)',
}
matches="no"
# --- CORRECTED INPUT STRING ---
text = """
Refencia:               VARIOS

Nro Control:             7854

"""

# The re.S flag (re.DOTALL) is essential here to allow '.' and '\s' to match across newlines
# The re.I flag (re.IGNORECASE) is also used as in your original logic
if "Nro Control" in text:
        # control_area = text.split("Nro Control:", 1)[-1]
        # control_area = re.sub(r'\s+', ' ', control_area)
        if op_match := re.search(pattern['numeric_op'], text, re.I | re.S):
            op_value = op_match.group(1).strip().replace('-', '').replace(' ', '')
            if op_value:
                matches = op_value[-6:].lower() if len(op_value) >= 6 else op_value.lower()
                print(matches)
