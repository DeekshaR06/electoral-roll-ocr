import cv2
import pytesseract
import os
from pipeline.preprocessing import detect_voter_boxes
from pipeline.parser import parse_voter_fields
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text

# Check images directory
temp_images = sorted([f for f in os.listdir('images') if f.endswith('.jpg')])
if len(temp_images) >= 5:
    img_path = os.path.join('images', temp_images[4])
    img = cv2.imread(img_path)
    if img is not None:
        boxes = detect_voter_boxes(img, min_width=400, min_height=150)
        print(f'Page {temp_images[4]}: Found {len(boxes)} cards\n')
        
        for idx, (x, y, w, h) in enumerate(boxes[:3]):
            crop = img[y:y+h, x:x+w]
            text = image_array_to_text(crop, psm=6)
            epic = extract_epic_from_crop(crop) or extract_epic_fallback_from_text(text)
            rec = parse_voter_fields(text, epic=epic)
            
            name = rec.get('Name', '') if rec else 'PARSE ERROR'
            
            print(f'Card {idx+1}:')
            print(f'  Name: {repr(name)}')
            print(f'  Contains colon: {(":" in str(name)) if name else False}')
            print(f'  EPIC: {epic or "(MISSING)"}')
            print(f'  OCR text (first 200 chars): {repr(text[:200])}')
            print()
