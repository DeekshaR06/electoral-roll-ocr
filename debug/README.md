# Debug & Diagnostic Tools

This folder contains debugging and diagnostic scripts for the Electoral Roll OCR pipeline.

## Quick Reference

| Script | Purpose | When to Use |
|--------|---------|------------|
| **diagnose_missing_fields.py** | Overall field extraction accuracy analysis | After running pipeline to check missing names/relatives/relations |
| **detailed_field_analysis.py** | Shows raw OCR text of problem records | When you need to see actual OCR content for failed extractions |
| **find_duplicates.py** | Find duplicate voter records | To identify if records are being extracted twice |
| **find_all_rejected.py** | Analyze rejected voter cards | When valid cards are being rejected (low extraction count) |
| **debug_card_318.py** | Debug specific card #318 | For targeted debugging of a single problematic card |
| **debug_epic.py** | Debug EPIC extraction logic | When EPIC numbers aren't being extracted correctly |
| **debug_mapping.py** | Debug field mapping | When extracted fields aren't matching expected structure |
| **debug_names.py** | Debug name extraction | When voter names are being missed or truncated |
| **find_bad_names.py** | Find problematic name patterns | To identify systematic name extraction failures |

## Usage Examples

### Check Overall Accuracy
```bash
python debug/diagnose_missing_fields.py
```
This shows how many records have missing names, relative names, or relation types.

### Analyze Problem Records
```bash
python debug/detailed_field_analysis.py
```
Shows the raw OCR text from the first few problem cards to understand why extraction failed.

### Find Duplication Issues
```bash
python debug/find_duplicates.py
```
Identifies if the same voter appears multiple times in output.

### Check Why Records Were Rejected
```bash
python debug/find_all_rejected.py
```
Shows cards that Tesseract detected but the parser rejected, and their OCR text.

## Workflow Tips

1. **After Processing a New PDF:**
   - Run `diagnose_missing_fields.py` to check accuracy
   - If missing fields > 2%, run `detailed_field_analysis.py` to see what patterns are failing

2. **If Record Count is Too Low:**
   - Run `find_all_rejected.py` to see rejected cards
   - Check if validation logic is too strict

3. **If Duplicates Exist:**
   - Run `find_duplicates.py` to identify them
   - This usually indicates pages being processed multiple times

4. **For Specific Field Problems:**
   - Use targeted debug scripts (`debug_names.py`, `debug_epic.py`, etc.)
   - These isolate specific extraction logic

## Notes

- Debug scripts read from the latest OCR temp directory (`ocr_pages_*`)
- Output Excel file is assumed to be in `output/voter_output.xlsx`
- Run from project root: `python debug/script_name.py`
