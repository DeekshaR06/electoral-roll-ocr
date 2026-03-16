# pipeline/preprocessing.py
import cv2
import numpy as np

def to_grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def denoise(img):
    # Non-local means or median blur
    return cv2.fastNlMeansDenoising(img, h=10)

def adaptive_threshold(img):
    # img should be grayscale
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 25, 10)

def resize_for_ocr(img, max_dim=2000):
    h, w = img.shape[:2]
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
    return img

def deskew(img):
    """
    Deskew grayscale image using Hough / moments approach.
    Returns deskewed image.
    """
    coords = np.column_stack(np.where(img < 255))
    if coords.size == 0:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def preprocess_for_ocr(path_or_image):
    """
    Accepts a cv2 image (BGR) or a file path. Returns cleaned grayscale image ready for OCR.
    """
    if isinstance(path_or_image, str):
        img = cv2.imread(path_or_image)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {path_or_image}")
    else:
        img = path_or_image.copy()

    img = resize_for_ocr(img)
    gray = to_grayscale(img)
    gray = denoise(gray)
    gray = deskew(gray)
    # Some images benefit from adaptive threshold; others from a light blur + Otsu.
    th = adaptive_threshold(gray)
    return th


def preprocess_page_for_boxes(img):
    """
    Build the threshold image used to detect voter card blocks on a full page.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        25,
        15,
    )
    return thresh


def detect_voter_boxes(img, min_width=400, min_height=120):
    """
    Detect voter-card contours and return sorted (x, y, w, h) boxes.
    """
    thresh = preprocess_page_for_boxes(img)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > min_width and h > min_height:
            boxes.append((x, y, w, h))

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    return boxes


def is_data_page(image_path: str, min_boxes: int = 3, min_width: int = 400, min_height: int = 120) -> bool:  # OPTIMIZED
    """  # OPTIMIZED
    Returns True if page contains voter card data.  # OPTIMIZED
    Detects data pages automatically without hardcoding page numbers.  # OPTIMIZED
    Works for any Electoral Roll PDF regardless of front page count.  # OPTIMIZED
    """  # OPTIMIZED
    img = cv2.imread(image_path)  # OPTIMIZED
    if img is None:  # OPTIMIZED
        return False  # OPTIMIZED
    boxes = detect_voter_boxes(img, min_width=min_width, min_height=min_height)  # OPTIMIZED
    return len(boxes) >= min_boxes  # OPTIMIZED