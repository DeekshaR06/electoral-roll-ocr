# main.py
import os
import shutil
import tempfile
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed  # OPTIMIZED
from typing import Callable, Optional
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page  # OPTIMIZED
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


def process_single_page(args):  # OPTIMIZED
    """Process one page and return list of voter records without serial numbers."""  # OPTIMIZED
    page_path, page_idx = args  # OPTIMIZED
    page_records = []  # OPTIMIZED
    try:  # OPTIMIZED
        img = cv2.imread(page_path)  # OPTIMIZED
        if img is None:  # OPTIMIZED
            print(f"Warning: could not read {page_path}")  # OPTIMIZED
            return page_idx, []  # OPTIMIZED

        # Each detected box corresponds to one voter card block on the page.
        boxes = detect_voter_boxes(img, min_width=400, min_height=120)  # OPTIMIZED
        for x, y, w, h in boxes:  # OPTIMIZED
            try:  # OPTIMIZED
                voter_crop = img[y:y + h, x:x + w]  # OPTIMIZED
                text = image_array_to_text(voter_crop, psm=6)  # OPTIMIZED
                epic = extract_epic_from_crop(voter_crop)  # OPTIMIZED
                if not epic:  # OPTIMIZED
                    epic = extract_epic_fallback_from_text(text)  # OPTIMIZED
                rec = parse_voter_fields(text, epic=epic)  # OPTIMIZED
                rec['source_file'] = os.path.basename(page_path)  # OPTIMIZED
                page_records.append(rec)  # OPTIMIZED
            except Exception as e:  # OPTIMIZED
                print(f"Error on crop in {page_path}: {e}")  # OPTIMIZED
    except Exception as e:  # OPTIMIZED
        print(f"Error processing page {page_path}: {e}")  # OPTIMIZED

    return page_idx, page_records  # OPTIMIZED


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
    autosave_every_pages=5,  # OPTIMIZED
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

        if progress_callback:  # OPTIMIZED
            progress_callback(15)  # OPTIMIZED
        # Filter out non-data pages (cover/index pages) using layout heuristics.
        pages = [page for page in pages if is_data_page(page)]  # OPTIMIZED
        print(f"Auto-detected {len(pages)} data pages")  # OPTIMIZED

        if not pages:  # OPTIMIZED
            return {  # OPTIMIZED
                "records": [],  # OPTIMIZED
                "pages_processed": 0,  # OPTIMIZED
                "output_path": None,  # OPTIMIZED
            }  # OPTIMIZED

        print(  # OPTIMIZED
            f"Processing {len(pages)} data pages from '{working_images_folder}' after skipping {skip_front_pages} front pages."  # OPTIMIZED
        )  # OPTIMIZED

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
            all_page_results = [[] for _ in range(len(pages))]  # OPTIMIZED
            completed_pages = set()  # OPTIMIZED
            next_page_to_finalize = 0  # OPTIMIZED
            serial_counter = 1  # OPTIMIZED

            with ThreadPoolExecutor(max_workers=4) as executor:  # OPTIMIZED
                future_to_idx = {  # OPTIMIZED
                    executor.submit(process_single_page, (page, idx)): idx  # OPTIMIZED
                    for idx, page in enumerate(pages)  # OPTIMIZED
                }  # OPTIMIZED
                for future in tqdm(as_completed(future_to_idx), total=len(future_to_idx), desc="Processing pages"):  # OPTIMIZED
                    try:  # OPTIMIZED
                        page_idx, page_records = future.result()  # OPTIMIZED
                        all_page_results[page_idx] = page_records  # OPTIMIZED
                        completed_pages.add(page_idx)  # OPTIMIZED
                    except Exception as e:  # OPTIMIZED
                        print(f"Page future failed: {e}")  # OPTIMIZED
                    finally:  # OPTIMIZED
                        pages_processed += 1  # OPTIMIZED

                    # Futures complete out of order; finalize only contiguous pages to
                    # preserve deterministic serial numbering across runs.
                    while next_page_to_finalize in completed_pages:  # OPTIMIZED
                        for rec in all_page_results[next_page_to_finalize]:  # OPTIMIZED
                            rec['Serial Number'] = serial_counter  # OPTIMIZED
                            records.append(rec)  # OPTIMIZED
                            serial_counter += 1  # OPTIMIZED
                        next_page_to_finalize += 1  # OPTIMIZED

                    if progress_callback and len(pages) > 0:  # OPTIMIZED
                        progress_callback(int((pages_processed / len(pages)) * 90))  # OPTIMIZED
                    if autosave_every_pages > 0 and pages_processed % autosave_every_pages == 0:  # OPTIMIZED
                        flush_outputs()  # OPTIMIZED
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
        default=5,  # OPTIMIZED
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