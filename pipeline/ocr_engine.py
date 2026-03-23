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

def image_array_to_text(img_array, lang='eng', oem=3, psm=6):  # OPTIMIZED
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
    for header_pct in [0.20, 0.25, 0.30]:  # OPTIMIZED
        header_h = max(40, int(h * header_pct))  # OPTIMIZED
        header_crop = voter_crop[0:header_h, w // 2:]  # OPTIMIZED

        scale = 3  # OPTIMIZED
        header_large = cv2.resize(  # OPTIMIZED
            header_crop,  # OPTIMIZED
            (header_crop.shape[1] * scale, header_crop.shape[0] * scale),  # OPTIMIZED
            interpolation=cv2.INTER_CUBIC,  # OPTIMIZED
        )  # OPTIMIZED
        header_gray = cv2.cvtColor(header_large, cv2.COLOR_BGR2GRAY)  # OPTIMIZED

        _, otsu = cv2.threshold(  # OPTIMIZED
            header_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU  # OPTIMIZED
        )  # OPTIMIZED
        header_text = pytesseract.image_to_string(  # OPTIMIZED
            otsu, config='--oem 3 --psm 7'  # OPTIMIZED
        ).strip().upper()  # OPTIMIZED

        cleaned = re.sub(r'[^A-Z0-9]', '', header_text)  # OPTIMIZED
        # EPIC candidates are normalized to alnum before 10-char scanning.
        for match in re.finditer(r'[A-Z0-9]{10}', cleaned):  # OPTIMIZED
            fixed = fix_epic_ocr(match.group(0))  # OPTIMIZED
            if fixed:  # OPTIMIZED
                return fixed  # OPTIMIZED

    # Fallback pass with a simpler threshold in case Otsu removes faint characters.
    header_h = max(40, int(h * 0.20))  # OPTIMIZED
    header_crop = voter_crop[0:header_h, w // 2:]  # OPTIMIZED
    scale = 3  # OPTIMIZED
    header_large = cv2.resize(  # OPTIMIZED
        header_crop,  # OPTIMIZED
        (header_crop.shape[1] * scale, header_crop.shape[0] * scale),  # OPTIMIZED
        interpolation=cv2.INTER_CUBIC,  # OPTIMIZED
    )  # OPTIMIZED
    header_gray = cv2.cvtColor(header_large, cv2.COLOR_BGR2GRAY)  # OPTIMIZED
    _, plain = cv2.threshold(header_gray, 127, 255, cv2.THRESH_BINARY)  # OPTIMIZED
    header_text = pytesseract.image_to_string(  # OPTIMIZED
        plain, config='--oem 3 --psm 7'  # OPTIMIZED
    ).strip().upper()  # OPTIMIZED

    cleaned = re.sub(r'[^A-Z0-9]', '', header_text)  # OPTIMIZED
    for match in re.finditer(r'[A-Z0-9]{10}', cleaned):  # OPTIMIZED
        fixed = fix_epic_ocr(match.group(0))  # OPTIMIZED
        if fixed:  # OPTIMIZED
            return fixed  # OPTIMIZED

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

# Useful helper: get OCR with bounding boxes (if you want to inspect confidence)
def image_to_data(img_array, lang='eng', oem=3, psm=3):
    config = f'--oem {oem} --psm {psm}'
    return pytesseract.image_to_data(img_array, lang=lang, config=config, output_type=pytesseract.Output.DICT)