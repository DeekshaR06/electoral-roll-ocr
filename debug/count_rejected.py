"""Simple counter for rejected boxes."""

import os
import cv2
import tempfile
import shutil
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.parser import parse_voter_fields

def count_rejected(pdf_path):
    """Count rejected boxes."""
    
    temp_folder = tempfile.mkdtemp(prefix="count_")
    pages, _ = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    data_pages = [p for p in pages if is_data_page(p)]
    
    rejected_pages = []  # (page_num, count)
    total_rejected = 0
    
    for page_num, page_path in enumerate(data_pages):
        img = cv2.imread(page_path)
        if img is None:
            continue
        
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        page_rejected = 0
        
        for box_idx, (x, y, w, h) in enumerate(boxes):
            voter_crop = img[y:y + h, x:x + w]
            text = image_array_to_text(voter_crop, psm=6)
            
            epic = extract_epic_from_crop(voter_crop)
            if not epic:
                epic = extract_epic_fallback_from_text(text)
            
            try:
                rec = parse_voter_fields(text, epic=epic)
                
                if rec is None:
                    page_rejected += 1
                else:
                    key_fields = [
                        rec.get('EPIC Number', ''),
                        rec.get('Name', ''),
                        rec.get('Relative Name', ''),
                        rec.get('House Number', ''),
                        rec.get('Age', ''),
                        rec.get('Gender', ''),
                    ]
                    if not any(str(v).strip() for v in key_fields):
                        page_rejected += 1
            except:
                page_rejected += 1
        
        if page_rejected > 0:
            rejected_pages.append((page_num + 1, len(boxes), page_rejected))
            total_rejected += page_rejected
            print(f"Page {page_num + 1}: {page_rejected} of {len(boxes)} boxes rejected")
    
    print(f"\nTotal rejected: {total_rejected}")
    
    if rejected_pages:
        print("\nPages with rejections:")
        for pg_num, total_boxes, rejected in rejected_pages:
            print(f"  Page {pg_num}: {rejected}/{total_boxes} rejected")
    
    shutil.rmtree(temp_folder, ignore_errors=True)

if __name__ == '__main__':
    count_rejected("newTest1.pdf")
