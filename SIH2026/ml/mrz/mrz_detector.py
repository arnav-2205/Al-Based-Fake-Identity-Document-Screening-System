"""MRZ Region Detection and Extraction Engine.
Uses OpenCV morphological operations and contour analysis to locate the
Machine Readable Zone at the bottom of identity documents.
"""
import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple

def detect_mrz_region(image: Image.Image) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
    """Detects and crops the MRZ band from a document image.
    
    Returns:
        (cropped_mrz_image, (x, y, w, h))
    """
    img_np = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    
    # Bottom 35% of the document is the canonical MRZ zone
    bottom_crop_y = int(h * 0.65)
    bottom_region = gray[bottom_crop_y:, :]
    
    # Smooth to reduce noise
    blurred = cv2.GaussianBlur(bottom_region, (3, 3), 0)
    
    # Blackhat morphological operation to reveal dark text on light background
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
    blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, kernel)
    
    # Compute Scharr gradient magnitude
    grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
    grad_x = np.absolute(grad_x)
    (min_val, max_val) = (np.min(grad_x), np.max(grad_x))
    grad_x = (255 * ((grad_x - min_val) / (max_val - min_val + 1e-6))).astype("uint8")
    
    # Close gaps between characters in the MRZ lines
    grad_x = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, kernel)
    _, thresh = cv2.threshold(grad_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_box = None
    max_area = 0
    
    for c in contours:
        (x, y, cw, ch) = cv2.boundingRect(c)
        ar = cw / float(ch)
        # MRZ lines have high aspect ratio (wide band)
        if ar > 3.0 and cw > (w * 0.40) and ch > 15:
            area = cw * ch
            if area > max_area:
                max_area = area
                best_box = (x, y + bottom_crop_y, cw, ch)
                
    if best_box is not None:
        bx, by, bw, bh = best_box
        # Add small padding
        pad = 8
        bx = max(0, bx - pad)
        by = max(0, by - pad)
        bw = min(w - bx, bw + 2 * pad)
        bh = min(h - by, bh + 2 * pad)
        
        crop = image.crop((bx, by, bx + bw, by + bh))
        return crop, (bx, by, bw, bh)
    else:
        # Fallback to bottom 25% default band
        def_y = int(h * 0.75)
        crop = image.crop((0, def_y, w, h))
        return crop, (0, def_y, w, h - def_y)
