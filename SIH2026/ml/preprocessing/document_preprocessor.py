"""Document Preprocessing, Perspective Normalization, and Multi-Region Segmentation.
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Dict, Any, Optional

def enhance_document_image(image: Image.Image) -> Image.Image:
    """Applies adaptive contrast enhancement and edge sharpening for crisp OCR."""
    img_np = np.array(image.convert("RGB"))
    
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced_np = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
    
    enhanced_img = Image.fromarray(enhanced_np)
    return enhanced_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))

def extract_document_rois(image: Image.Image) -> Dict[str, Image.Image]:
    """Segments standardized identity document into functional ROIs.
    
    Returns:
        dict containing:
          - portrait: facial photo crop
          - visual_zone: printed textual fields
          - mrz: machine readable zone
          - stamp: official seal / stamp region
    """
    w, h = image.size
    
    # Normalized layout anchors (ICAO Doc 9303 / Standard ID cards)
    # Portrait: Exact standard photo region
    portrait_crop = image.crop((40, 85, 180, 265))
    
    # Visual Inspection Zone: Middle band
    viz_crop = image.crop((220, 85, w - 20, 360))
    
    # Stamp Zone: Bottom right of main body
    stamp_crop = image.crop((w - 170, 220, w - 60, 330))
    
    # MRZ: Bottom band
    mrz_crop = image.crop((0, h - 120, w, h))
    
    return {
        "portrait": portrait_crop,
        "visual_zone": viz_crop,
        "stamp": stamp_crop,
        "mrz": mrz_crop,
    }
