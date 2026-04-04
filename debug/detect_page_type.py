"""
Detect page type/section (Regular Voters, Additions, Summary, etc.)
"""

import cv2
import pytesseract

def detect_page_type(image_path):
    """
    Detect the type/section of a page to understand its content.
    Returns: 'Regular Voters', 'Additions', 'Amendments', 'Summary', or 'Unknown'
    """
    img = cv2.imread(image_path)
    if img is None:
        return 'Unknown'
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Resize to max width for faster OCR
    h, w = gray.shape[:2]
    max_w = 1200
    if w > max_w:
        scale = max_w / float(w)
        gray = cv2.resize(gray, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA)
    
    # Get top portion of page which usually contains section title
    top_portion = gray[:int(gray.shape[0] * 0.3), :]
    text = pytesseract.image_to_string(top_portion, config='--oem 3 --psm 6').upper()
    
    # Check for section type indicators
    if 'ADDITION' in text or 'AMENDMENT' in text or 'SUPPLEMENT' in text:
        return 'Additions'
    elif 'SUMMARY' in text or 'TOTAL' in text or 'VOTER' in text and 'TOTAL' in text:
        return 'Summary'
    elif 'SECTION' in text or 'HOSA' in text or ('1-' in text and 'ROAD' in text):
        return 'Regular Voters'
    else:
        return 'Unknown'

if __name__ == '__main__':
    # Test on pages
    from pipeline.preprocessing import is_data_page
    from pipeline.image_loader import get_voter_pages
    import tempfile
    import shutil

    temp_folder = tempfile.mkdtemp()
    pages, _ = get_voter_pages(temp_folder, pdf_path="newTest1.pdf", skip_front_pages=0)
    data_pages = [p for p in pages if is_data_page(p)]
    
    print(f"Analyzing page types from {len(data_pages)} data pages:\n")
    
    page_types = {}
    for idx, page in enumerate(data_pages):
        page_type = detect_page_type(page)
        if page_type not in page_types:
            page_types[page_type] = []
        page_types[page_type].append(idx + 1)
        
        if (idx + 1) % 5 == 0 or idx == 0:
            print(f"Page {idx + 1:2d}: {page_type}")
    
    print(f"\n--- Summary ---")
    for page_type, pages_list in page_types.items():
        print(f"{page_type:15s}: {len(pages_list):2d} pages - {pages_list[:3]}{'...' if len(pages_list) > 3 else ''}")
    
    shutil.rmtree(temp_folder, ignore_errors=True)
