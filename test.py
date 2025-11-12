

import re

# We will use a dedicated pattern for this specific field
control_pattern = r'nro\s*control\s*[:\-]?[\s\n\xa0\-:]+([0-9]+)' 
patterns={'numeric_op': r'(?:n°?\s+de\s+operaci[oó]n|n[uú]mero\s+de\s+operaci[oó]n\s+de\s+Mercado\s*Pago|nro\.|n°?\s*control|referencia|transacti[oó]n|n°?\s*c[oó]mprobante|Nro. de comprobante|comprobante)\s*[:\-]?\s*([0-9]+)'
}
# Note: This is similar to the robust part of 'numeric_op', but only for 'nro control'

# Example Text:
text = """
Reference                VAIOS

comprobante:         1234586
Another line.

"""

if op_match := re.search(patterns['numeric_op'], text, re.I | re.S):
        op_value = op_match.group(1).strip()
        if op_value:
            Transaction_Number = op_value[-6:].lower() if len(op_value) >= 6 else op_value.lower()
            print(f"Found Transaction Number: {Transaction_Number}")

# matches = "NO MATCH FOUND" # Default value

# # --- Dedicated Search Logic ---

# # 1. Check if the specific string is present (optional, but good for filtering large text)
# if "Nro Control" in text:
#     # 2. Search using the highly specific pattern (case-insensitive and dot-all flags)
#     # The pattern targets 'Nro Control' and captures the digits ([0-9]+) after the gap.
#     if op_match := re.search(control_pattern, text, re.I | re.S):
#         op_value = op_match.group(1).strip().replace('-', '').replace(' ', '')
        
#         if op_value:
#             # Apply your final formatting logic (last 6 digits or full value)
#             matches = op_value[-6:].lower() if len(op_value) >= 6 else op_value.lower()
#             print(f"Found Nro Control: {matches}")
#         else:
#             print("Nro Control found, but captured value was empty")
#     else:
#         # This executes if "Nro Control" is in text, but the number was not found right after it
#         print("Nro Control found, but numeric value could not be extracted by regex.")
# else:
#     print(matches) # Prints "NO MATCH FOUND"

# Amount="Noting"
# def format_to_argentine_locale(raw_value: str) -> str:
#     """Converts a raw numeric string (e.g., '784596.27' or '784.596,27')
#     into a clean Argentine string (e.g., '784.596,27').
#     """
#     if not raw_value:
#         return "0,00" # Safe return

#     # 1. Clean up spacing and currency symbols (if any)
#     clean_value = raw_value.strip().replace(' ', '')
    
#     # 2. Convert to a US/Python standard float string (e.g., '784596.27')
    
#     # Check for two separators (e.g., 1.234,56 or 1,234.56)
#     if '.' in clean_value and ',' in clean_value:
#         # Determine decimal separator by its position (rightmost is usually decimal)
#         if clean_value.rfind(',') > clean_value.rfind('.'):
#             # Format is 1.234,56 (AR format) -> remove dots, keep comma
#             float_str = clean_value.replace('.', '')
#         else:
#             # Format is 1,234.56 (US format) -> remove commas, keep dot
#             float_str = clean_value.replace(',', '')
#     else:
#         # Only one separator (e.g., 784596.27 or 784596,27) or none.
#         float_str = clean_value

#     # 3. Convert to float to normalize, then format as clean AR string.
#     try:
#         # Convert to float to handle different raw formats
#         num_value = float(float_str.replace(',', '.')) 
        
#         # Split number into integer and decimal components based on Python's string representation
#         # Example: 784596.27 -> '784596' and '27'
#         integer_part, decimal_part = "{:.2f}".format(num_value).split('.')
        
#     except ValueError:
#         return raw_value # Return original value if conversion fails

#     # 4. Insert periods as thousands separators into the integer part
#     formatted_integer = ""
#     for i, digit in enumerate(reversed(integer_part)):
#         if i > 0 and i % 3 == 0:
#             formatted_integer += "."
#         formatted_integer += digit
    
#     # Reverse back
#     formatted_integer = formatted_integer[::-1]
    
#     # 5. Combine with the Argentine decimal comma
#     return f"{formatted_integer},{decimal_part}"
        
# text = """$ 784528.27"""
# if amount_match := re.search(pattern['amount'], text, re.I):
#     # extracted_data['Amount'] = amount_match.group(1).strip()
#     raw_amount = amount_match.group(1).strip()
#     Amount = format_to_argentine_locale(raw_amount)
#     print(Amount)
# else:
# # Fallback: try to find a standalone numeric pattern like 400,000.00 or 1.234,56
#     amount_match = re.search(r'(\d{1,3}(?:[.,]\d{3})+[.,]\d{2})', text)
#     if amount_match:
#         raw_amount = amount_match.group(1).strip()
#         # APPLY FORMATTING HERE:
#         Amount = format_to_argentine_locale(raw_amount)
#         print(Amount)
#     else:
#         Amount = None
