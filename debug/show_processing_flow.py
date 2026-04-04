"""
Show processing flow: which pages processed, sections detected, records extracted.
Demonstrates: extraction continues through additions→regular sections until end.
"""

import os
import cv2
import tempfile
import shutil
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import is_data_page, detect_voter_boxes
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.parser import parse_voter_fields

def analyze_processing_flow(pdf_path):
    """Show flow:  which sections → how many cards → extraction continues"""
    
    temp_folder = tempfile.mkdtemp(prefix="flow_")
    all_pages, _ = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    
    print(f"Total pages from PDF: {len(all_pages)}\n")
    print("=" * 70)
    print("PROCESSING FLOW: Section Detection & Extraction")
    print("=" * 70)
    
    # Data pages
    data_pages = [p for p in all_pages if is_data_page(p)]
    print(f"\nData pages detected: {len(data_pages)} / {len(all_pages)}\n")
    print("Showing processing order:")
    print("-" * 70)
    
    total_records = 0
    records_by_section = {}
    last_section = None
    consecutive_empty = 0
    stopped_at = None
    
    for page_idx, page_path in enumerate(data_pages):
        page_name = os.path.basename(page_path)
        img = cv2.imread(page_path)
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        
        # Try to detect section from OCR of top portion
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        top_portion = gray[:int(h * 0.15), :]
        
        try:
            import pytesseract
            header_text = pytesseract.image_to_string(top_portion, config='--oem 3 --psm 6').upper()
            if 'ADDITION' in header_text or 'AMENDMENT' in header_text:
                section = 'ADDITIONS'
            elif 'SECTION' in header_text:
                section = 'NEW SECTION'
            else:
                section = 'VOTERS'
        except:
            section = 'VOTERS'
        
        # Count extracted records from this page
        records_this_page = 0
        for x, y, w_box, h_box in boxes:
            voter_crop = img[y:y + h_box, x:x + w_box]
            text = image_array_to_text(voter_crop, psm=6)
            epic = extract_epic_from_crop(voter_crop)
            if not epic:
                epic = extract_epic_fallback_from_text(text)
            
            rec = parse_voter_fields(text, epic=epic)
            if rec is not None:
                key_fields = [
                    rec.get('EPIC Number', ''),
                    rec.get('Name', ''),
                    rec.get('Relative Name', ''),
                    rec.get('House Number', ''),
                    rec.get('Age', ''),
                    rec.get('Gender', ''),
                ]
                if any(str(v).strip() for v in key_fields):
                    records_this_page += 1
        
        total_records += records_this_page
        
        # Track flow
        if section != last_section:
            print(f"\n[{page_idx + 1:2d}] *** {section:15s} section starts ***")
            last_section = section
            records_by_section[section] = 0
        
        if records_this_page == 0:
            consecutive_empty += 1
        else:
            consecutive_empty = 0
        
        status = "OK" if records_this_page > 0 else "EMPTY"
        print(f"[{page_idx + 1:2d}] {page_name:15s} | {len(boxes):2d} boxes | {records_this_page:2d} records | {status}")
        
        records_by_section[section] = records_by_section.get(section, 0) + records_this_page
        
        # Check if we should stop (multiple empty pages in a row)
        if consecutive_empty >= 2 and page_idx < len(data_pages) - 1:
            stopped_at = page_idx + 1
            print(f"\n[STOP: {consecutive_empty} consecutive empty pages]")
            break
    
    print("\n" + "=" * 70)
    print(f"Total records extracted: {total_records}")
    print(f"\nBreakdown by section:")
    for section, count in records_by_section.items():
        print(f"  {section:15s}: {count:3d} records")
    
    if stopped_at:
        print(f"\nProcessing stopped at page {stopped_at} (2+ consecutive empty pages)")
        print(f"Remaining pages: {len(data_pages) - stopped_at}")
    else:
        print(f"\nProcessing continued to end of PDF ({len(data_pages)} pages)")
    
    shutil.rmtree(temp_folder, ignore_errors=True)

if __name__ == '__main__':
    analyze_processing_flow("newTest1.pdf")
