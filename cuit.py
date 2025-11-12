import re

patterns = {'cuit': r'(?:CUIT|CUIL|DNI|origen|ORIGEN|N[úu]m\s*Doc)[:\s\n]*([0-9\-]{11,15})'}

cleaned_text = """
De
CUIT: 30-12345678-9

"""
sender_area=cleaned_text
sender_area = cleaned_text
if 'De' in cleaned_text:
    sender_area = cleaned_text.split('De', 1)[-1]
    if 'Para' in sender_area:
        sender_area = sender_area.split('Para', 1)[0]
sender_area = re.sub(r'\s+', ' ', sender_area)
if sender_match := re.search(patterns['cuit'], sender_area, re.I | re.S):
        cuit_digits = re.sub(r'\D', '', sender_match.group(1))
        if len(cuit_digits) == 11:
            if ('De' in cleaned_text and not "BNA" in cleaned_text)  or cuit_digits.startswith('2'):
                  print(cuit_digits)