"""
Diagnostic script to identify missing names and relative information.
Analyzes raw OCR text vs extracted data to find patterns being missed.
"""

import json
import re
import openpyxl
from pathlib import Path
from pipeline.parser import parse_voter_fields, _extract_name, _extract_relation
from pipeline.ocr_engine import image_array_to_text
from pipeline.preprocessing import detect_voter_boxes
import cv2
import numpy as np
from PIL import Image
import pytesseract

def analyze_extraction_accuracy():
    """Compare raw OCR text with extracted fields to identify gaps."""
    
    # Read the output Excel file
    xlsx_path = Path('output/voter_output.xlsx')
    if not xlsx_path.exists():
        print("❌ Output Excel file not found")
        return
    
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    
    # Count records with missing data
    missing_names = 0
    missing_relatives = 0
    missing_relation_type = 0
    name_examples = []
    relative_examples = []
    relation_type_examples = []
    
    print("\n📊 Analyzing extracted voter records...")
    print("=" * 80)
    
    # Skip metadata rows (rows 1-8 typically)
    start_row = 9
    for row_idx, row in enumerate(ws.iter_rows(min_row=start_row, values_only=True), start=start_row):
        if not row or not row[0]:  # Empty row
            break
        
        # Column indices: 0=Serial, 1=EPIC, 2=Name, 3=Relative Name, 4=Relation Type, 5=House, 6=Age, 7=Gender, 8=Record Type
        serial = row[0]
        name = row[2] or ''
        relative_name = row[3] or ''
        relation_type = row[4] or ''
        
        if not name:
            missing_names += 1
            if len(name_examples) < 5:
                name_examples.append(f"Serial {serial}")
        
        if not relative_name:
            missing_relatives += 1
            if len(relative_examples) < 5:
                relative_examples.append(f"Serial {serial}")
        
        if not relation_type:
            missing_relation_type += 1
            if len(relation_type_examples) < 5:
                relation_type_examples.append(f"Serial {serial}")
    
    total_records = row_idx - start_row + 1
    
    print(f"\n🎯 Total Records Analyzed: {total_records}")
    print(f"\n❌ Missing Names: {missing_names} ({100*missing_names/total_records:.1f}%)")
    if name_examples:
        print(f"   Examples: {', '.join(name_examples)}")
    
    print(f"\n❌ Missing Relative Names: {missing_relatives} ({100*missing_relatives/total_records:.1f}%)")
    if relative_examples:
        print(f"   Examples: {', '.join(relative_examples)}")
    
    print(f"\n❌ Missing Relation Type: {missing_relation_type} ({100*missing_relation_type/total_records:.1f}%)")
    if relation_type_examples:
        print(f"   Examples: {', '.join(relation_type_examples)}")
    
    print("\n" + "=" * 80)


def analyze_ocr_patterns():
    """
    Analyze OCR pages to find patterns in Name and Relation fields.
    """
    ocr_dir = Path('ocr_pages_*')
    ocr_dirs = list(Path('.').glob('ocr_pages_*'))
    
    if not ocr_dirs:
        print("❌ No OCR pages directory found")
        return
    
    ocr_dir = ocr_dirs[0]
    print(f"\n📂 Analyzing OCR pages from: {ocr_dir}")
    
    pages = sorted(ocr_dir.glob('page_*.jpg'))[:5]  # First 5 pages
    
    name_patterns = {}
    relation_patterns = {}
    
    for page_path in pages:
        print(f"\n🔍 Processing: {page_path.name}")
        
        img = cv2.imread(str(page_path))
        if img is None:
            continue
        
        boxes = detect_voter_boxes(img)
        print(f"   Found {len(boxes)} voter boxes")
        
        for i, (x, y, w, h) in enumerate(boxes[:3]):  # First 3 boxes per page
            crop = img[y:y+h, x:x+w]
            ocr_text = pytesseract.image_to_string(crop)
            
            # Look for Name patterns
            name_matches = re.findall(r'(?<!\w)Name\s*[:=]?\s*([^\n=:]{15,60})', ocr_text, re.IGNORECASE)
            if name_matches:
                pattern = name_matches[0][:30]
                name_patterns[pattern] = name_patterns.get(pattern, 0) + 1
            
            # Look for Relation patterns
            for rel_label in ['Husband', 'Father', 'Mother', 'Other']:
                rel_matches = re.findall(rf"{rel_label}'?s?\s*Name?\s*[:=]?\s*([^\n=:]{{15,60}})", ocr_text, re.IGNORECASE)
                if rel_matches:
                    pattern = f"{rel_label}: {rel_matches[0][:25]}"
                    relation_patterns[pattern] = relation_patterns.get(pattern, 0) + 1
    
    if name_patterns:
        print("\n📋 Name Patterns Found:")
        for pattern, count in sorted(name_patterns.items(), key=lambda x: -x[1])[:10]:
            print(f"  - {pattern} (count: {count})")
    
    if relation_patterns:
        print("\n📋 Relation Patterns Found:")
        for pattern, count in sorted(relation_patterns.items(), key=lambda x: -x[1])[:10]:
            print(f"  - {pattern} (count: {count})")


def find_low_confidence_extractions():
    """
    Find records that might have extraction issues by analyzing
    the raw OCR text stored in the Excel.
    """
    xlsx_path = Path('output/voter_output.xlsx')
    if not xlsx_path.exists():
        print("❌ Output Excel file not found")
        return
    
    # For now, this is a placeholder
    # The raw_text is not typically stored in the final Excel
    print("\n💡 Tip: To analyze raw OCR text, enable raw_text column in Excel output")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🔬 ELECTORAL ROLL OCR - FIELD EXTRACTION DIAGNOSTIC")
    print("=" * 80)
    
    analyze_extraction_accuracy()
    analyze_ocr_patterns()
    find_low_confidence_extractions()
    
    print("\n✅ Diagnostic complete!")
