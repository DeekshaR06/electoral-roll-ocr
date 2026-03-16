# electoral-roll-ocr

OCR pipeline to extract voter details from electoral-roll pages (images or PDF), matching the notebook workflow in a modular file structure.

## Features

- Numeric sorting of `page_*.jpg` files.
- Process all pages by default; optionally skip front pages when needed.
- Detect voter-card boxes on each page (`w > 400`, `h > 120`).
- OCR each voter card crop (`--psm 6`).
- EPIC extraction from header crop with OCR correction (`3 letters + 7 digits`).
- Fallback EPIC extraction from first OCR line.
- Field extraction:
	- Serial Number
	- EPIC Number
	- Name
	- Relative Name
	- Relation Type
	- House Number
	- Age
	- Gender
- Export file:
	- `output/voter_output.xlsx`
- Startup cleanup removes old legacy output files from previous versions.

## Project Structure

- `main.py`: Runs end-to-end extraction.
- `pipeline/image_loader.py`: Loads images, optional PDF-to-images conversion.
- `pipeline/preprocessing.py`: Page thresholding and voter box detection.
- `pipeline/ocr_engine.py`: OCR helpers and EPIC extraction logic.
- `pipeline/parser.py`: Text parsing into voter fields.
- `pipeline/exporter.py`: Excel export writer (formatted workbook).

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run with PDF input (recommended, notebook-style flow):

```bash
python main.py --pdf sample_data.pdf
```

3. Or run with pre-existing page images (`page_001.jpg`, `page_002.jpg`, ... in `images/`):

```bash
python main.py
```

4. Useful options:

```bash
python main.py --pdf your_roll.pdf --images images --output output --skip-front-pages 2
python main.py --pdf your_roll.pdf --autosave-every-pages 1
python main.py --use-sample-pdf-if-empty
```

Optional Windows setup for Tesseract path:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
python main.py
```
