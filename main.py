# main.py
import os
import shutil
import tempfile
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page
from pipeline.ocr_engine import (
    image_array_to_text,
    extract_epic_from_crop,
    extract_epic_fallback_from_text,
)
from pipeline.parser import parse_voter_fields
from pipeline.exporter import save_to_formatted_excel
import cv2
from tqdm import tqdm
import pytesseract
 
IMAGES_DIR = "images"
OUTPUT_DIR = "output"
PDF_SAMPLE = "sample_data.pdf"
 
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
 
 

def process_additions_page(args):
    """
    Process a page looking for voter additions/amendments on ALL boxes.
    Returns (page_idx, records, 'additions') with 'Record Type' field added.
    Scans entire page for amendment indicators, not just bottom portion.
    """
    page_path, page_idx = args
    additions = []
    try:
        from pipeline.parser import detect_additions_section, parse_additions_fields
        
        img = cv2.imread(page_path)
        if img is None:
            return page_idx, [], 'additions'
        
        # Get full page text to check if this is an amendments page
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        full_text = pytesseract.image_to_string(img_gray, config='--oem 3 --psm 6')
        
        # If page contains addition keywords, process ALL boxes on this page
        is_amendments_page = detect_additions_section(full_text)
        
        if not is_amendments_page:
            return page_idx, [], 'additions'
        
        # Process ALL boxes on this page (not just bottom portion)
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        
        for x, y, w, h_box in boxes:
            try:
                voter_crop = img[y:y + h_box, x:x + w]
                text = image_array_to_text(voter_crop, psm=6)
                
                # Check if this box has amendment indicators
                if not detect_additions_section(text):
                    # Even if this box doesn't have keywords, parse it as amendment 
                    # since we're on an amendments page - let the parser decide
                    # by checking the full page context
                    pass
                
                epic = extract_epic_from_crop(voter_crop)
                if not epic:
                    epic = extract_epic_fallback_from_text(text)
                
                # Parse as additions field - parser will detect type (New/Amendment/Deletion)
                rec = parse_additions_fields(text, epic=epic)
                if rec is not None:
                    key_fields = [
                        rec.get('EPIC Number', ''),
                        rec.get('Name', ''),
                        rec.get('House Number', ''),
                    ]
                    if any(str(v).strip() for v in key_fields):
                        rec['source_file'] = os.path.basename(page_path)
                        additions.append(rec)
            except Exception:
                pass
    except Exception:
        pass
    
    return page_idx, additions, 'additions'


def process_single_page(args):
    """Process one page and return list of voter records without serial numbers."""
    page_path, page_idx = args
    page_records = []
    try:
        img = cv2.imread(page_path)
        if img is None:
            print(f"Warning: could not read {page_path}")
            return page_idx, [], 'voter'
 
        # FIX 7: raised min_height 120→150 so section-header divider lines
        # are no longer detected as voter card boxes.
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        for x, y, w, h in boxes:
            try:
                voter_crop = img[y:y + h, x:x + w]
                text = image_array_to_text(voter_crop, psm=6)
                epic = extract_epic_from_crop(voter_crop)
                if not epic:
                    epic = extract_epic_fallback_from_text(text)
                debug_context = (
                    f"page={os.path.basename(page_path)} "
                    f"box=({x},{y},{w},{h}) epic={epic or 'NA'}"
                )
 
                # FIX 1: parse_voter_fields() now returns None for non-card
                # blocks (cover pages, map pages, section headers). Must check
                # for None before calling rec.get() — otherwise crashes with
                # AttributeError: 'NoneType' has no attribute 'get'.
                rec = parse_voter_fields(text, epic=epic, debug_context=debug_context)
                if rec is None:
                    continue
 
                key_fields = [
                    rec.get('EPIC Number', ''),
                    rec.get('Name', ''),
                    rec.get('Relative Name', ''),
                    rec.get('House Number', ''),
                    rec.get('Age', ''),
                    rec.get('Gender', ''),
                ]
                if not any(str(v).strip() for v in key_fields):
                    continue
 
                rec['source_file'] = os.path.basename(page_path)
                page_records.append(rec)
            except Exception as e:
                print(f"Error on crop in {page_path}: {e}")
    except Exception as e:
        print(f"Error processing page {page_path}: {e}")
 
    return page_idx, page_records, 'voter'
 
 
def cleanup_legacy_outputs(out_folder):
    """Remove old output files from previous multi-file export versions."""
    legacy_files = [
        "voters.csv",
        "voters.xlsx",
        "voter_output_FINAL.xlsx",
        "voter_output_FINAL_PERFECT.xlsx",
    ]
    removed = []
    for fname in legacy_files:
        path = os.path.join(out_folder, fname)
        if os.path.exists(path):
            os.remove(path)
            removed.append(fname)
    if removed:
        print(f"Removed old output files: {', '.join(removed)}")
 
 
def run_pipeline(
    images_folder=IMAGES_DIR,
    out_folder=OUTPUT_DIR,
    pdf_path=None,
    autosave_every_pages=5,
    skip_front_pages=0,
    progress_callback: Optional[Callable[[int], None]] = None,
):
    """Run end-to-end OCR from input pages/PDF and persist records to Excel."""
    os.makedirs(out_folder, exist_ok=True)
    cleanup_legacy_outputs(out_folder)
 
    working_images_folder = images_folder
    temp_images_folder = None
 
    if pdf_path:
        temp_images_folder = tempfile.mkdtemp(prefix="ocr_pages_")
        working_images_folder = temp_images_folder
 
    if pdf_path:
        print(f"Input PDF: {pdf_path}")
 
    try:
        pages, metadata = get_voter_pages(
            working_images_folder,
            pdf_path=pdf_path,
            skip_front_pages=skip_front_pages,
        )
 
        if not pages:
            print(
                "No input pages found. Add page images to 'images/' "
                "or run with pdf_path='sample_data.pdf'."
            )
            return {"records": [], "pages_processed": 0, "output_path": None}
 
        if progress_callback:
            progress_callback(15)
 
        pages = [page for page in pages if is_data_page(page)]
        print(f"Auto-detected {len(pages)} data pages")
 
        if not pages:
            return {"records": [], "pages_processed": 0, "output_path": None}
 
        print(
            f"Processing {len(pages)} data pages from '{working_images_folder}' "
            f"after skipping {skip_front_pages} front pages."
        )
 
        output_xlsx_path = os.path.join(out_folder, "voter_output.xlsx")
        fallback_xlsx_path = os.path.join(out_folder, "voter_output_autosave.xlsx")
        latest_saved_path = None
 
        def flush_outputs():
            nonlocal latest_saved_path
            try:
                save_to_formatted_excel(records, output_xlsx_path, metadata=metadata)
                latest_saved_path = output_xlsx_path
            except PermissionError:
                print(
                    f"Could not write '{output_xlsx_path}' (file is in use). "
                    f"Saving to '{fallback_xlsx_path}' instead."
                )
                save_to_formatted_excel(records, fallback_xlsx_path, metadata=metadata)
                latest_saved_path = fallback_xlsx_path
 
        records = []
        pages_processed = 0

        try:
            # Process each page once to extract all voter cards uniformly
            # (from data pages, voter pages, amendment pages, etc.)
            serial_counter = 1
            total_tasks = len(pages)
            
            with ThreadPoolExecutor(max_workers=12) as executor:
                # Submit voter processing for each page
                future_to_page = {executor.submit(process_single_page, (page, idx)): idx 
                                  for idx, page in enumerate(pages)}
                
                for future in tqdm(
                    as_completed(future_to_page),
                    total=len(future_to_page),
                    desc="Processing pages for voter cards",
                ):
                    try:
                        page_idx, result_records, record_type = future.result()
                        
                        # Mark all records as 'Voter' type (system extracts voter cards uniformly)
                        for rec in result_records:
                            rec['Record Type'] = 'Voter'
                            rec['Serial Number'] = serial_counter
                            records.append(rec)
                            serial_counter += 1
                    except Exception as e:
                        print(f"Page {future_to_page[future]} failed: {e}")
                    finally:
                        pages_processed += 1
                    
                    if progress_callback and len(pages) > 0:
                        progress_callback(int((pages_processed / total_tasks) * 90))
                    if autosave_every_pages > 0 and pages_processed % autosave_every_pages == 0:
                        flush_outputs()
 
        except KeyboardInterrupt:
            print("\nInterrupted. Saving partial results...")
            flush_outputs()
            print(f"Saved {len(records)} partial voter records to {latest_saved_path}")
            return {
                "records": records,
                "pages_processed": pages_processed,
                "output_path": latest_saved_path,
            }
 
        flush_outputs()
        if progress_callback:
            progress_callback(100)
        print(f"Saved {len(records)} voter records to {latest_saved_path}")
        return {
            "records": records,
            "pages_processed": pages_processed,
            "output_path": latest_saved_path,
        }
    finally:
        if temp_images_folder and os.path.isdir(temp_images_folder):
            shutil.rmtree(temp_images_folder, ignore_errors=True)
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Electoral roll OCR: PDF/images -> voter records Excel"
    )
    parser.add_argument("--pdf", dest="pdf_path", default=None)
    parser.add_argument("--images", dest="images_folder", default=IMAGES_DIR)
    parser.add_argument("--output", dest="out_folder", default=OUTPUT_DIR)
    parser.add_argument("--skip-front-pages", dest="skip_front_pages", type=int, default=0)
    parser.add_argument("--autosave-every-pages", dest="autosave_every_pages", type=int, default=5)
    parser.add_argument("--use-sample-pdf-if-empty", action="store_true")
 
    args = parser.parse_args()
 
    selected_pdf = args.pdf_path
    if selected_pdf is None and args.use_sample_pdf_if_empty and os.path.exists(PDF_SAMPLE):
        image_files = (
            [
                f for f in os.listdir(args.images_folder)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))
            ]
            if os.path.exists(args.images_folder)
            else []
        )
        if not image_files:
            selected_pdf = PDF_SAMPLE
            print(f"No images found in '{args.images_folder}'. Using '{PDF_SAMPLE}'.")
 
    run_pipeline(
        images_folder=args.images_folder,
        out_folder=args.out_folder,
        pdf_path=selected_pdf,
        autosave_every_pages=args.autosave_every_pages,
        skip_front_pages=max(0, args.skip_front_pages),
    )