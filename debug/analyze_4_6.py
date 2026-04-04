"""Find specific rejected boxes on pages 4 and 6."""

import os
import cv2
import tempfile
import shutil
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.parser import parse_voter_fields

def analyze_pages_4_6(pdf_path):
    """Analyze pages 4 and 6 specifically."""
    
    temp_folder = tempfile.mkdtemp(prefix="analyze_")
    pages, _ = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    data_pages = [p for p in pages if is_data_page(p)]
    
    target_pages = {3: data_pages[3], 5: data_pages[5]}  # 0-indexed
    
    for page_idx, page_path in target_pages.items():
        page_num = page_idx + 1
        img = cv2.imread(page_path)
        if img is None:
            continue
        
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        
        print(f"\n--- Page {page_num} ({os.path.basename(page_path)}) ---")
        print(f"Total boxes: {len(boxes)}\n")
        
        for box_idx, (x, y, w, h) in enumerate(boxes):
            voter_crop = img[y:y + h, x:x + w]
            text = image_array_to_text(voter_crop, psm=6)
            
            epic = extract_epic_from_crop(voter_crop)
            if not epic:
                epic = extract_epic_fallback_from_text(text)
            
            rec = parse_voter_fields(text, epic=epic)
            
            if rec is None:
                print(f"Box {box_idx + 1}: [REJECTED] - parse_voter_fields returned None")
                print(f"  EPIC: {epic}")
                print(f"  Text (first 300 chars):")
                preview = ' '.join(text.split())[:300]
                print(f"    {preview}")
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
                    print(f"Box {box_idx + 1}: [FILTERED] - no key_fields")
                    print(f"  EPIC: {epic}")
                    print(f"  Record: {rec}")
                else:
                    name = rec.get('Name', '?')
                    print(f"Box {box_idx + 1}: [OK] - {name}")
    
    shutil.rmtree(temp_folder, ignore_errors=True)

if __name__ == '__main__':
    analyze_pages_4_6("newTest1.pdf")
