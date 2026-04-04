"""
Enhanced diagnostic to show raw OCR text for records with missing fields.
"""

import json
from pathlib import Path
import re
import sys
import cv2
import numpy as np
import glob
sys.path.insert(0, str(Path.cwd()))

from pipeline.parser import parse_voter_fields, _extract_name, _extract_relation
from pipeline.preprocessing import detect_voter_boxes
from pipeline.ocr_engine import image_array_to_text

def find_problem_records():
    """Extract actual OCR text for records with missing names/relatives."""
    
    # First, find pages to analyze
    pages_dir = list(Path('.').glob('ocr_pages_*'))
    if not pages_dir:
        print("❌ No OCR pages directory found. Please run main.py first to process a PDF.")
        return
    
    ocr_dir = str(pages_dir[0])
    print(f"📂 Loading OCR pages from: {ocr_dir}\n")
    
    # Load all page images
    import glob
    page_paths = sorted(glob.glob(f"{ocr_dir}/page_*.jpg"))
    page_images = [cv2.imread(p) for p in page_paths]
    
    print("=" * 100)
    print("📋 ANALYZING VOTER CARDS WITH MISSING FIELDS")
    print("=" * 100)
    
    card_counter = 0
    problem_cards = []
    
    for page_idx, img in enumerate(page_images):
        if img is None:
            continue
        boxes = detect_voter_boxes(img)
        
        for box_idx, (x, y, w, h) in enumerate(boxes):
            card_counter += 1
            crop = img[y:y+h, x:x+w]
            ocr_text = image_array_to_text(crop)
            
            # Try to extract
            result = parse_voter_fields(ocr_text)
            
            # Check for problems
            has_problem = False
            problem_type = []
            
            if result:
                if not result.get('Name', ''):
                    problem_type.append('NAME')
                    has_problem = True
                if not result.get('Relative Name', ''):
                    problem_type.append('RELATIVE')
                    has_problem = True
                if not result.get('Relation Type', ''):
                    problem_type.append('REL_TYPE')
                    has_problem = True
            else:
                problem_type.append('REJECTED')
                has_problem = True
            
            if has_problem:
                problem_cards.append({
                    'card_num': card_counter,
                    'page': page_idx + 1,
                    'box': box_idx + 1,
                    'problem': ','.join(problem_type),
                    'raw_text': ocr_text,
                    'result': result
                })
                
                if len(problem_cards) >= 15:  # Limit to first 15 problems
                    break
        
        if len(problem_cards) >= 15:
            break
    
    # Display problems
    if not problem_cards:
        print("✅ No problems found! All records extracted successfully.")
        return
    
    print(f"\n🔴 Found {len(problem_cards)} records with issues:\n")
    
    for i, card in enumerate(problem_cards, 1):
        print(f"\n{'─' * 100}")
        print(f"Problem #{i}: Card #{card['card_num']} (Page {card['page']}, Box {card['box']}) - {card['problem']}")
        print(f"{'─' * 100}")
        
        # Show raw OCR text
        text_preview = card['raw_text'].replace('\n', ' | ')
        if len(text_preview) > 150:
            print(f"OCR Text: {text_preview[:150]}...")
        else:
            print(f"OCR Text: {text_preview}")
        
        print()
        
        # Show extracted fields
        if card['result']:
            print("Extracted Fields:")
            for key in ['Name', 'Relation Type', 'Relative Name', 'Age', 'Gender']:
                val = card['result'].get(key, '')
                status = '✅' if val else '❌'
                print(f"  {status} {key:20s}: {val}")
        else:
            print("❌ REJECTED: Card failed validity check")
        
        print()
        
        # ANALYSIS: Look for what's in the raw text that wasn't extracted
        print("Analysis - Searching raw text for patterns:")
        
        # Name patterns
        name_in_text = re.findall(r'(?<!\w)[Nn]ame\s*[:=]?\s*([^\n=:]{10,80})', card['raw_text'])
        if name_in_text and (not card['result'] or not card['result'].get('Name')):
            print(f"  ⚠️  Found Name pattern in text: {name_in_text[0][:60]}")
        
        # Relation patterns
        for rel_label in ['Husband', 'Father', 'Mother', 'Other']:
            rel_in_text = re.findall(
                rf"{rel_label}'?s?\s*[Nn]ame?\s*[:=]?\s*([^\n=:]{{10,80}})",
                card['raw_text'],
                re.IGNORECASE
            )
            if rel_in_text and (not card['result'] or not card['result'].get('Relative Name')):
                print(f"  ⚠️  Found {rel_label} pattern in text: {rel_in_text[0][:60]}")
        
        print()


if __name__ == '__main__':
    find_problem_records()
