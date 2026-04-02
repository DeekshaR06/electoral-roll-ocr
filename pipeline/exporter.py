# pipeline/exporter.py
import pandas as pd
from typing import List, Dict
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
 
VOTER_HEADERS = [
    'Serial Number',
    'EPIC Number',
    'Name',
    'Relative Name',
    'Relation Type',
    'House Number',
    'Age',
    'Gender',
]
 
 
def _to_voter_df(records: List[Dict]) -> pd.DataFrame:
    """Normalize arbitrary record dicts into the fixed voter export schema."""
    df = pd.DataFrame(records)
    return df.reindex(columns=VOTER_HEADERS)
 
 
def save_to_csv(records: List[Dict], out_path: str):
    """Write records as plain CSV with stable voter column ordering."""
    df = _to_voter_df(records)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    df.to_csv(out_path, index=False, encoding='utf-8')
    return out_path
 
 
def save_to_excel(records: List[Dict], out_path: str):
    """Write records as a basic Excel file without custom styling."""
    df = _to_voter_df(records)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    df.to_excel(out_path, index=False)
    return out_path
 
 
def save_to_formatted_excel(records: List[Dict], out_path: str):
    """
    Export voter records to a clean, properly formatted Excel file.
 
    FIX: Removed the misleading 'Booth Details' label that was placed in
    cell E1 (the Relation Type column). It had no relation to that column
    and confused anyone reading the file. The first row is now a proper
    merged title row showing the total voter count, making the file
    immediately useful when opened.
 
    Layout:
      Row 1 — merged title: "Electoral Roll Data — N voters"
      Row 2 — bold column headers
      Row 3+ — data rows
    """
    headers = VOTER_HEADERS
    df = _to_voter_df(records)
 
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
 
    wb = Workbook()
    ws = wb.active
    ws.title = 'Voter Data'
 
    num_cols = len(headers)
    last_col = get_column_letter(num_cols)
 
    # Row 1: merged title with total count
    title_cell = ws.cell(1, 1, f"Electoral Roll Data — {len(records)} voters")
    title_cell.font = Font(bold=True, size=13)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    title_fill = PatternFill("solid", fgColor="1F4E79")
    title_cell.font = Font(bold=True, size=13, color="FFFFFF")
    title_cell.fill = title_fill
    ws.merge_cells(f"A1:{last_col}1")
    ws.row_dimensions[1].height = 22
 
    # Row 2: column headers
    header_fill = PatternFill("solid", fgColor="2E75B6")
    for c, header in enumerate(headers, 1):
        cell = ws.cell(2, c, header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal='center')
        cell.fill = header_fill
 
    # Row 3+: data
    if not df.empty:
        for r_idx, row in enumerate(df.itertuples(index=False), 3):
            for c_idx, value in enumerate(row, 1):
                cell = ws.cell(r_idx, c_idx, value)
                cell.alignment = Alignment(horizontal='left')
            # Light alternating row shading for readability
            if r_idx % 2 == 0:
                row_fill = PatternFill("solid", fgColor="EBF3FB")
                for c_idx in range(1, num_cols + 1):
                    ws.cell(r_idx, c_idx).fill = row_fill
 
    # Column widths
    column_widths = {
        'A': 12,  # Serial Number
        'B': 13,  # EPIC Number
        'C': 25,  # Name
        'D': 25,  # Relative Name
        'E': 14,  # Relation Type
        'F': 15,  # House Number
        'G': 8,   # Age
        'H': 10,  # Gender
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
 
    # Freeze top 2 rows so headers stay visible when scrolling
    ws.freeze_panes = 'A3'
 
    wb.save(out_path)
    return out_path