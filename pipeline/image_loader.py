# pipeline/image_loader.py
import glob
import os
import re
from pdf2image import convert_from_path
from typing import List

def ensure_folder(path: str):
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
        base = os.path.basename(path)
        match = re.search(r"page_(\d+)", base)
        if match:
            return int(match.group(1))
        return float("inf")

    return sorted(pages, key=page_key)


def get_voter_pages(images_folder: str, pdf_path: str = None, skip_front_pages: int = 2) -> List[str]:
    """
    If pdf_path provided, convert to images (in images_folder) and return list.
    Otherwise just return existing images in images_folder.
    """
    ensure_folder(images_folder)
    if pdf_path:
        # convert pdf pages to images into images_folder
        pdf_to_images(pdf_path, images_folder)

    pages = list_voter_pages(images_folder)
    if not pages:
        pages = list_images(images_folder)

    if skip_front_pages > 0 and len(pages) > skip_front_pages:
        pages = pages[skip_front_pages:]
    elif skip_front_pages > 0 and len(pages) <= skip_front_pages:
        print(
            f"Requested skip_front_pages={skip_front_pages}, but only {len(pages)} page(s) found. Processing all pages."
        )

    return pages