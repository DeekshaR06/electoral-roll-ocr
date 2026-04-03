# pipeline/ocr_engine.py
import pytesseract
from PIL import Image
import numpy as np
import cv2
import re

# If Tesseract is not on PATH set it here (Windows example):
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def image_to_text_pil(pil_image, lang='eng', oem=3, psm=3):
    """Run OCR on a PIL image with configurable Tesseract engine/page modes."""
    config = f'--oem {oem} --psm {psm}'
    return pytesseract.image_to_string(pil_image, lang=lang, config=config)

def image_path_to_text(img_path, lang='eng', oem=3, psm=3):
    pil = Image.open(img_path)
    return image_to_text_pil(pil, lang=lang, oem=oem, psm=psm)

def image_array_to_text(img_array, lang='eng', oem=3, psm=6):
    """OCR helper that accepts either grayscale or BGR numpy images."""
    # Convert OpenCV BGR arrays to RGB before creating PIL image.
    if len(img_array.shape) == 2:
        pil = Image.fromarray(img_array)
    else:
        pil = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
    return image_to_text_pil(pil, lang=lang, oem=oem, psm=psm)


def fix_epic_ocr(raw):
    """Fix common OCR misreads. EPIC must be exactly 3 letters + 7 digits."""
    if not raw or len(raw) < 10:
        return None

    raw = raw.upper().strip()
    # Different correction maps are used for EPIC prefix letters vs suffix digits.
    letter_fixes = {'0': 'O', '1': 'I', '5': 'S', '8': 'B'}
    digit_fixes = {
        'O': '0', 'I': '1', 'S': '5', 'B': '8',
        'A': '4', 'G': '6', 'Z': '2', 'T': '7',
        'N': '0', 'U': '0', 'D': '0', 'Q': '0'
    }

    letters = ''.join(letter_fixes.get(c, c) for c in raw[:3])
    digits = ''.join(digit_fixes.get(c, c) for c in raw[3:10])
    result = letters + digits

    if re.match(r'^[A-Z]{3}\d{7}$', result):
        return result
    return None


def extract_epic_from_crop(voter_crop):
    """
    Extract EPIC number from top-right header area of a voter-card crop.
    """
    h, w = voter_crop.shape[:2]

    # Try multiple header heights because different PDFs use different card templates.
    for header_pct in [0.20, 0.25, 0.30]:
        header_h = max(40, int(h * header_pct))
        header_crop = voter_crop[0:header_h, w // 2:]

        scale = 3
        header_large = cv2.resize(
            header_crop,
            (header_crop.shape[1] * scale, header_crop.shape[0] * scale),
            interpolation=cv2.INTER_CUBIC,
        )
        header_gray = cv2.cvtColor(header_large, cv2.COLOR_BGR2GRAY)

        _, otsu = cv2.threshold(
            header_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        header_text = pytesseract.image_to_string(
            otsu, config='--oem 3 --psm 7'
        ).strip().upper()

        cleaned = re.sub(r'[^A-Z0-9]', '', header_text)
        # EPIC candidates are normalized to alnum before 10-char scanning.
        for match in re.finditer(r'[A-Z0-9]{10}', cleaned):
            fixed = fix_epic_ocr(match.group(0))
            if fixed:
                return fixed

    # Fallback pass with a simpler threshold in case Otsu removes faint characters.
    header_h = max(40, int(h * 0.20))
    header_crop = voter_crop[0:header_h, w // 2:]
    scale = 3
    header_large = cv2.resize(
        header_crop,
        (header_crop.shape[1] * scale, header_crop.shape[0] * scale),
        interpolation=cv2.INTER_CUBIC,
    )
    header_gray = cv2.cvtColor(header_large, cv2.COLOR_BGR2GRAY)
    _, plain = cv2.threshold(header_gray, 127, 255, cv2.THRESH_BINARY)
    header_text = pytesseract.image_to_string(
        plain, config='--oem 3 --psm 7'
    ).strip().upper()

    cleaned = re.sub(r'[^A-Z0-9]', '', header_text)
    for match in re.finditer(r'[A-Z0-9]{10}', cleaned):
        fixed = fix_epic_ocr(match.group(0))
        if fixed:
            return fixed

    return None


def extract_epic_fallback_from_text(text):
    """Fallback EPIC detection from OCR text first line."""
    first_line = text.split('\n')[0] if text else ''
    cleaned = re.sub(r'[^A-Z0-9]', '', first_line.upper())
    for match in re.finditer(r'[A-Z0-9]{10}', cleaned):
        fixed = fix_epic_ocr(match.group(0))
        if fixed:
            return fixed
    return None


def extract_polling_station_metadata(text: str) -> dict:
    """
    Extract polling station metadata (number, name, address, block, ward)
    from OCR text of the cover page.
    
    Designed to handle OCR noise and variations in the electoral roll cover page layout.
    Returns dict with keys: polling_station_number, polling_station_name,
    polling_station_address, block, ward (empty string if not found).
    """
    if not text:
        return {
            'polling_station_number': '',
            'polling_station_name': '',
            'polling_station_address': '',
            'block': '',
            'ward': '',
        }
    
    metadata = {
        'polling_station_number': '',
        'polling_station_name': '',
        'polling_station_address': '',
        'block': '',
        'ward': '',
    }
    
    # Normalize text: uppercase for matching, but preserve original case in captures
    text_upper = text.upper()
    text_lines = text.split('\n')
    
    # ─ Extract Polling Station Number and Name ─
    # The OCR text often has station number and name like: "2 - St. Dominic Savio..." 
    # Pattern accounts for variations in layout and line breaks.
    
    # First, try to find the standard pattern
    ps_pattern = r"No\.\s+and\s+Name\s+of\s+Polling\s+Station\s*:(?:\s|\n)*(\d+)\s*-\s*(.+?)(?=\n\n|Address|Number\s+of|$)"
    ps_match = re.search(ps_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if not ps_match:
        # Fallback: look for digit-dash-name pattern anywhere after "Polling Station" label
        ps_pattern2 = r"Polling\s+Station\s*:.*?\n.*?(\d+)\s*-\s*(.+?)(?=\n.*?(?:Number|Address)|$)"
        ps_match = re.search(ps_pattern2, text, re.IGNORECASE | re.DOTALL)
    
    if ps_match:
        metadata['polling_station_number'] = ps_match.group(1).strip()
        ps_name = ps_match.group(2).strip()
        # Clean up: remove anything with an opening paren (e.g., "(Western side-front end)")
        ps_name = ps_name.split('(')[0].strip()
        # Remove trailing junk: "Number of...", "Type of...", etc.
        ps_name = re.sub(r'\s+(?:Number|Type|Auxiliary).*$', '', ps_name, flags=re.IGNORECASE).strip()
        # Clean up extra whitespace
        ps_name = re.sub(r'\s+', ' ', ps_name).strip()
        metadata['polling_station_name'] = ps_name
    
    # ─ Extract Address of Polling Station ─
    # Pattern: "Address of Polling Station :" followed by multi-line address
    addr_pattern = r"Address\s+of\s+Polling\s+Station\s*:\s*(.+?)(?=\n\n|(?:Number|Type)\s+of|$)"
    addr_match = re.search(addr_pattern, text, re.IGNORECASE | re.DOTALL)
    if addr_match:
        addr_text = addr_match.group(1).strip()
        # Clean up: collapse multiple spaces, remove excessive newlines
        addr_text = ' '.join(addr_text.split())
        # Remove OCR noise at end: "4." or other single digits, "NUMBER OF ELECTORS", etc.
        addr_text = re.sub(r'\s+\d+\s*\.?\s*$', '', addr_text)
        addr_text = re.sub(r'\s+(?:NUMBER|TYPE|Auxiliary)\s+.*$', '', addr_text, flags=re.IGNORECASE)
        metadata['polling_station_address'] = addr_text.strip()
    
    # ─ Extract Block ─
    # Pattern: "Block\s*:\s*<value>" (often in section details or right column)
    block_pattern = r"Block\s*:\s*([^\n]+)"
    block_match = re.search(block_pattern, text, re.IGNORECASE)
    if block_match:
        block_val = block_match.group(1).strip()
        metadata['block'] = block_val
    
    # ─ Extract Ward ─
    # Pattern: "Ward\s*:\s*<value>" or "[Ww]ard" if it appears in the text
    ward_pattern = r"Ward\s*:\s*([^\n]+)"
    ward_match = re.search(ward_pattern, text, re.IGNORECASE)
    if ward_match:
        ward_val = ward_match.group(1).strip()
        metadata['ward'] = ward_val
    
    return metadata


# Useful helper: get OCR with bounding boxes (if you want to inspect confidence)
def image_to_data(img_array, lang='eng', oem=3, psm=3):
    config = f'--oem {oem} --psm {psm}'
    return pytesseract.image_to_data(img_array, lang=lang, config=config, output_type=pytesseract.Output.DICT)