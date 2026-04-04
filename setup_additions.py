#!/usr/bin/env python3
"""
Script to append additions detection functions to pipeline/parser.py
and update main.py for 6-worker parallel processing
"""

import re

# Read current parser.py
with open('d:\\BCA\\4th_sem\\electoral-roll-ocr\\pipeline\\parser.py', 'r') as f:
    parser_content = f.read()

# Additions functions code
additions_code = '''


# ── Voter Additions / Amendments Detection ────────────────────────────────────

def detect_additions_section(text: str) -> bool:
    """
    Detect if text contains voter additions/amendments/new registrations.
    
    Additions sections typically contain keywords like:
    - 'ADDITIONS PART A' or 'ADDITIONS PART B'
    - 'NEW ELECTORS REGISTERED'
    - 'AMENDMENTS TO PART I'
    - 'DELETION OF NAME'
    """
    additions_keywords = [
        'ADDITION', 'AMENDMENT', 'CORRECTION',
        'NEW ELECTOR', 'NEW VOTER', 'NEW REGISTR',
        'DELETION', 'REMOVAL', 'STRUCK OFF',
        'SUPPLEMENTARY', 'PART A', 'PART B',
    ]
    
    text_upper = text.upper()
    return any(keyword in text_upper for keyword in additions_keywords)


def parse_additions_fields(text: str, epic: str = '', addition_type: str = 'Amendment') -> dict:
    """
    Parse voter additions/amendments data using same field extraction as regular voters.
    Addition type: 'New', 'Amendment', 'Deletion', etc.
    Returns the parsed record with Record Type field added, or None if invalid.
    """
    base_record = parse_voter_fields(text, epic=epic)
    if base_record is None:
        return None
    
    # Add metadata field indicating this is an addition
    if 'NEW' in text.upper():
        base_record['Record Type'] = 'New'
    elif 'DELETE' in text.upper() or 'STRUCK' in text.upper():
        base_record['Record Type'] = 'Deletion'
    elif 'AMENDMENT' in text.upper() or 'CORRECTION' in text.upper():
        base_record['Record Type'] = 'Amendment'
    else:
        base_record['Record Type'] = addition_type
    
    return base_record
'''

# Append to parser.py
with open('d:\\BCA\\4th_sem\\electoral-roll-ocr\\pipeline\\parser.py', 'a') as f:
    f.write(additions_code)

print("✓ Added detection and parsing functions to pipeline/parser.py")

# Update main.py for 6 workers
with open('d:\\BCA\\4th_sem\\electoral-roll-ocr\\main.py', 'r') as f:
    main_content = f.read()

# Replace 4 workers with 6
main_content = main_content.replace(
    'with ThreadPoolExecutor(max_workers=4) as executor:',
    'with ThreadPoolExecutor(max_workers=6) as executor:'
)

with open('d:\\BCA\\4th_sem\\electoral-roll-ocr\\main.py', 'w') as f:
    f.write(main_content)

print("✓ Updated main.py to use 6 parallel workers")
