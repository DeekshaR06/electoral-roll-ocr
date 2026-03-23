# pipeline/image_loader.py
import glob
import os
import re
from pdf2image import convert_from_path
from typing import List
import cv2
import pytesseract

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

def pdf_to_images(pdf_path: str, output_folder: str, dpi: int = 200) -> List[str]:  # OPTIMIZED
    """
    Convert PDF pages to images and save in output_folder.
    Returns list of saved image file paths.
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
    print(f"Converted '{pdf_path}' into {len(saved)} page images.")
    return saved

def list_images(folder: str, patterns=None) -> List[str]:
    """
    List image files in folder, sorted.
    Patterns default to jpg/png/jpeg.
    """
    if patterns is None:
        patterns = ["*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff"]
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(folder, p)))
    files = sorted(files)
    return files


def list_voter_pages(folder: str) -> List[str]:
    """
    Return page images sorted numerically by page_<n> naming.
    Falls back to lexical sort if page number is not present.
    """
    pages = glob.glob(os.path.join(folder, "page_*.jpg"))

    def page_key(path: str):
        # Numeric sort avoids page_10 appearing before page_2.
        base = os.path.basename(path)
        match = re.search(r"page_(\d+)", base)
        if match:
            return int(match.group(1))
        return float("inf")

    return sorted(pages, key=page_key)


def _has_voter_card_signals_ocr(image_path: str) -> bool:
    """
    OCR-based heuristic: returns True when page text looks like voter-card content.
    This is intentionally conservative because OCR can be noisy.
    """
    img = cv2.imread(image_path)
    if img is None:
        return True

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Keep OCR cost reasonable for full-page checks.
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
        "EPIC",
        "NAME",
        "HOUSE",
        "NUMBER",
        "AGE",
        "GENDER",
        "FATHER",
        "HUSBAND",
        "MOTHER",
    ]
    hits = sum(1 for kw in keywords if kw in norm)

    # Require multiple field-label hits so cover/index pages are unlikely to pass.
    return hits >= 3


def _filter_boundary_pages_by_ocr(pages: List[str]) -> List[str]:
    """
    Check only boundary pages (first 3 and last page).
    Remove boundary pages that do not look like voter-card pages via OCR signals.
    """
    if not pages:
        return pages

    boundary_indexes = set(range(min(3, len(pages))))
    boundary_indexes.add(len(pages) - 1)

    kept = []
    removed = []

    for idx, page in enumerate(pages):
        if idx in boundary_indexes:
            try:
                if _has_voter_card_signals_ocr(page):
                    kept.append(page)
                else:
                    removed.append(os.path.basename(page))
            except Exception as exc:
                # On OCR check failures, keep page to avoid accidental data loss.
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

    return kept


def get_voter_pages(images_folder: str, pdf_path: str = None, skip_front_pages: int = 0) -> List[str]:
    """
    If pdf_path provided, convert to images (in images_folder) and return list.
    Otherwise just return existing images in images_folder.
    """
    ensure_folder(images_folder)
    if pdf_path:
        # Convert PDF pages to image files before downstream processing.
        pdf_to_images(pdf_path, images_folder)

    pages = list_voter_pages(images_folder)
    if not pages:
        pages = list_images(images_folder)

    # For PDF input, avoid fixed front-page dropping and use OCR checks only on
    # the first 3 pages and last page.
    if pdf_path:
        pages = _filter_boundary_pages_by_ocr(pages)

    if skip_front_pages > 0:
        print(
            "skip_front_pages is deprecated for PDF flow; boundary OCR filtering is used instead."
        )

    return pages