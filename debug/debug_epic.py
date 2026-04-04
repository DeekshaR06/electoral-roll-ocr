import cv2
import pytesseract
from pipeline.ocr_engine import extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.preprocessing import detect_voter_boxes

# Load a data page and check for missing EPICs
img_path = 'images/page_003.jpg'
img = cv2.imread(img_path)
boxes = detect_voter_boxes(img, min_width=400, min_height=150)

print(f'Found {len(boxes)} voter boxes on {img_path}')
print('\n=== Checking EPIC extraction for first 5 cards ===\n')

for idx, (x, y, w, h) in enumerate(boxes[:5]):
    voter_crop = img[y:y+h, x:x+w]
    text = pytesseract.image_to_string(voter_crop, config='--oem 3 --psm 6')
    
    epic_header = extract_epic_from_crop(voter_crop)
    epic_fallback = extract_epic_fallback_from_text(text)
    epic_final = epic_header or epic_fallback
    
    print(f'Card {idx+1}:')
    print(f'  Header extraction: {epic_header}')
    print(f'  Fallback extraction: {epic_fallback}')
    print(f'  Final EPIC: {epic_final or "(MISSING)"}')
    print(f'  Raw text (first 250 chars):\n    {repr(text[:250])}')
    print()
