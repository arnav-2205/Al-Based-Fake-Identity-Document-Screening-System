"""Photo Replacement & Compositing Forensic Analysis Module.

Detects whether a photograph on an identity document appears to have been
digitally replaced, manipulated, or composited.

Independent of face verification (face-matching).
"""
from __future__ import annotations

import io
import math
import numpy as np
import cv2
from PIL import Image, ImageChops
from typing import Dict, Any, List, Tuple, Optional


def detect_photo_region(img: Image.Image | np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], float, List[str]]:
    """Locate portrait region using face detection or layout geometry.

    Returns:
        (x0, y0, x1, y1) bounding box in image coordinates, confidence score, and detection notes.
    """
    if isinstance(img, np.ndarray):
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    w, h = img.size
    rgb = np.asarray(img.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    notes = []

    # 1. Try OpenCV Haar Cascade face detection
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(int(h * 0.15), int(h * 0.15)))
        if len(faces) > 0:
            # Pick largest face
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            # Expand bounding box by 30% margin to cover entire portrait box border
            margin_w = int(fw * 0.30)
            margin_h = int(fh * 0.35)
            x0 = max(0, fx - margin_w)
            y0 = max(0, fy - margin_h)
            x1 = min(w, fx + fw + margin_w)
            y1 = min(h, fy + fh + margin_h)
            notes.append(f"Portrait region detected via face location: [{x0}, {y0}, {x1}, {y1}]")
            return (x0, y0, x1, y1), 0.92, notes
    except Exception as e:
        notes.append(f"Face cascade detection note: {e}")

    # 2. Document layout heuristic fallback (e.g. passport / ID photo region)
    # Typical portrait position: left 5%-40% width, 15%-75% height
    x0, y0, x1, y1 = int(w * 0.04), int(h * 0.15), int(w * 0.38), int(h * 0.72)
    notes.append(f"Portrait region estimated from document geometry: [{x0}, {y0}, {x1}, {y1}]")
    return (x0, y0, x1, y1), 0.65, notes


def analyze_photo_replacement(img: Image.Image | np.ndarray, photo_box: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
    """Analyze portrait region for forensic indicators of photo replacement / digital splicing."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    w, h = img.size

    # 1. Locate photo region if not provided
    if photo_box is None:
        photo_box, loc_conf, loc_notes = detect_photo_region(img)
    else:
        loc_conf = 0.95
        loc_notes = ["User-provided portrait coordinates"]

    if photo_box is None or loc_conf < 0.30:
        return {
            "status": "INCONCLUSIVE",
            "confidence": 0.0,
            "reasons": ["Portrait region could not be located on the document"],
            "metrics": {},
            "notes": loc_notes,
        }

    x0, y0, x1, y1 = photo_box
    pw, ph = x1 - x0, y1 - y0

    if pw < 20 or ph < 20 or pw >= w or ph >= h:
        return {
            "status": "INCONCLUSIVE",
            "confidence": 0.0,
            "reasons": ["Detected portrait region is invalid or bounds entire image"],
            "metrics": {},
            "notes": loc_notes,
        }

    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Extract portrait ROI and background ROI (document area outside photo box)
    photo_roi = gray[y0:y1, x0:x1]

    # Background ROI: sample document area to the right or top of photo box
    bg_x0 = min(w - 10, x1 + 10)
    bg_x1 = min(w, bg_x0 + pw)
    bg_roi = gray[y0:y1, bg_x0:bg_x1] if (bg_x1 - bg_x0 > 20) else gray[0:int(h * 0.3), int(w * 0.5):w]

    if photo_roi.size < 100 or bg_roi.size < 100:
        return {
            "status": "INCONCLUSIVE",
            "confidence": 0.0,
            "reasons": ["Insufficient pixel area inside portrait ROI"],
            "metrics": {},
            "notes": loc_notes,
        }

    reasons = []
    suspicion_score = 0.0

    # -------------------------------------------------------------------------
    # INDICATOR 1: Boundary / Perimeter Edge Discontinuity (Seam Artifacts)
    # -------------------------------------------------------------------------
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)

    # Sample perimeter border (5px strip along photo box boundary)
    border_mask = np.zeros_like(gray, dtype=bool)
    pad = 4
    border_mask[max(0, y0-pad):min(h, y0+pad), x0:x1] = True
    border_mask[max(0, y1-pad):min(h, y1+pad), x0:x1] = True
    border_mask[y0:y1, max(0, x0-pad):min(w, x0+pad)] = True
    border_mask[y0:y1, max(0, x1-pad):min(w, x1+pad)] = True

    border_edge = float(edge_mag[border_mask].mean()) if border_mask.any() else 0.0
    photo_interior_edge = float(edge_mag[y0+10:y1-10, x0+10:x1-10].mean()) if (y1-y0 > 20 and x1-x0 > 20) else 1.0

    boundary_ratio = round(border_edge / (photo_interior_edge + 1e-4), 3)
    if boundary_ratio > 2.8:
        suspicion_score += 0.35
        reasons.append(f"Irregular portrait boundary / edge discontinuity around photo region (Ratio: {boundary_ratio})")

    # -------------------------------------------------------------------------
    # INDICATOR 2: Texture / High-Frequency Noise Mismatch
    # -------------------------------------------------------------------------
    photo_lap = float(cv2.Laplacian(photo_roi.astype(np.uint8), cv2.CV_64F).var())
    bg_lap = float(cv2.Laplacian(bg_roi.astype(np.uint8), cv2.CV_64F).var())

    lap_ratio = round(abs(photo_lap - bg_lap) / (bg_lap + 1e-4), 3)
    if lap_ratio > 3.5:
        suspicion_score += 0.30
        reasons.append(f"Texture & noise frequency mismatch between portrait and document background (Variance Diff: {lap_ratio})")

    # -------------------------------------------------------------------------
    # INDICATOR 3: Error Level Analysis (ELA) Compression Discontinuity
    # -------------------------------------------------------------------------
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    diff = ImageChops.difference(img.convert("RGB"), recompressed)
    diff_arr = np.asarray(diff).astype(np.float32).mean(axis=2)

    photo_ela = float(diff_arr[y0:y1, x0:x1].mean())
    bg_ela = float(diff_arr[0:h, 0:w].mean())

    ela_ratio = round(photo_ela / (bg_ela + 1e-4), 3)
    if ela_ratio > 2.2 or ela_ratio < 0.40:
        suspicion_score += 0.25
        reasons.append(f"JPEG compression / ELA response mismatch in portrait region (Ratio: {ela_ratio})")

    # -------------------------------------------------------------------------
    # INDICATOR 4: Color / Illumination Temperature Divergence
    # -------------------------------------------------------------------------
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV)
    photo_hsv = hsv[y0:y1, x0:x1]
    bg_hsv = hsv[y0:y1, bg_x0:bg_x1] if (bg_x1 - bg_x0 > 20) else hsv[0:int(h * 0.3), int(w * 0.5):w]

    hist_photo = cv2.calcHist([photo_hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])
    hist_bg = cv2.calcHist([bg_hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])

    cv2.normalize(hist_photo, hist_photo, alpha=1, beta=0, norm_type=cv2.NORM_L1)
    cv2.normalize(hist_bg, hist_bg, alpha=1, beta=0, norm_type=cv2.NORM_L1)

    color_dist = round(float(cv2.compareHist(hist_photo, hist_bg, cv2.HISTCMP_BHATTACHARYYA)), 3)
    if color_dist > 0.60:
        suspicion_score += 0.20
        reasons.append(f"Illumination & color distribution mismatch in portrait area (Distance: {color_dist})")

    # Final Composite Status & Confidence Calculation
    composite_suspicion = min(1.0, suspicion_score)

    if composite_suspicion >= 0.50 or len(reasons) >= 2:
        status = "SUSPICIOUS"
        confidence = round(min(0.98, 0.70 + composite_suspicion * 0.28), 2)
    else:
        status = "NOT_DETECTED"
        confidence = round(max(0.85, 0.98 - composite_suspicion * 0.20), 2)

    return {
        "status": status,
        "confidence": confidence,
        "reasons": reasons,
        "metrics": {
            "boundaryRatio": boundary_ratio,
            "textureRatio": lap_ratio,
            "elaRatio": ela_ratio,
            "colorDistance": color_dist,
            "suspicionScore": round(composite_suspicion, 3),
        },
        "notes": loc_notes,
    }
