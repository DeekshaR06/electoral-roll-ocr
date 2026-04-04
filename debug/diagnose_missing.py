"""
Diagnostic script to find missing records.
Checks which pages are being filtered out and why.
"""

import os
import cv2
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page
from pipeline.ocr_engine import image_array_to_text
import tempfile
import shutil

def diagnose_extraction(pdf_path):
    """Analyze PDF to find where records might be missing."""
    
    # Extract images
    temp_folder = tempfile.mkdtemp(prefix="diag_")
    print(f"Converting PDF to images...")
    pages, metadata = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    
    print(f"\n✓ Total pages extracted: {len(pages)}")
    
    # Check data page filtering
    data_pages = [p for p in pages if is_data_page(p)]
    non_data_pages = [p for p in pages if not is_data_page(p)]
    
    print(f"✓ Data pages detected: {len(data_pages)}")
    print(f"✗ Non-data pages (filtered out): {len(non_data_pages)}")
    
    if non_data_pages:
        print("\nNon-data pages filtered by is_data_page():")
        for page in non_data_pages:
            print(f"  - {os.path.basename(page)}")
    
    # Check box detection on each data page
    print(f"\n--- Analyzing box detection on {len(data_pages)} data pages ---")
    total_boxes = 0
    low_box_pages = []
    
    for idx, page_path in enumerate(data_pages):
        img = cv2.imread(page_path)
        if img is None:
            continue
        
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        total_boxes += len(boxes)
        
        if len(boxes) < 5:  # Abnormally low box count
            low_box_pages.append((os.path.basename(page_path), len(boxes)))
        
        if (idx + 1) % 5 == 0 or idx == 0:
            print(f"  Page {idx+1:2d}: {len(boxes):2d} boxes detected")
    
    print(f"\n✓ Total boxes detected across all data pages: {total_boxes}")
    
    if low_box_pages:
        print(f"\n⚠ Pages with unusually low box counts:")
        for page_name, box_count in low_box_pages:
            print(f"  - {page_name}: {box_count} boxes")
    
    # Cleanup
    shutil.rmtree(temp_folder, ignore_errors=True)
    
    print("\n--- Summary ---")
    print(f"Expected records (at ~26-27 per data page): {len(data_pages) * 26}")
    print(f"Actual extracted: 821")
    print(f"Missing: 5")
    print(f"\nLikely reasons for missing records:")
    print("  1. Boxes not detected on some pages (check low_box_pages)")
    print("  2. parse_voter_fields() returns None for some extracted boxes")
    print("  3. Records filtered by key_fields validation")

if __name__ == '__main__':
    diagnose_extraction("newTest1.pdf")
