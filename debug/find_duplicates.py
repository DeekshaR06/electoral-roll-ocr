"""
Find duplicate records in the voter_output.xlsx file.
Duplicates are identified by matching EPIC Number, Name, and House Number.
"""

import pandas as pd
from collections import defaultdict
import sys

def find_duplicates(excel_path):
    """Load Excel and find duplicate records."""
    try:
        # Read without header first to see structure
        xl_file = pd.ExcelFile(excel_path)
        ws = xl_file.parse(sheet_name=0, header=None)
        
        # Find where actual headers start
        # Look for "Serial Number" in first column
        header_row = None
        for idx, row in ws.iterrows():
            if isinstance(row[0], str) and 'Serial Number' in str(row[0]):
                header_row = idx
                break
        
        if header_row is None:
            print("Could not find header row")
            return
        
        # Read from the header row onwards
        df = pd.read_excel(excel_path, sheet_name=0, header=header_row)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return
    
    print(f"Total records in Excel: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"Header row index: {header_row}")
    print()
    
    # Create a key for each record (EPIC, Name, House Number)
    duplicates = defaultdict(list)
    
    for idx, row in df.iterrows():
        epic = str(row.get('EPIC Number', '')).strip()
        name = str(row.get('Name', '')).strip()
        house = str(row.get('House Number', '')).strip()
        record_type = str(row.get('Record Type', 'Unknown')).strip()
        
        # Build key from non-empty fields
        key_parts = [p for p in [epic, name, house] if p]
        if key_parts:
            key = tuple(key_parts)
            duplicates[key].append({
                'serial': row.get('Serial Number', ''),
                'epic': epic,
                'name': name,
                'house': house,
                'record_type': record_type,
                'row_index': idx + 2  # Excel is 1-indexed, +1 for header
            })
    
    # Find actual duplicates
    actual_duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
    
    if actual_duplicates:
        print(f"Found {len(actual_duplicates)} DUPLICATE groups:\n")
        for key, records in list(actual_duplicates.items())[:10]:  # Show first 10
            print(f"Key: {key}")
            for rec in records:
                print(f"  Row {rec['row_index']}: Serial={rec['serial']}, Type={rec['record_type']}")
            print()
        
        # Summary
        total_dups = sum(len(v) - 1 for v in actual_duplicates.values())
        print(f"Total duplicate records (extra copies): {total_dups}")
        print(f"\nExpected unique records: {len(df) - total_dups}")
    else:
        print("No exact duplicates found.")
    
    # Check for records with same EPIC but different names
    print("\n--- Checking for same EPIC with different names ---")
    epics = defaultdict(list)
    for idx, row in df.iterrows():
        epic = str(row.get('EPIC Number', '')).strip()
        if epic:
            epics[epic].append({
                'name': str(row.get('Name', '')).strip(),
                'house': str(row.get('House Number', '')).strip(),
                'record_type': str(row.get('Record Type', '')).strip(),
                'row_index': idx + 2
            })
    
    multi_name_epics = {k: v for k, v in epics.items() if len(set(r['name'] for r in v)) > 1}
    if multi_name_epics:
        print(f"Found {len(multi_name_epics)} EPIC numbers with multiple names:")
        for epic, records in list(multi_name_epics.items())[:5]:
            print(f"  EPIC {epic}:")
            for rec in records:
                print(f"    Row {rec['row_index']}: {rec['name']} ({rec['record_type']})")

if __name__ == '__main__':
    excel_path = "output/voter_output.xlsx"
    find_duplicates(excel_path)
