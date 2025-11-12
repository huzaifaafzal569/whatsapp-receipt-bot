

import re

# The pattern you provided (using re.S | re.I for DotAll and IgnoreCase)
pattern = {
    'alphanumeric_op': r'(?:C[oó]digo\s+de\s+transacci[oó]n|C[oó]digo\s+de\s+identificaci[oó]n|referencia|control|id Op.|transacci[oó]n|operation|C[oó]mprobante)\s*[:\-]?\s*'
                       r'(?=[A-Za-z0-9\s\n\-]*[A-Za-z])(?=[A-Za-z0-9\s\n\-]*[0-9])'
                       r'([A-Za-z0-9\s\n\-]{20,36})',
    'numeric_op': r'(?:n°?\s+de\s+operaci[oó]n|n[uú]mero\s+de\s+operaci[oó]n\s+de\s+Mercado\s*Pago|nro\.|n°?\s*control|referencia|transacti[oó]n|n°?\s*c[oó]mprobante)'
                        r'\s*[:\-]?[\s\n]{0,10}([0-9]+)',
    'referencia_op':r'referen[cñ]ia\s*[:\-]?\s*[\s\n]{0,10}\s*([A-Za-z0-9\s\n\-]+?)',
    'amount': r'(?:\$|PESOS|IMPORTE|MONTO|TOTAL|PAGO)\s*[:$]?\s*(\d+(?:[.,]\d+)+)',
}

Amount="Noting"
def format_to_argentine_locale(raw_value: str) -> str:
    """Converts a raw numeric string (e.g., '784596.27' or '784.596,27')
    into a clean Argentine string (e.g., '784.596,27').
    """
    if not raw_value:
        return "0,00" # Safe return

    # 1. Clean up spacing and currency symbols (if any)
    clean_value = raw_value.strip().replace(' ', '')
    
    # 2. Convert to a US/Python standard float string (e.g., '784596.27')
    
    # Check for two separators (e.g., 1.234,56 or 1,234.56)
    if '.' in clean_value and ',' in clean_value:
        # Determine decimal separator by its position (rightmost is usually decimal)
        if clean_value.rfind(',') > clean_value.rfind('.'):
            # Format is 1.234,56 (AR format) -> remove dots, keep comma
            float_str = clean_value.replace('.', '')
        else:
            # Format is 1,234.56 (US format) -> remove commas, keep dot
            float_str = clean_value.replace(',', '')
    else:
        # Only one separator (e.g., 784596.27 or 784596,27) or none.
        float_str = clean_value

    # 3. Convert to float to normalize, then format as clean AR string.
    try:
        # Convert to float to handle different raw formats
        num_value = float(float_str.replace(',', '.')) 
        
        # Split number into integer and decimal components based on Python's string representation
        # Example: 784596.27 -> '784596' and '27'
        integer_part, decimal_part = "{:.2f}".format(num_value).split('.')
        
    except ValueError:
        return raw_value # Return original value if conversion fails

    # 4. Insert periods as thousands separators into the integer part
    formatted_integer = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted_integer += "."
        formatted_integer += digit
    
    # Reverse back
    formatted_integer = formatted_integer[::-1]
    
    # 5. Combine with the Argentine decimal comma
    return f"{formatted_integer},{decimal_part}"
# def format_to_argentine_locale(raw_value: str) -> str:
#         """Converts '786435,27' to '786.435,27'"""
#         raw_value = raw_value.replace(' ', '').replace('.', '') # Clean up existing periods/spaces if any
        
#         # Split into integer and decimal part (comma is the decimal separator)
#         if ',' in raw_value:
#             integer_part, decimal_part = raw_value.split(',', 1)
#         else:
#             integer_part = raw_value
#             decimal_part = None
        
#         # Insert periods as thousands separators from the right of the integer part
#         formatted_integer = ""
#         for i, digit in enumerate(reversed(integer_part)):
#             if i > 0 and i % 3 == 0:
#                 formatted_integer += "."
#             formatted_integer += digit
        
#         # Reverse the integer part back and combine
#         formatted_integer = formatted_integer[::-1]
        
#         if decimal_part is not None:
#             return f"{formatted_integer},{decimal_part}"
#         else:
#             return formatted_integer
        
text = """$ 784528.27"""
if amount_match := re.search(pattern['amount'], text, re.I):
    # extracted_data['Amount'] = amount_match.group(1).strip()
    raw_amount = amount_match.group(1).strip()
    Amount = format_to_argentine_locale(raw_amount)
    print(Amount)
else:
# Fallback: try to find a standalone numeric pattern like 400,000.00 or 1.234,56
    amount_match = re.search(r'(\d{1,3}(?:[.,]\d{3})+[.,]\d{2})', text)
    if amount_match:
        raw_amount = amount_match.group(1).strip()
        # APPLY FORMATTING HERE:
        Amount = format_to_argentine_locale(raw_amount)
        print(Amount)
    else:
        Amount = None
