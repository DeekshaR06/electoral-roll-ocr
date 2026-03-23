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
PDF_SAMPLE = "sample_data.pdf"  # optional: if you want to convert pdf to images first

# Optional Windows override, same behavior as notebook cell.
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")


def process_single_page(args):  
    """Process one page and return list of voter records without serial numbers."""
    page_path, page_idx = args  
    page_records = []  
    try:  
        img = cv2.imread(page_path)  
        if img is None: 
            print(f"Warning: could not read {page_path}")  
            return page_idx, []  

        # Each detected box corresponds to one voter card block on the page.
        boxes = detect_voter_boxes(img, min_width=400, min_height=120)
        for x, y, w, h in boxes:  
            try:  
                voter_crop = img[y:y + h, x:x + w]  
                text = image_array_to_text(voter_crop, psm=6) 
                epic = extract_epic_from_crop(voter_crop) 
                if not epic:
                    epic = extract_epic_fallback_from_text(text)
                rec = parse_voter_fields(text, epic=epic)
                rec['source_file'] = os.path.basename(page_path)
                page_records.append(rec)
            except Exception as e:
                print(f"Error on crop in {page_path}: {e}")
    except Exception as e:
        print(f"Error processing page {page_path}: {e}")

    return page_idx, page_records


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
        # Use an isolated temp folder for PDF page images so repeated runs do not
        # delete or mix pages from another invocation.
        temp_images_folder = tempfile.mkdtemp(prefix="ocr_pages_")
        working_images_folder = temp_images_folder

    if pdf_path:
        print(f"Input PDF: {pdf_path}")

    try:
        pages = get_voter_pages(
            working_images_folder,
            pdf_path=pdf_path,
            skip_front_pages=skip_front_pages,
        )

        if not pages:
            print(
                "No input pages found. Add page images to 'images/' or run with pdf_path='sample_data.pdf'."
            )
            return {
                "records": [],
                "pages_processed": 0,
                "output_path": None,
            }

        if progress_callback:
            progress_callback(15)
        # Filter out non-data pages (cover/index pages) using layout heuristics.
        pages = [page for page in pages if is_data_page(page)]
        print(f"Auto-detected {len(pages)} data pages")

        if not pages:
            return {
                "records": [],
                "pages_processed": 0,
                "output_path": None,
            }

        print(
            f"Processing {len(pages)} data pages from '{working_images_folder}' after skipping {skip_front_pages} front pages."
        )

        output_xlsx_path = os.path.join(out_folder, "voter_output.xlsx")
        fallback_xlsx_path = os.path.join(out_folder, "voter_output_autosave.xlsx")
        latest_saved_path = None

        def flush_outputs():
            """Write records to primary output; fall back if target is locked by Excel."""
            nonlocal latest_saved_path
            try:
                save_to_formatted_excel(records, output_xlsx_path)
                latest_saved_path = output_xlsx_path
            except PermissionError:
                # Most commonly this happens when voter_output.xlsx is open in Excel.
                print(
                    f"Could not write '{output_xlsx_path}' (file is in use). "
                    f"Saving to '{fallback_xlsx_path}' instead."
                )
                save_to_formatted_excel(records, fallback_xlsx_path)
                latest_saved_path = fallback_xlsx_path

        records = []
        pages_processed = 0

        try:
            all_page_results = [[] for _ in range(len(pages))]  
            completed_pages = set()  
            next_page_to_finalize = 0  
            serial_counter = 1  

            with ThreadPoolExecutor(max_workers=4) as executor: 
                future_to_idx = {  
                    executor.submit(process_single_page, (page, idx)): idx  
                    for idx, page in enumerate(pages)  
                }  
                for future in tqdm(as_completed(future_to_idx), total=len(future_to_idx), desc="Processing pages"):
                    try:  
                        page_idx, page_records = future.result() 
                        all_page_results[page_idx] = page_records  
                        completed_pages.add(page_idx)  
                    except Exception as e:  
                        print(f"Page future failed: {e}")  
                    finally:  
                        pages_processed += 1  

                    # Futures complete out of order; finalize only contiguous pages to
                    # preserve deterministic serial numbering across runs.
                    while next_page_to_finalize in completed_pages:  
                        for rec in all_page_results[next_page_to_finalize]:
                            rec['Serial Number'] = serial_counter  
                            records.append(rec) 
                            serial_counter += 1  
                        next_page_to_finalize += 1  

                    if progress_callback and len(pages) > 0: 
                        progress_callback(int((pages_processed / len(pages)) * 90))  
                    if autosave_every_pages > 0 and pages_processed % autosave_every_pages == 0:  
                        flush_outputs()  
        except KeyboardInterrupt:
            print("\nInterrupted. Saving partial results...")
            flush_outputs()
            print(f"Saved {len(records)} partial records to {latest_saved_path}")
            return {
                "records": records,
                "pages_processed": pages_processed,
                "output_path": latest_saved_path,
            }

        flush_outputs()
        if progress_callback:
            progress_callback(100)
        print(f"Saved {len(records)} records to {latest_saved_path}")
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
    parser.add_argument(
        "--pdf",
        dest="pdf_path",
        default=None,
        help="Path to input PDF. If provided, pages are converted to images/ first.",
    )
    parser.add_argument(
        "--images",
        dest="images_folder",
        default=IMAGES_DIR,
        help="Folder containing page images (or destination for converted PDF pages).",
    )
    parser.add_argument(
        "--output",
        dest="out_folder",
        default=OUTPUT_DIR,
        help="Folder to write Excel output.",
    )
    parser.add_argument(
        "--skip-front-pages",
        dest="skip_front_pages",
        type=int,
        default=0,
        help="Number of front pages to skip after sorting pages.",
    )
    parser.add_argument(
        "--autosave-every-pages",
        dest="autosave_every_pages",
        type=int,
        default=5,
        help="Autosave outputs every N processed pages. Use 0 to disable.",
    )
    parser.add_argument(
        "--use-sample-pdf-if-empty",
        action="store_true",
        help="If no images exist and sample_data.pdf exists, use it automatically.",
    )

    args = parser.parse_args()

    selected_pdf = args.pdf_path
    if selected_pdf is None and args.use_sample_pdf_if_empty and os.path.exists(PDF_SAMPLE):
        image_files = [
            f
            for f in os.listdir(args.images_folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))
        ] if os.path.exists(args.images_folder) else []
        if not image_files:
            selected_pdf = PDF_SAMPLE
            print(
                f"No images found in '{args.images_folder}'. Using '{PDF_SAMPLE}' to generate pages."
            )

    run_pipeline(
        images_folder=args.images_folder,
        out_folder=args.out_folder,
        pdf_path=selected_pdf,
        autosave_every_pages=args.autosave_every_pages,
        skip_front_pages=max(0, args.skip_front_pages),
    )