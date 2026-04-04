# pipeline/parser.py
"""
Generic voter-card field parser.
 
Design goals
────────────
• Work correctly on ANY electoral-roll PDF of this format (not just one file).
• Achieve <5% missing values across all eight fields.
• Robust to OCR noise: spacing, apostrophes in labels, 'House No.' vs
  'House Number', garbled chars, interleaved layout text (Photo/Available),
  and normalised (newline-collapsed) text.
 
Key strategies
──────────────
1. Broad label patterns   – catch variants (Father/Father's/Fathers,
                            House No./H.No/House Number, Others/Other, …)
2. \\S anchor on values    – do NOT require first captured char to be alpha;
                            strip noise after capture instead of before.
3. Explicit noise removal – 'Photo' / 'Available' stripped from every
                            captured value, not only used as lookahead stops.
4. Neighbor inference     – missing house numbers borrowed from adjacent
                            records in the same household block (called by
                            main.py after all cards parsed).
5. Valid-card guard       – non-voter pages (cover, maps, photos, summary)
                            rejected before parsing → zero ghost rows.
"""
 
import re
import os
 
 
# ── OCR character correction map ──────────────────────────────────────────────
 
_OCR_DIGIT_MAP = {
    'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8',
    'Z': '2', 'G': '6', 'T': '7', 'A': '4', '?': '7',
    '§': '5', '%': '8',
}
 
# Layout words that appear in the photo column of every voter card.
# They must never be treated as field values.
_LAYOUT_RE = re.compile(r'\b(?:Photo|Available)\b', re.IGNORECASE)
_TRAIL_RE   = re.compile(r'[\-–—\s]+$')
 
# Stop pattern: lookahead that prevents capturing into the next field or
# layout word. Used in all value capture groups.
_STOP = (
    r'(?=\s*(?:'
    r"Husband'?s?\s*Name"
    r"|Father'?s?\s*Name"
    r"|Mother'?s?\s*Name"
    r'|Others?\s*[=:]'
    r'|House\s*N|H\.?\s*No'
    r'|Age\s*[=:]|Gender\s*[=:]'
    r'|Photo|Available'
    r')|$)'
)
 
# Relation label patterns in priority order - enhanced to handle more variations
_RELATION_PATTERNS = [
    ('Husband', r"Husband'?s?\s*Names?\s*[=:\s]+"),
    ('Father',  r"Father'?s?\s*Names?\s*[=:\s]+"),
    ('Mother',  r"Mother'?s?\s*Names?\s*[=:\s]+"),
    ('Other',   r"Others?\s*[=:\s]+"),
]

# House label: covers House Number, House No., H.No, H.No.
_HOUSE_LABEL_RE = re.compile(
    r'(?:House\s*N(?:o\.?|umber)[\.\s]*|H\.?\s*No\.?\s*)\s*[=:\s]+',
    re.IGNORECASE,
)

_EMPTY_HOUSE_VALUES = {'', '-', '–', '—', '.', 'nil', 'none', 'na', 'n/a'}


# ── Helper: clean a captured string ──────────────────────────────────────────

def _clean(value: str) -> str:
    """Remove layout noise, trailing dashes, collapse whitespace."""
    if not value:
        return ''
    value = _LAYOUT_RE.sub('', value)
    value = _TRAIL_RE.sub('', value)
    # Remove leading/trailing colons and other punctuation that can appear from OCR noise
    value = value.lstrip(':-–—').rstrip(':-–—')
    return re.sub(r'\s+', ' ', value).strip()
 
def _extract_name(text: str) -> str:
    """
    Extract voter's own name.
    (?<!\\w) prevents matching 'Fathers Name', 'Husbands Name' etc.
    Value ends at the next relation label, house label or layout word.
    
    Enhanced to handle more OCR variations while maintaining performance.
    """
    # Primary pattern: strict name extraction
    m = re.search(
        r'(?<!\w)Name\s*[=:]\s*(\S[^\n=:]*?)' + _STOP,
        text, re.IGNORECASE,
    )
    if m:
        val = _clean(m.group(1))
        if len(val) >= 2:
            return val
    
    # Fallback: Less strict - handle variations with OCR noise
    m = re.search(
        r'(?<!\w)Name\s*[:=\-\.+]?\s*(\S+[^\n=:]*?)(?=[\n]|$|(?:Husband|Father|Mother|House|Age|Gender))',
        text, re.IGNORECASE,
    )
    if m:
        val = _clean(m.group(1))
        if len(val) >= 2:
            return val
    
    return ''
 
 
def _extract_relation(text: str):
    """
    Return (relation_type: str, relative_name: str).
 
    Handles label variants:
      Husbands Name / Husband's Name / Husband Name
      Fathers Name  / Father's Name  / Father Name
      Mothers Name  / Mother's Name  / Mother Name
      Others        / Other
 
    Uses \\S as value anchor (not [A-Za-z]) so OCR noise before a name
    (e.g. a leading colon or dash) doesn't cause a miss — _clean() removes it.
    """
    for rel_type, label_pat in _RELATION_PATTERNS:
        m = re.search(label_pat + r'(\S[^\n=:]*?)' + _STOP, text, re.IGNORECASE)
        if m:
            val = _clean(m.group(1))
            if len(val) >= 2:  # Must be at least 2 chars for a name
                return rel_type, val
    
    # Fallback: try less restrictive patterns for Husband specifically (most common)
    m = re.search(r"(?:Husband|H[Ua]sband)'?s?\s*(?:Name)?\s*[:=\s]+(\S[^\n=:]{1,}?)(?=\n|$|(?:Father|Mother|House|Age|Gender))", 
                 text, re.IGNORECASE)
    if m:
        val = _clean(m.group(1))
        if len(val) >= 2:
            return 'Husband', val
    
    return '', ''


def _extract_house(text: str) -> str:
    """
    Extract house / door number.

    Two-stage approach:
      1. Find the label (House Number / House No. / H.No) — broad match.
      2. Capture text from label end up to the next newline; then strip
         Photo/Available tokens that bleed in from the right card column.

    Using [^\n] as the raw capture (not [A-Za-z0-9] anchor) fixes the
    previous bug where 'Photo'/'Available' were captured as the house value
    when the field was genuinely blank — they are now stripped afterwards.

    Treating the result as empty when it equals a lone dash / dot / layout
    word handles the real 'House Number : -' entries seen in the PDF.
    """
    m = _HOUSE_LABEL_RE.search(text)
    if not m:
        return ''
    rest  = text[m.end():]
    val_m = re.match(r'([^\n]*?)(?=\s*(?:Photo|Age|Gender)|$)', rest, re.IGNORECASE)
    if not val_m:
        return ''
    val = _clean(val_m.group(1))
    return '' if val.lower() in _EMPTY_HOUSE_VALUES else val
 
 
def _extract_gender(text: str) -> str:
    """
    Extract gender.
    Primary:  'Gender : Male / Female' labelled field with flexible separators.
    Fallback: standalone \\bMale\\b / \\bFemale\\b anywhere in the card —
              handles cards where the Gender label is faint or mis-OCR'd.
    """
    # More flexible separator handling
    m = re.search(r'Gender\s*[:=\-\.+]?\s*(Male|Female|Third\s*Gender)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().title()
    
    # Fallback: Standalone gender keywords
    fb = re.search(r'\b(Male|Female)\b', text, re.IGNORECASE)
    return fb.group(1).capitalize() if fb else ''
 
 
def extract_age_value(text: str) -> str:
    """
    Extract age from noisy OCR text.
    Applies character-substitution map before digit parsing.
    Accepts ages 18–125; corrects common artifact (e.g. '164' → 64).
    """
    if not text:
        return ''
    normalized = text.replace('|', ':')
    patterns = [
        r'\b(?:age|aged|aqe|a9e|ag[e6])\b\s*[:;=\-]?\s*([0-9OILSBZGTA?§%]{1,3})(?=\s|$|[,:;])',
        r'\b(?:age|aged|aqe|a9e|ag[e6])\D{0,8}([0-9OILSBZGTA?§%]{1,3})(?=\s|$|[,:;])',
        r'([0-9OILSBZGTA?§%]{1,3})\s*(?:years?|yrs?)\b',
    ]
 
    def _fix(token):
        cleaned = ''.join(_OCR_DIGIT_MAP.get(c.upper(), c) for c in token
                          if c.isalnum() or c in {'?', '§', '%'})
        digits = re.sub(r'\D', '', cleaned)
        if not digits:
            return None
        val = int(digits)
        if 18 <= val <= 125:
            return val
        if len(digits) == 3 and digits.startswith('1'):
            tail = int(digits[1:])
            if 18 <= tail <= 99:
                return tail
        return None
 
    for pat in patterns:
        for m in re.finditer(pat, normalized, re.IGNORECASE):
            v = _fix(m.group(1))
            if v is not None:
                return str(v)
    return ''
 
 
def _debug_age_miss(text: str, debug_context: str = '') -> None:
    if os.getenv('OCR_DEBUG_AGE', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
        return
    compact = re.sub(r'\s+', ' ', text or '').strip()
    hints = []
    for pat in [r'\b(age|aged)\b[^\n]{0,25}', r'\b(\d{1,3})\s*(years?|yrs?)\b']:
        for m in re.finditer(pat, text or '', re.IGNORECASE):
            s = m.group(0).replace('\n', ' ').strip()
            if s not in hints:
                hints.append(s)
    print('[AGE-DEBUG] Missing age')
    if debug_context:
        print(f'[AGE-DEBUG] Context: {debug_context}')
    if hints:
        print(f"[AGE-DEBUG] Hints: {' | '.join(hints[:3])}")
    print(f"[AGE-DEBUG] Text: {compact[:200]}")
 
 
# ── Valid-card guard ──────────────────────────────────────────────────────────
 
def _is_valid_card(text: str, epic: str = '') -> bool:
    """
    Reject non-voter-card OCR blocks (cover page, maps, photos, summary).

    Requires 'Name :' label AND at least one of:
      • 'Age :'   label
      • 'Gender :' label
      • A pattern matching an EPIC number in text OR epic parameter

    This check is intentionally broad so it works across different PDF
    templates from different constituencies / years.
    """
    has_name   = bool(re.search(r'(?<!\w)Name\s*[=:]', text, re.IGNORECASE))
    has_age    = bool(re.search(r'\bAge\s*[=:]', text, re.IGNORECASE))
    has_gender = bool(re.search(r'\bGender\s*[=:]', text, re.IGNORECASE))
    has_epic   = bool(re.search(r'\b[A-Z]{2,4}\d{6,8}\b', text)) or bool(epic)
    return has_name and (has_age or has_gender or has_epic)
 
 
def normalize_text(text: str) -> str:
    """Collapse all whitespace to single spaces (utility, kept for compat)."""
    return re.sub(r'\s+', ' ', text).strip()
 
 
# ── Main entry point ──────────────────────────────────────────────────────────
 
def parse_voter_fields(
    raw_text: str,
    serial_number: int = None,
    epic: str = '',
    debug_context: str = '',
) -> 'dict | None':
    """
    Parse a single voter card's OCR text into a structured record.
 
    Returns None if the block is not a genuine voter card.
 
    IMPORTANT: raw_text (newlines intact) is passed directly to extractors.
    normalize_text() is NOT applied before extraction because collapsing
    newlines breaks the [^\\n]-based house-number capture.
    """
    text = raw_text or ''
 
    if not _is_valid_card(text, epic=epic):
        return None
 
    name                         = _extract_name(text)
    relation_type, relative_name = _extract_relation(text)
    house                        = _extract_house(text)
    age                          = extract_age_value(text)
    gender                       = _extract_gender(text)
 
    if not age:
        _debug_age_miss(text, debug_context=debug_context)
 
    return {
        'Serial Number': serial_number if serial_number is not None else '',
        'EPIC Number':   epic or '',
        'Name':          name,
        'Relative Name': relative_name,
        'Relation Type': relation_type,
        'House Number':  house,
        'Age':           age,
        'Gender':        gender,
        'Record Type':   'Voter',
        'raw_text':      text,
    }
 
 
# ── Post-processing: neighbor inference ───────────────────────────────────────
 
def infer_missing_houses(records: list) -> list:
    """
    Fill blank house numbers using adjacent records in the same household.
 
    Electoral rolls list household members consecutively; neighbours almost
    always share the same house number. This is the final fallback called
    by main.py after all cards have been parsed.
 
    Rules (priority order):
      1. Prev AND next both have the same value → use it.
      2. Only prev has a value → use it.
      3. Only next has a value → use it.
      4. Neither → leave blank.
 
    Only 'simple' house values (short alphanumeric strings) are propagated
    to avoid spreading complex addresses across section boundaries.
    """
    def _ok(val):
        if not val:
            return False
        return bool(re.match(r'^[A-Za-z0-9][A-Za-z0-9\s\.\,\-\/]{0,20}$', str(val).strip()))
 
    n = len(records)
    for i, rec in enumerate(records):
        if rec.get('House Number'):
            continue
        prev = records[i - 1].get('House Number', '') if i > 0     else ''
        nxt  = records[i + 1].get('House Number', '') if i < n - 1 else ''
 
        if _ok(prev) and _ok(nxt) and str(prev).strip() == str(nxt).strip():
            rec['House Number'] = prev
        elif _ok(prev):
            rec['House Number'] = prev
        elif _ok(nxt):
            rec['House Number'] = nxt
 
    return records
 
 
# ── Utility / legacy helpers ──────────────────────────────────────────────────
 
def find_epic_candidates(text: str) -> list:
    """Scan text for 10-char EPIC candidates (≥2 letters, ≥3 digits)."""
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
    out = []
    for i in range(max(0, len(cleaned) - 9)):
        chunk = cleaned[i:i + 10]
        if (len(chunk) == 10
                and sum(c.isalpha() for c in chunk) >= 2
                and sum(c.isdigit() for c in chunk) >= 3):
            out.append(chunk)
    return out
 
 
def extract_field_by_label(lines: list, label_keywords: list) -> 'str | None':
    for i, line in enumerate(lines):
        lower = line.lower()
        for kw in label_keywords:
            if kw in lower:
                m = re.search(r'(\d{1,3})', line)
                if m:
                    return m.group(1)
                if i + 1 < len(lines):
                    m2 = re.search(r'(\d{1,3})', lines[i + 1])
                    if m2:
                        return m2.group(1)
    return None
 
 
def extract_name(lines: list) -> 'str | None':
    """Heuristic: first short mostly-letter line that is not a heading."""
    for line in lines:
        s = line.strip()
        if not (4 <= len(s) <= 60):
            continue
        if re.search(
            r'(electoral|voter|list|page|photo|age|sex|dob|father|husband|available)',
            s, re.I,
        ):
            continue
        if sum(c.isalpha() for c in s) > sum(c.isdigit() for c in s):
            if ' ' in s or len(s.split()) <= 3:
                return s
    return None
 
 
def parse_voter_card(raw_text: str) -> dict:
    """Legacy entry-point for backward compatibility."""
    text  = normalize_text(raw_text)
    lines = [re.sub(r'[^A-Za-z0-9\s:/-]', '', ln).strip()
             for ln in raw_text.splitlines() if ln.strip()]
    rec = {
        'name': None, 'epic': None, 'age': None,
        'gender': None, 'dob': None, 'address': None,
        'raw_text': raw_text,
    }
    epics = find_epic_candidates(text)
    rec['epic'] = epics[0] if epics else None
    age = extract_age_value(raw_text) or extract_field_by_label(lines, ['age', 'aged'])
    if not age:
        _debug_age_miss(raw_text)
    rec['age']    = age
    dob_m = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
    if dob_m:
        rec['dob'] = dob_m.group(1)
    rec['gender'] = _extract_gender(text)
    rec['name']   = extract_name(lines)
    addr = [ln for ln in lines
            if re.search(r'(house|vill|addr|post|dist|pin|taluk|city|state)', ln, re.I)]
    rec['address'] = ' '.join(addr) if addr else ' '.join(
        ln for ln in lines if len(ln) > 30
    )
    return rec

# -- Voter Additions / Amendments Detection --------

def detect_additions_section(text: str) -> bool:
    additions_keywords = [
        'ADDITION', 'ADDITIONS',
        'AMENDMENT', 'AMENDMENTS', 'AMENDED',
        'CORRECTION', 'CORRECTED', 'CORRECTIONS',
        'NEW ELECTOR', 'NEW VOTER', 'NEW REGISTR', 'NEWLY REGISTERED',
        'DELETION', 'DELETIONS', 'DELETED', 'REMOVAL', 'REMOVED', 'STRUCK OFF',
        'SUPPLEMENTARY', 'SUPPLEMENT',
        'PART A', 'PART B', 'PART C',
        'CHANGES', 'MODIFIED', 'MODIFIED ENTRIES',
    ]
    text_upper = text.upper()
    return any(keyword in text_upper for keyword in additions_keywords)


def parse_additions_fields(text: str, epic: str = '', addition_type: str = 'Amendment') -> dict:
    base_record = parse_voter_fields(text, epic=epic)
    if base_record is None:
        return None
    
    if 'NEW' in text.upper():
        base_record['Record Type'] = 'New'
    elif 'DELETE' in text.upper() or 'STRUCK' in text.upper():
        base_record['Record Type'] = 'Deletion'
    elif 'AMENDMENT' in text.upper() or 'CORRECTION' in text.upper():
        base_record['Record Type'] = 'Amendment'
    else:
        base_record['Record Type'] = addition_type
    
    return base_record
