# pipeline/exporter.py
import pandas as pd
from typing import List, Dict
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

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
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False, encoding='utf-8')
    return out_path

def save_to_excel(records: List[Dict], out_path: str):
    """Write records as a basic Excel file without custom styling."""
    df = _to_voter_df(records)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_excel(out_path, index=False)
    return out_path


def save_to_formatted_excel(records: List[Dict], out_path: str):
    """Notebook-style Excel export with a Booth Details header row."""
    headers = VOTER_HEADERS
    df = _to_voter_df(records)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Voter Data'

    ws['E1'] = 'Booth Details'
    ws['E1'].font = Font(bold=True, size=12)
    ws['E1'].alignment = Alignment(horizontal='center')

    for c, header in enumerate(headers, 1):
        cell = ws.cell(2, c, header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    if not df.empty:
        # Start data rows at row 3 because row 1/2 are title + column headers.
        for r_idx, row in enumerate(df.itertuples(index=False), 3):
            for c_idx, value in enumerate(row, 1):
                cell = ws.cell(r_idx, c_idx, value)
                cell.alignment = Alignment(horizontal='left')

    column_widths = {
        'A': 12,
        'B': 13,
        'C': 25,
        'D': 25,
        'E': 14,
        'F': 15,
        'G': 8,
        'H': 10,
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    wb.save(out_path)
    return out_path