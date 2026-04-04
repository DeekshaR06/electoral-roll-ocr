"""Find ALL boxes that are being rejected across all pages."""

import os
import cv2
import tempfile
import shutil
from pipeline.image_loader import get_voter_pages
from pipeline.preprocessing import detect_voter_boxes, is_data_page
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.parser import parse_voter_fields

def find_all_rejected(pdf_path):
    """Find all rejected boxes across ALL pages."""
    
    temp_folder = tempfile.mkdtemp(prefix="fulldiag_")
    pages, _ = get_voter_pages(temp_folder, pdf_path=pdf_path, skip_front_pages=0)
    data_pages = [p for p in pages if is_data_page(p)]
    
    rejected = []
    accepted = 0
    
    print(f"Checking all {len(data_pages)} data pages...\n")
    
    for page_num, page_path in enumerate(data_pages):
        img = cv2.imread(page_path)
        if img is None:
            continue
        
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        page_name = os.path.basename(page_path)
        
        for box_idx, (x, y, w, h) in enumerate(boxes):
            voter_crop = img[y:y + h, x:x + w]
            text = image_array_to_text(voter_crop, psm=6)
            
            epic = extract_epic_from_crop(voter_crop)
            if not epic:
                epic = extract_epic_fallback_from_text(text)
            
            rec = parse_voter_fields(text, epic=epic)
            
            if rec is None:
                rejected.append((page_num, page_name, box_idx, text, epic, "parse_voter_fields returned None"))
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
                    rejected.append((page_num, page_name, box_idx, text, epic, "no key_fields"))
                else:
                    accepted += 1
    
    print(f"Total accepted: {accepted}")
    print(f"Total rejected: {len(rejected)}\n")
    
    if rejected:
        print("REJECTED BOXES:")
        for page_num, page_name, box_idx, text, epic, reason in rejected:
            print(f"\nPage {page_num + 1} ({page_name}), Box {box_idx + 1}")
            print(f"  Reason: {reason}")
            print(f"  EPIC: {epic}")
            # Show first 150 chars
            preview = ' '.join(text.split())[:150]
            print(f"  Text: {preview}...")
    
    shutil.rmtree(temp_folder, ignore_errors=True)

if __name__ == '__main__':
    find_all_rejected("newTest1.pdf")
