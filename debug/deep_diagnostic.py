"""
Deep diagnostic to find why some extracted boxes are becoming no records.
"""

import os
import cv2
import tempfile
import shutil
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.parser import parse_voter_fields

def deep_diagnostic(pdf_path):
    """Extract and analyze each box to see why records are rejected."""
    
    temp_folder = tempfile.mkdtemp(prefix="deepdiag_")
    pages, _ = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    data_pages = [p for p in pages if is_data_page(p)]
    
    filtered_records = []  # Records that return None from parse_voter_fields
    
    # Check last 3 pages where box count is low
    for idx, page_path in enumerate(data_pages[-3:]):
        page_num = len(data_pages) - 3 + idx + 1
        page_name = os.path.basename(page_path)
        
        print(f"\n--- Page {page_num} ({page_name}) ---")
        img = cv2.imread(page_path)
        if img is None:
            continue
        
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        print(f"Boxes detected: {len(boxes)}")
        
        for box_idx, (x, y, w, h) in enumerate(boxes):
            voter_crop = img[y:y + h, x:x + w]
            text = image_array_to_text(voter_crop, psm=6)
            
            # Try parsing
            epic = extract_epic_from_crop(voter_crop)
            if not epic:
                epic = extract_epic_fallback_from_text(text)
            
            rec = parse_voter_fields(text, epic=epic)
            
            if rec is None:
                print(f"\n  Box {box_idx + 1}: [REJECTED] (parse_voter_fields returned None)")
                # Show first 200 chars of text
                preview = text[:200].replace('\n', ' ')
                print(f"    Text preview: {preview}...")
                filtered_records.append((page_name, box_idx, text, epic))
            else:
                # Check if it passes key_fields validation
                key_fields = [
                    rec.get('EPIC Number', ''),
                    rec.get('Name', ''),
                    rec.get('Relative Name', ''),
                    rec.get('House Number', ''),
                    rec.get('Age', ''),
                    rec.get('Gender', ''),
                ]
                if not any(str(v).strip() for v in key_fields):
                    print(f"  Box {box_idx + 1}: [FILTERED] (no key fields)")
                    filtered_records.append((page_name, box_idx, text, epic))
                else:
                    # Successfully extracted
                    name = rec.get('Name', 'Unknown')
                    epic_val = rec.get('EPIC Number', 'N/A')
                    print(f"  Box {box_idx + 1}: [OK] - {name} ({epic_val})")
    
    print(f"\n\n--- SUMMARY ---")
    print(f"Total boxes rejected/filtered: {len(filtered_records)}")
    
    if filtered_records:
        print("\nRejected box contents:")
        for page, box_idx, text, epic in filtered_records:
            print(f"\n  {page}, Box {box_idx + 1} (EPIC: {epic}):")
            lines = text.strip().split('\n')[:3]  # Show first 3 lines
            for line in lines:
                print(f"    {line}")
    
    shutil.rmtree(temp_folder, ignore_errors=True)

if __name__ == '__main__':
    deep_diagnostic("newTest1.pdf")
