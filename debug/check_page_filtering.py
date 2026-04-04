"""
Diagnostic: Show which pages are kept/filtered and record counts per section.
"""

import os
import cv2
import tempfile
import shutil
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import is_data_page, detect_voter_boxes

def analyze_page_filtering(pdf_path):
    """Analyze which pages are kept and filtered."""
    
    temp_folder = tempfile.mkdtemp(prefix="pagefilter_")
    pages, metadata = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    
    print(f"Total pages from PDF: {len(pages)}\n")
    
    kept_pages = []
    filtered_pages = []
    
    for idx, page_path in enumerate(pages):
        page_name = os.path.basename(page_path)
        is_data = is_data_page(page_path)
        
        img = cv2.imread(page_path)
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        
        status = "KEEP" if is_data else "FILTER"
        
        if is_data:
            kept_pages.append((idx + 1, page_name, len(boxes)))
        else:
            filtered_pages.append((idx + 1, page_name, len(boxes)))
        
        if (idx + 1) % 5 == 0 or idx == 0 or idx == len(pages) - 1:
            print(f"Page {idx + 1:2d}: {page_name:15s} | Boxes: {len(boxes):2d} | {status}")
    
    print(f"\n--- SUMMARY ---")
    print(f"Pages KEPT for processing: {len(kept_pages)}")
    print(f"Pages FILTERED out: {len(filtered_pages)}")
    
    if filtered_pages:
        print(f"\nFiltered pages (not processed):")
        for pg_num, page_name, box_count in filtered_pages:
            print(f"  Page {pg_num}: {page_name} ({box_count} boxes)")
    
    print(f"\nKept pages (WILL be processed):")
    for pg_num, page_name, box_count in kept_pages[:5]:  # Show first 5
        print(f"  Page {pg_num}: {page_name} ({box_count} boxes)")
    if len(kept_pages) > 5:
        print(f"  ... and {len(kept_pages) - 5} more pages")
    
    # Expected voter count
    total_boxes = sum(boxes for _, _, boxes in kept_pages)
    print(f"\nTotal boxes to extract from kept pages: {total_boxes}")
    
    shutil.rmtree(temp_folder, ignore_errors=True)

if __name__ == '__main__':
    analyze_page_filtering("newTest1.pdf")
