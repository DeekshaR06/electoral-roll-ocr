# pipeline/parser.py
import re
import os


def extract_age_value(text: str) -> str:
    """Extract age from noisy OCR text with tolerant patterns and sanity checks."""
    if not text:
        return ''

    normalized = (text or '').replace('|', ':')
    age_patterns = [
        r'\b(?:age|aged|aqe|a9e|ag[e6])\b\s*[:;=\-]?\s*([0-9OILSBZGTA?§%]{1,3})(?=\s|$|[,:;])',
        r'\b(?:age|aged|aqe|a9e|ag[e6])\D{0,8}([0-9OILSBZGTA?§%]{1,3})(?=\s|$|[,:;])',
        r'([0-9OILSBZGTA?§%]{1,3})\s*(?:years?|yrs?)\b',
    ]

    def normalize_age_token(token: str):
        if not token:
            return None
        mapping = {
            'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8',
            'Z': '2', 'G': '6', 'T': '7', 'A': '4', '?': '7',
            '§': '5', '%': '8',
        }
        cleaned = ''.join(mapping.get(ch.upper(), ch) for ch in token if ch.isalnum() or ch in {'?', '§', '%'})
        digits = re.sub(r'\D', '', cleaned)
        if not digits:
            return None

        val = int(digits)
        if 18 <= val <= 125:
            return val

        # Common OCR artifact: extra leading '1' for two-digit ages (e.g., 164 -> 64).
        if len(digits) == 3 and digits.startswith('1'):
            tail = int(digits[1:])
            if 18 <= tail <= 99:
                return tail
        return None

    candidates = []
    for pattern in age_patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            val = normalize_age_token(match.group(1))
            if val is not None:
                candidates.append(str(val))

    return candidates[0] if candidates else ''


def _debug_age_miss(text: str, debug_context: str = '') -> None:
    """Emit focused debug logs for records where age could not be extracted."""
    if os.getenv('OCR_DEBUG_AGE', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
        return

    raw = text or ''
    compact = re.sub(r'\s+', ' ', raw).strip()
    hint_patterns = [
        r'\b(age|aged|aqe|a9e|ag[e6])\b[^\n]{0,25}',
        r'\b(\d{1,3})\s*(years?|yrs?)\b',
    ]
    hints = []
    for pat in hint_patterns:
        for m in re.finditer(pat, raw, re.IGNORECASE):
            snippet = m.group(0).replace('\n', ' ').strip()
            if snippet and snippet not in hints:
                hints.append(snippet)

    print('[AGE-DEBUG] Missing age')
    if debug_context:
        print(f'[AGE-DEBUG] Context: {debug_context}')
    if hints:
        print(f"[AGE-DEBUG] Nearby age-like text: {' | '.join(hints[:3])}")
    print(f"[AGE-DEBUG] OCR snippet: {compact[:220]}")

def normalize_text(text: str) -> str:
    """Collapse repeated whitespace for regex-friendly parsing."""
    return re.sub(r'\s+', ' ', text).strip()


def parse_voter_fields(
    raw_text: str,
    serial_number: int = None,
    epic: str = '',
    debug_context: str = '',
) -> dict:
    """
    Parse OCR text from a single voter card block into notebook-style fields.
    """
    text = raw_text or ''

    # Use stop words so relation/house lines are not captured as part of the name.
    name = ''
    name_match = re.search(
        r'Name\s*[=:]\s*([A-Za-z\.\s]+?)(?=Husbands?|Mothers?|Fathers?|Others?|House|Age|$)',
        text,
        re.IGNORECASE,
    )
    if name_match:
        name = name_match.group(1).strip()

    # Relation parsing prioritizes common labels in descending frequency.
    relation_type = ''
    relative_name = ''
    rel_match = None

    if re.search(r'Husbands?\s*Name', text, re.IGNORECASE):
        relation_type = 'Husband'
        rel_match = re.search(
            r'Husbands?\s*Name\s*[=:]\s*([A-Za-z\.\s]+?)(?=House|Age|$)',
            text,
            re.IGNORECASE,
        )
    elif re.search(r'Fathers?\s*Name', text, re.IGNORECASE):
        relation_type = 'Father'
        rel_match = re.search(
            r'Fathers?\s*Name\s*[=:]\s*([A-Za-z\.\s]+?)(?=House|Age|$)',
            text,
            re.IGNORECASE,
        )
    elif re.search(r'Mothers?\s*Name', text, re.IGNORECASE):
        relation_type = 'Mother'
        rel_match = re.search(
            r'Mothers?\s*Name\s*[=:]\s*([A-Za-z\.\s]+?)(?=House|Age|$)',
            text,
            re.IGNORECASE,
        )
    elif re.search(r'Others?\s*[=:]', text, re.IGNORECASE):
        relation_type = 'Other'
        rel_match = re.search(
            r'Others?\s*[=:]\s*([A-Za-z\.\s]+?)(?=House|Age|$)',
            text,
            re.IGNORECASE,
        )

    if rel_match:
        relative_name = rel_match.group(1).strip()

    house = ''
    house_match = re.search(
        r'House\s*Number\s*[=:]\s*([^\n]+?)(?=\s*Photo|\s*(?:Father|Mother|Husband|Other|Relative|Age|Gender)|$)',
        text,
        re.IGNORECASE,
    )
    if house_match:
        house = re.sub(r'\s+', ' ', house_match.group(1).strip())

    age = extract_age_value(text)
    if not age:
        _debug_age_miss(text, debug_context=debug_context)

    gender = ''
    gender_match = re.search(
        r'Gender\s*[=:]\s*(Male|Female|Third Gender)', text, re.IGNORECASE
    )
    if gender_match:
        gender = gender_match.group(1).capitalize()

    return {
        'Serial Number': serial_number if serial_number is not None else '',
        'EPIC Number': epic or '',
        'Name': name,
        'Relative Name': relative_name,
        'Relation Type': relation_type,
        'House Number': house,
        'Age': age,
        'Gender': gender,
        'raw_text': text,
    }

def find_epic_candidates(text: str):
    """
    Attempt robust EPIC detection:
    Typical EPIC: 10 chars alphanumeric (often 3 letters + 7 digits).
    OCR may insert spaces or non-alpha characters; remove non-alnum and search windows.
    """
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
    candidates = []
    # window scan for length 9-12 to handle OCR variations
    for size in [10, 11, 9, 12]:
        for i in range(0, max(0, len(cleaned) - size + 1)):
            chunk = cleaned[i:i+size]
            if len(chunk) == size:
                # Heuristic: candidate should contain both letters and digits.
                letters = sum(c.isalpha() for c in chunk)
                digits = sum(c.isdigit() for c in chunk)
                # Require a good mix: at least 2 letters and 3 digits
                if letters >= 2 and digits >= 3 and letters + digits >= size * 0.8:
                    candidates.append(chunk)
        if candidates:
            break  # Return best match from preferred size first
    return candidates

def extract_field_by_label(lines, label_keywords):
    """
    Find line containing any of label_keywords and return following tokens or numbers.
    """
    for i, line in enumerate(lines):
        lower = line.lower()
        for kw in label_keywords:
            if kw in lower:
                # try to find digits on same line
                m = re.search(r'(\d{1,3})', line)
                if m:
                    return m.group(1)
                # if next line exists, return digits there
                if i+1 < len(lines):
                    m2 = re.search(r'(\d{1,3})', lines[i+1])
                    if m2:
                        return m2.group(1)
    return None

def extract_name(lines):
    """
    Heuristic: names are usually uppercase or Title case and are short lines with letters.
    We'll pick the first line that looks like a name but not a heading like 'ELECTORAL ROLL'.
    """
    for line in lines:
        s = line.strip()
        if len(s) < 4 or len(s) > 60:
            continue
        # discard obvious headings
        if re.search(r'(electoral|voter|list|page|photo|age|sex|dob|father|husband)', s, re.I):
            continue
        # if line contains many letters and few digits, likely name
        letters = sum(c.isalpha() for c in s)
        digits = sum(c.isdigit() for c in s)
        if letters > digits and any(c.isalpha() for c in s):
            # further: likely contains a space (first + last)
            if ' ' in s or len(s.split()) <= 3:
                return s
    return None

def parse_voter_card(raw_text: str) -> dict:
    """
    Parse OCR'd text and return a record dict:
    { 'name', 'epic', 'age', 'gender', 'dob', 'address' }
    """
    text = normalize_text(raw_text)
    # Keep line-based variants because some fields are easier to detect per-line.
    raw_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    # Preserve dots in names while removing other special chars
    lines = [re.sub(r'[^A-Za-z0-9\s:./-]', '', ln).strip() for ln in raw_lines]

    rec = {
        "name": None,
        "epic": None,
        "age": None,
        "gender": None,
        "dob": None,
        "address": None,
        "raw_text": raw_text
    }

    # EPIC detection
    epics = find_epic_candidates(text)
    rec['epic'] = epics[0] if epics else None

    # Age detection
    age = extract_age_value(raw_text)
    if not age:
        age = extract_field_by_label(lines, ['age', 'aged'])
    if not age:
        _debug_age_miss(raw_text)
    rec['age'] = age

    # DOB detection
    dob_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
    if dob_match:
        rec['dob'] = dob_match.group(1)

    # Gender detection
    if re.search(r'\bmale\b', text, re.I):
        rec['gender'] = 'Male'
    elif re.search(r'\bfemale\b', text, re.I):
        rec['gender'] = 'Female'
    else:
        # short heuristics: 'M' or 'F' preceded by 'sex' or 'gender'
        m = re.search(r'(sex|gender)[:\s]*([MFmf])\b', text)
        if m:
            rec['gender'] = 'Male' if m.group(2).upper() == 'M' else 'Female'

    # Name detection
    name = extract_name(lines)
    rec['name'] = name

    # Address fallback: prefer keyword lines, then long lines as a weak fallback.
    addr_lines = []
    for ln in lines:
        if re.search(r'(house|vill|addr|post|dist|district|pin|pincode|taluk|tehsil|city|state)', ln, re.I):
            addr_lines.append(ln)
    if addr_lines:
        rec['address'] = ' '.join(addr_lines)
    else:
        # fallback: if there are lines longer than 30 chars, join some as address
        long_lines = [ln for ln in lines if len(ln) > 30]
        if long_lines:
            rec['address'] = ' '.join(long_lines[:2])

    return rec