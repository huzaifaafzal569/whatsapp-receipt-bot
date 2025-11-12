

import re

# The pattern you provided (using re.S | re.I for DotAll and IgnoreCase)
pattern = {
    'alphanumeric_op': r'(?:C[oó]digo\s+de\s+transacci[oó]n|C[oó]digo\s+de\s+identificaci[oó]n|referencia|control|id Op.|transacci[oó]n|operation|C[oó]mprobante)\s*[:\-]?\s*'
                       r'(?=[A-Za-z0-9\s\n\-]*[A-Za-z])(?=[A-Za-z0-9\s\n\-]*[0-9])'
                       r'([A-Za-z0-9\s\n\-]{20,36})'
}

# --- CORRECTED INPUT STRING ---
text = """
transaccion

88CSA5CA8S-CAS5C8FF08-O

CNAJUSHCJSHJNC
"""

# The re.S flag (re.DOTALL) is essential here to allow '.' and '\s' to match across newlines
# The re.I flag (re.IGNORECASE) is also used as in your original logic
matches = re.findall(pattern['alphanumeric_op'], text, re.IGNORECASE | re.DOTALL)

print(matches)