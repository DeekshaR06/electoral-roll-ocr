import cv2
import os
from pipeline.preprocessing import detect_voter_boxes
from pipeline.ocr_engine import image_array_to_text, extract_epic_from_crop, extract_epic_fallback_from_text
from pipeline.parser import parse_voter_fields

temp_images = sorted([f for f in os.listdir('images') if f.endswith('.jpg')])

page_idx = 10
card_idx = 8

img_path = os.path.join('images', temp_images[page_idx])
img = cv2.imread(img_path)

boxes = detect_voter_boxes(img, min_width=400, min_height=150)
x, y, w, h = boxes[card_idx]
crop = img[y:y+h, x:x+w]

text = image_array_to_text(crop, psm=6)
epic_header = extract_epic_from_crop(crop)
epic_fallback = extract_epic_fallback_from_text(text)
epic = epic_header or epic_fallback

rec = parse_voter_fields(text, epic=epic)

print(f"Card 8 on page_011.jpg:")
print(f"Raw OCR text:")
print(repr(text))
print()
print(f"Parsed record:")
print(f"  Name: {repr(rec.get('Name'))}")
print(f"  EPIC: {repr(epic)}")
print(f"  Full record: {rec}")
