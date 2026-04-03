# pipeline/image_loader.py
import glob
import os
import re
from pdf2image import convert_from_path
from typing import List, Dict, Tuple
import cv2
import pytesseract
from pipeline.ocr_engine import extract_polling_station_metadata
 
 
def ensure_folder(path: str):
    """Create folder if missing."""
    os.makedirs(path, exist_ok=True)
 
 
def clear_generated_pages(output_folder: str) -> int:
    """Remove previously generated page_*.jpg files to avoid mixing PDFs."""
    pattern = os.path.join(output_folder, "page_*.jpg")
    files = glob.glob(pattern)
    for path in files:
        os.remove(path)
    return len(files)
 
 
def pdf_to_images(pdf_path: str, output_folder: str, dpi: int = 300) -> List[str]:
    """
    Convert PDF pages to images and save in output_folder.
    Returns list of saved image file paths.
 
    FIX: raised default DPI from 200 → 300.
    Electoral roll cards use small 8-10pt text. At 200 DPI many characters
    are under 10px tall which causes Tesseract to misread them (e.g. 'rn'→'m',
    '6'→'b', etc.). 300 DPI is the minimum recommended for reliable OCR and
    reduces character-level errors significantly.
    """
    ensure_folder(output_folder)
    removed = clear_generated_pages(output_folder)
    if removed:
        print(f"Cleared {removed} old generated page images from '{output_folder}'.")
 
    images = convert_from_path(pdf_path, dpi=dpi)
    saved = []
    for i, img in enumerate(images, start=1):
        fname = os.path.join(output_folder, f"page_{i:03d}.jpg")
        img.save(fname, "JPEG")
        saved.append(fname)
    print(f"Converted '{pdf_path}' into {len(saved)} page images at {dpi} DPI.")
    return saved
 
 
def list_images(folder: str, patterns=None) -> List[str]:
    """List image files in folder, sorted."""
    if patterns is None:
        patterns = ["*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff"]
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(folder, p)))
    return sorted(files)
 
 
def list_voter_pages(folder: str) -> List[str]:
    """
    Return page images sorted numerically by page_<n> naming.
    Falls back to lexical sort if page number is not present.
    """
    pages = glob.glob(os.path.join(folder, "page_*.jpg"))
 
    def page_key(path: str):
        base = os.path.basename(path)
        match = re.search(r"page_(\d+)", base)
        if match:
            return int(match.group(1))
        return float("inf")
 
    return sorted(pages, key=page_key)
 
 
def _has_voter_card_signals_ocr(image_path: str) -> bool:
    """
    OCR-based heuristic: returns True when page text looks like voter-card content.
 
    FIX: raised hit threshold from 3 → 5 and added hard requirement for both
    AGE and GENDER to be present.
 
    The old threshold of 3 was too low — the PDF cover page contains words like
    NAME, NUMBER, AGE, GENDER, FATHER, HUSBAND in its summary table, easily
    scoring 3+ hits and slipping through the filter. This caused the cover page
    to be treated as a data page, producing ghost rows in the output.
 
    A genuine voter-card page reliably contains all field labels (Name, House,
    Age, Gender, Father/Husband) across multiple cards. Requiring 5+ hits AND
    both AGE + GENDER makes it practically impossible for cover/summary pages
    to pass while still catching real data pages.
    """
    img = cv2.imread(image_path)
    if img is None:
        return True  # Keep on read failure to avoid accidental data loss.
 
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    max_dim = 1600
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        gray = cv2.resize(
            gray,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )
 
    text = pytesseract.image_to_string(gray, config="--oem 3 --psm 6")
    norm = text.upper()
 
    keywords = [
        "EPIC", "NAME", "HOUSE", "NUMBER", "AGE",
        "GENDER", "FATHER", "HUSBAND", "MOTHER",
    ]
    hits = sum(1 for kw in keywords if kw in norm)
 
    # Require 5+ keyword hits AND both AGE and GENDER must be present.
    # This reliably excludes cover pages, map pages, and photo pages.
    return hits >= 5 and "AGE" in norm and "GENDER" in norm
 
 
def _filter_boundary_pages_by_ocr(pages: List[str]) -> Tuple[List[str], Dict]:
    """
    Check only boundary pages (first 3 and last page).
    Remove boundary pages that do not look like voter-card pages via OCR signals.
    
    Also extracts polling station metadata from the first page (cover page) if detected as non-data.
    Returns tuple: (kept_pages, metadata_dict)
    """
    if not pages:
        return pages, {
            'polling_station_number': '',
            'polling_station_name': '',
            'polling_station_address': '',
            'block': '',
            'ward': '',
        }
 
    boundary_indexes = set(range(min(3, len(pages))))
    boundary_indexes.add(len(pages) - 1)
 
    kept = []
    removed = []
    metadata = {
        'polling_station_number': '',
        'polling_station_name': '',
        'polling_station_address': '',
        'block': '',
        'ward': '',
    }
 
    for idx, page in enumerate(pages):
        if idx in boundary_indexes:
            try:
                is_data_page = _has_voter_card_signals_ocr(page)
                if is_data_page:
                    kept.append(page)
                else:
                    removed.append(os.path.basename(page))
                    # Extract metadata from first non-data page (typically cover page)
                    if idx == 0 and not metadata['polling_station_number']:
                        img = cv2.imread(page)
                        if img is not None:
                            try:
                                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                                h, w = gray.shape[:2]
                                max_dim = 1600
                                if max(h, w) > max_dim:
                                    scale = max_dim / float(max(h, w))
                                    gray = cv2.resize(
                                        gray,
                                        (int(w * scale), int(h * scale)),
                                        interpolation=cv2.INTER_AREA,
                                    )
                                ocr_text = pytesseract.image_to_string(gray, config="--oem 3 --psm 6")
                                metadata = extract_polling_station_metadata(ocr_text)
                            except Exception as exc:
                                print(f"Metadata extraction failed for '{page}': {exc}")
            except Exception as exc:
                print(
                    f"Boundary OCR check failed for '{page}' ({exc}). Keeping page."
                )
                kept.append(page)
        else:
            kept.append(page)
 
    if removed:
        print(
            "Removed non-voter boundary pages via OCR check: "
            + ", ".join(removed)
        )
 
    return kept, metadata
 
 
def get_voter_pages(
    images_folder: str,
    pdf_path: str = None,
    skip_front_pages: int = 0,
) -> Tuple[List[str], Dict]:
    """
    If pdf_path provided, convert to images (in images_folder) and return list.
    Otherwise just return existing images in images_folder.
    
    Returns tuple: (pages, metadata_dict)
    """
    ensure_folder(images_folder)
    metadata = {
        'polling_station_number': '',
        'polling_station_name': '',
        'polling_station_address': '',
        'block': '',
        'ward': '',
    }
    
    if pdf_path:
        pdf_to_images(pdf_path, images_folder)
 
    pages = list_voter_pages(images_folder)
    if not pages:
        pages = list_images(images_folder)
 
    if pdf_path:
        pages, metadata = _filter_boundary_pages_by_ocr(pages)
 
    if skip_front_pages > 0:
        print(
            "skip_front_pages is deprecated for PDF flow; "
            "boundary OCR filtering is used instead."
        )
 
    return pages, metadata