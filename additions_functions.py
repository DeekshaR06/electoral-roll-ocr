# Code snippet to add to pipeline/parser.py at the end of the file
# These functions detect and parse voter additions/amendments

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
