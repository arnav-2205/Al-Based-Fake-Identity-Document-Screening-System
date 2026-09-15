"""Text Manipulation & Field Compositing Forensic Analysis Module.

Detects whether important textual fields on an identity document (Name, DOB, Passport/Document Number,
Nationality, Gender, Dates, etc.) appear to have been digitally modified, replaced, erased, or composited.

Independent of OCR confidence, MRZ checksum validation, photo replacement, and face verification.
"""
from __future__ import annotations

import io
import math
import re
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional


KEY_FIELDS = (
    "name", "holderName", "passportNumber", "documentNumber",
    "dateOfBirth", "dob", "nationality", "gender", "sex",
    "issueDate", "expiryDate", "address"
)


def _to_pil_and_cv(img: Image.Image | np.ndarray) -> Tuple[Image.Image, np.ndarray]:
    """Convert input image to both PIL Image and OpenCV BGR ndarray."""
    if isinstance(img, np.ndarray):
        bgr = img.copy()
        if len(bgr.shape) == 2:
            bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
    else:
        pil_img = img.convert("RGB")
        rgb = np.asarray(pil_img)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return pil_img, bgr


def _clean_str(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s).upper().strip())


def localize_field_boxes(
    w: int, h: int, fields: Dict[str, Any], ocr_boxes: List[Dict[str, Any]]
) -> Dict[str, Tuple[int, int, int, int]]:
    """Associate extracted text fields with spatial bounding boxes (x0, y0, x1, y1)."""
    field_rois: Dict[str, Tuple[int, int, int, int]] = {}
    if not fields or not ocr_boxes:
        return field_rois

    for field_name in KEY_FIELDS:
        val = fields.get(field_name)
        if not val or not str(val).strip():
            continue
        clean_val = _clean_str(val)
        if len(clean_val) < 2:
            continue

        matched_boxes = []
        for b in ocr_boxes:
            raw_t = b.get("text", "")
            # Skip MRZ payload lines for precise visual zone field localization
            if "<" in raw_t or len(raw_t) > 35:
                continue
            b_text = _clean_str(raw_t)
            if not b_text:
                continue
            # Match if clean field value contains box text or box text contains field value
            if clean_val in b_text or b_text in clean_val or (len(clean_val) >= 4 and clean_val in b_text):
                matched_boxes.append(b)

        if matched_boxes:
            x0 = max(0, min(b["xmin"] for b in matched_boxes) - 6)
            y0 = max(0, min(b["ymin"] for b in matched_boxes) - 4)
            x1 = min(w, max(b["xmax"] for b in matched_boxes) + 6)
            y1 = min(h, max(b["ymax"] for b in matched_boxes) + 4)
            if (x1 - x0) >= 15 and (y1 - y0) >= 10:
                field_rois[field_name] = (int(x0), int(y0), int(x1), int(y1))

    return field_rois


def analyze_text_manipulation(
    img: Image.Image | np.ndarray, ocr_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze document image text fields for digital manipulation / patch overlay anomalies."""
    pil_img, bgr = _to_pil_and_cv(img)
    w, h = pil_img.size
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    fields = ocr_result.get("fields", {}) if ocr_result else {}
    vz = ocr_result.get("visualZone", {}) if ocr_result else {}
    ocr_boxes = (ocr_result.get("ocrBoxes") if ocr_result else None) or vz.get("ocrBoxes") or []

    # Localize field bounding boxes
    field_rois = localize_field_boxes(w, h, fields, ocr_boxes)

    # If no OCR bounding boxes match, try heuristic position sampling for passport/ID text zones
    if not field_rois and fields:
        # Default sampling zones for passport number (top-right) and DOB/Name (middle left)
        if fields.get("passportNumber") or fields.get("documentNumber"):
            fn = "passportNumber" if fields.get("passportNumber") else "documentNumber"
            field_rois[fn] = (int(w * 0.55), int(h * 0.12), int(w * 0.92), int(h * 0.28))
        if fields.get("dateOfBirth"):
            field_rois["dateOfBirth"] = (int(w * 0.35), int(h * 0.45), int(w * 0.75), int(h * 0.60))

    if not field_rois:
        return {
            "status": "NOT_DETECTED",
            "confidence": 0.95,
            "suspiciousFields": [],
            "reasons": [],
            "fieldResults": {},
            "notes": ["No key text field coordinates localized for forensic inspection"]
        }

    # Extract background paper sample (middle document area free of photos)
    bg_roi = gray[int(h * 0.70):int(h * 0.85), int(w * 0.10):int(w * 0.50)]
    if bg_roi.size < 100:
        bg_roi = gray[0:int(h * 0.20), int(w * 0.10):int(w * 0.40)]

    bg_lap = float(cv2.Laplacian(bg_roi.astype(np.uint8), cv2.CV_64F).var()) if bg_roi.size > 0 else 10.0

    # ELA global reference image
    buf = io.BytesIO()
    pil_img.save(buf, "JPEG", quality=90)
    buf.seek(0)
    ela_img = Image.open(buf).convert("RGB")
    ela_diff = np.abs(np.asarray(pil_img, dtype=np.float32) - np.asarray(ela_img, dtype=np.float32))
    ela_gray = cv2.cvtColor(ela_diff.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    bg_ela = float(ela_gray[int(h * 0.70):int(h * 0.85), int(w * 0.10):int(w * 0.50)].mean()) if bg_roi.size > 0 else 1.0

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)

    suspicious_fields: List[str] = []
    global_reasons: List[str] = []
    field_results: Dict[str, Any] = {}
    total_anomaly_score = 0.0

    for field_name, (x0, y0, x1, y1) in field_rois.items():
        field_w, field_h = x1 - x0, y1 - y0
        if field_w < 10 or field_h < 8:
            continue

        crop_gray = gray[y0:y1, x0:x1]
        crop_hsv = hsv[y0:y1, x0:x1]
        crop_ela = ela_gray[y0:y1, x0:x1]

        field_reasons = []
        field_suspicion = 0.0

        # ---------------------------------------------------------------------
        # INDICATOR 1: Perimeter Seam / Boundary Step Discontinuity (Overlay Patch)
        # ---------------------------------------------------------------------
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)

        border_mask = np.zeros_like(gray, dtype=bool)
        pad = 2
        border_mask[max(0, y0-pad):min(h, y0+pad), x0:x1] = True
        border_mask[max(0, y1-pad):min(h, y1+pad), x0:x1] = True
        border_mask[y0:y1, max(0, x0-pad):min(w, x0+pad)] = True
        border_mask[y0:y1, max(0, x1-pad):min(w, x1+pad)] = True

        border_edge = float(edge_mag[border_mask].mean()) if border_mask.any() else 0.0
        interior_edge = max(1.0, float(edge_mag[y0+2:y1-2, x0+2:x1-2].mean())) if (y1-y0 > 6 and x1-x0 > 6) else 1.0

        boundary_ratio = round(border_edge / interior_edge, 3)
        if border_edge > 35.0 and boundary_ratio > 3.5:
            field_suspicion += 0.30
            field_reasons.append(f"Abnormal boundary seam / overlay patch border around {field_name} (Ratio: {boundary_ratio})")

        # ---------------------------------------------------------------------
        # INDICATOR 2: Texture / High-Frequency Noise Inconsistency
        # ---------------------------------------------------------------------
        field_lap = float(cv2.Laplacian(crop_gray.astype(np.uint8), cv2.CV_64F).var())
        lap_ratio = round(abs(field_lap - bg_lap) / (bg_lap + 1e-4), 3)

        if lap_ratio > 3.0:
            field_suspicion += 0.25
            field_reasons.append(f"Abnormal local texture & high-frequency noise variance on {field_name} (Ratio: {lap_ratio})")

        # ---------------------------------------------------------------------
        # INDICATOR 3: ELA Compression Discrepancy
        # ---------------------------------------------------------------------
        field_ela_val = float(crop_ela.mean()) if crop_ela.size > 0 else 0.0
        ela_ratio = round(field_ela_val / (bg_ela + 1e-4), 3)

        if ela_ratio > 3.0:
            field_suspicion += 0.30
            field_reasons.append(f"JPEG compression / ELA response discrepancy in {field_name} text box (Ratio: {ela_ratio})")

        # ---------------------------------------------------------------------
        # INDICATOR 4: Color / Illumination Step Discontinuity
        # ---------------------------------------------------------------------
        bg_hsv = hsv[int(h * 0.70):int(h * 0.85), int(w * 0.10):int(w * 0.50)]
        if bg_hsv.size > 0:
            field_val_mean = float(crop_hsv[:, :, 2].mean())
            bg_val_mean = float(bg_hsv[:, :, 2].mean())
            val_diff = round(abs(field_val_mean - bg_val_mean) / (bg_val_mean + 1e-4), 3)
            if val_diff > 0.45:
                field_suspicion += 0.20
                field_reasons.append(f"Local paper brightness / illumination step discontinuity around {field_name} (Diff: {val_diff})")

        field_ocr_conf = 0.90
        if ocr_result:
            fc_dict = ocr_result.get("fieldConfidences", {})
            field_ocr_conf = fc_dict.get(field_name, 0.90)

        # Requirement 3: Low OCR confidence alone -> NOT manipulation
        if field_ocr_conf < 0.40:
            is_field_suspicious = False
            field_status = "NOT_DETECTED"
            field_conf = round(field_ocr_conf, 2)
            field_reasons = [f"Low OCR quality / read confidence ({field_ocr_conf}) on {field_name}"]
        else:
            # Require multi-indicator agreement (field_suspicion >= 0.45) for SUSPICIOUS verdict
            is_field_suspicious = field_suspicion >= 0.45
            field_status = "SUSPICIOUS" if is_field_suspicious else "NOT_DETECTED"
            field_conf = round(min(0.98, max(0.60, 0.50 + field_suspicion)), 2)

        field_results[field_name] = {
            "status": field_status,
            "confidence": field_conf,
            "reasons": field_reasons,
            "metrics": {
                "boundaryRatio": boundary_ratio,
                "textureRatio": lap_ratio,
                "elaRatio": ela_ratio,
                "suspicionScore": round(field_suspicion, 3),
            },
            "roi": [x0, y0, x1, y1]
        }

        if is_field_suspicious:
            suspicious_fields.append(field_name)
            global_reasons.extend(field_reasons)
            total_anomaly_score += field_suspicion

    status = "SUSPICIOUS" if len(suspicious_fields) > 0 else "NOT_DETECTED"
    confidence = round(min(0.96, max(0.70, 0.85 + (0.10 if status == "SUSPICIOUS" else 0.10))), 2)

    return {
        "status": status,
        "confidence": confidence,
        "suspiciousFields": suspicious_fields,
        "reasons": global_reasons,
        "fieldResults": field_results,
    }
