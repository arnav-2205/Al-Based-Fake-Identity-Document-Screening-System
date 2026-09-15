"""Stamp Forgery & Digital Manipulation Forensic Analysis Module.

Detects whether visa/document stamps on an identity document appear to have been
digitally altered, copied, duplicated, pasted, or composited.

Independent of generic document tampering score, OCR confidence, photo forgery,
text manipulation, and face verification.
"""
from __future__ import annotations

import io
import math
import cv2
import numpy as np
from PIL import Image, ImageChops
from typing import Dict, Any, List, Tuple, Optional


def detect_stamp_regions(
    img: Image.Image | np.ndarray, ocr_result: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Locates candidate stamp-like regions on the document image using ink color masking and contour geometry.

    Returns:
        List of candidate region dicts [{'x': x, 'y': y, 'width': w, 'height': h, 'score': s}], and notes.
    """
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

    h, w = bgr.shape[:2]
    notes = []

    # Exclude photo region if photo location is available or estimated (left 40% / top 70%)
    photo_x0, photo_y0, photo_x1, photo_y1 = int(w * 0.02), int(h * 0.12), int(w * 0.40), int(h * 0.75)

    # Exclude MRZ region if present (bottom 20%)
    mrz_y0 = int(h * 0.80)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # 1. Color Ink Masking (Blue, Violet, Red, Pink, Green stamp inks)
    # Mask Red / Pink ink
    mask_red1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([12, 255, 255]))
    mask_red2 = cv2.inRange(hsv, np.array([160, 50, 50]), np.array([180, 255, 255]))
    # Mask Blue / Violet / Purple ink
    mask_blue = cv2.inRange(hsv, np.array([85, 45, 40]), np.array([145, 255, 255]))
    # Mask Green / Teal ink
    mask_green = cv2.inRange(hsv, np.array([35, 45, 40]), np.array([84, 255, 255]))

    color_mask = mask_red1 | mask_red2 | mask_blue | mask_green

    # Apply morphological closing to bridge ink strokes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidate_regions: List[Dict[str, Any]] = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 800 or area > (w * h * 0.25):
            continue

        cx, cy, cw, ch = cv2.boundingRect(cnt)
        aspect = max(cw, ch) / (min(cw, ch) + 1e-4)

        if aspect > 2.8:
            continue

        solidity = area / (cw * ch + 1e-4)
        if solidity < 0.20:
            continue

        # Check overlap with photo box
        overlap_x = max(0, min(cx + cw, photo_x1) - max(cx, photo_x0))
        overlap_y = max(0, min(cy + ch, photo_y1) - max(cy, photo_y0))
        if (overlap_x * overlap_y) > (cw * ch * 0.40):
            continue

        # Check overlap with MRZ area
        if cy > mrz_y0:
            continue

        score = round(min(0.95, 0.50 + solidity * 0.40), 2)
        candidate_regions.append({
            "x": int(cx),
            "y": int(cy),
            "width": int(cw),
            "height": int(ch),
            "score": score
        })

    notes.append(f"Stamp localization detected {len(candidate_regions)} candidate region(s)")
    return candidate_regions, notes


def analyze_stamp_forgery(
    img: Image.Image | np.ndarray, ocr_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze stamp candidate regions for digital forgery / compositing anomalies."""
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

    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    candidate_regions, loc_notes = detect_stamp_regions(pil_img, ocr_result)

    if not candidate_regions:
        return {
            "status": "NOT_DETECTED",
            "confidence": 0.95,
            "candidateRegions": [],
            "indicators": {
                "edgeDiscontinuity": 0.0,
                "textureMismatch": 0.0,
                "compressionMismatch": 0.0,
                "colorMismatch": 0.0,
                "duplicationScore": 0.0,
            },
            "reasons": [],
            "notes": loc_notes,
        }

    # Reference background document paper ROI
    bg_roi = gray[int(h * 0.70):int(h * 0.85), int(w * 0.10):int(w * 0.50)]
    if bg_roi.size < 100:
        bg_roi = gray[0:int(h * 0.20), int(w * 0.10):int(w * 0.40)]
    bg_lap = float(cv2.Laplacian(bg_roi.astype(np.uint8), cv2.CV_64F).var()) if bg_roi.size > 0 else 10.0

    # Global ELA reference
    buf = io.BytesIO()
    pil_img.save(buf, "JPEG", quality=90)
    buf.seek(0)
    ela_img = Image.open(buf).convert("RGB")
    ela_diff = np.abs(np.asarray(pil_img, dtype=np.float32) - np.asarray(ela_img, dtype=np.float32))
    ela_gray = cv2.cvtColor(ela_diff.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    bg_ela = float(ela_gray[int(h * 0.70):int(h * 0.85), int(w * 0.10):int(w * 0.50)].mean()) if bg_roi.size > 0 else 1.0

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)

    max_edge_disc = 0.0
    max_tex_mismatch = 0.0
    max_comp_mismatch = 0.0
    max_color_mismatch = 0.0
    max_duplication = 0.0

    reasons: List[str] = []
    max_suspicion_score = 0.0

    triggered_categories = set()

    # 1. Evaluate each candidate stamp region
    for idx, reg in enumerate(candidate_regions):
        x0, y0 = reg["x"], reg["y"]
        x1, y1 = x0 + reg["width"], y0 + reg["height"]

        if (x1 - x0) < 15 or (y1 - y0) < 15:
            continue

        crop_gray = gray[y0:y1, x0:x1]
        crop_ela = ela_gray[y0:y1, x0:x1]
        crop_hsv = hsv[y0:y1, x0:x1]

        reg_suspicion = 0.0

        # Indicator A: Edge / Boundary Step Discontinuity (Cutout/pasting seam)
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)

        border_mask = np.zeros_like(gray, dtype=bool)
        pad = 3
        border_mask[max(0, y0-pad):min(h, y0+pad), x0:x1] = True
        border_mask[max(0, y1-pad):min(h, y1+pad), x0:x1] = True
        border_mask[y0:y1, max(0, x0-pad):min(w, x0+pad)] = True
        border_mask[y0:y1, max(0, x1-pad):min(w, x1+pad)] = True

        border_edge = float(edge_mag[border_mask].mean()) if border_mask.any() else 0.0
        interior_edge = max(1.0, float(edge_mag[y0+3:y1-3, x0+3:x1-3].mean())) if (y1-y0 > 8 and x1-x0 > 8) else 1.0

        boundary_ratio = round(border_edge / interior_edge, 3)
        max_edge_disc = max(max_edge_disc, boundary_ratio)

        if border_edge > 35.0 and boundary_ratio > 3.2:
            reg_suspicion += 0.30
            triggered_categories.add("EDGE")
            reasons.append(f"Suspicious boundary seam / cut-out border around candidate stamp #{idx+1} (Ratio: {boundary_ratio})")

        # Indicator B: Texture & High-Frequency Noise Variance Divergence
        stamp_lap = float(cv2.Laplacian(crop_gray.astype(np.uint8), cv2.CV_64F).var())
        lap_ratio = round(abs(stamp_lap - bg_lap) / (bg_lap + 1e-4), 3)
        max_tex_mismatch = max(max_tex_mismatch, lap_ratio)

        if lap_ratio > 4.5:
            reg_suspicion += 0.25
            triggered_categories.add("TEXTURE")
            reasons.append(f"Texture & noise frequency variance mismatch in candidate stamp #{idx+1} (Ratio: {lap_ratio})")

        # Indicator C: JPEG / ELA Compression Discrepancy (Auxiliary signal - ELA alone cannot cause forgery)
        stamp_ela_val = float(crop_ela.mean()) if crop_ela.size > 0 else 0.0
        ela_ratio = round(stamp_ela_val / (bg_ela + 1e-4), 3)
        max_comp_mismatch = max(max_comp_mismatch, ela_ratio)

        if ela_ratio > 3.5:
            reg_suspicion += 0.15
            triggered_categories.add("ELA")
            reasons.append(f"JPEG compression / ELA response discrepancy in candidate stamp #{idx+1} (Ratio: {ela_ratio})")

        # Indicator D: Color / Ink Discontinuity
        bg_hsv_sample = hsv[int(h * 0.70):int(h * 0.85), int(w * 0.10):int(w * 0.50)]
        if bg_hsv_sample.size > 0:
            stamp_val_mean = float(crop_hsv[:, :, 2].mean())
            bg_val_mean = float(bg_hsv_sample[:, :, 2].mean())
            val_diff = round(abs(stamp_val_mean - bg_val_mean) / (bg_val_mean + 1e-4), 3)
            max_color_mismatch = max(max_color_mismatch, val_diff)
            if val_diff > 0.50:
                reg_suspicion += 0.20
                triggered_categories.add("COLOR")
                reasons.append(f"Unnatural illumination / color step discontinuity around candidate stamp #{idx+1} (Diff: {val_diff})")

        max_suspicion_score = max(max_suspicion_score, reg_suspicion)

    # Indicator E: Duplication / Cloning Clues if multiple stamp candidate regions exist
    if len(candidate_regions) >= 2:
        r1 = candidate_regions[0]
        r2 = candidate_regions[1]
        roi1 = cv2.resize(gray[r1["y"]:r1["y"]+r1["height"], r1["x"]:r1["x"]+r1["width"]], (64, 64))
        roi2 = cv2.resize(gray[r2["y"]:r2["y"]+r2["height"], r2["x"]:r2["x"]+r2["width"]], (64, 64))
        res_cc = cv2.matchTemplate(roi1.astype(np.uint8), roi2.astype(np.uint8), cv2.TM_CCOEFF_NORMED)
        duplication_sim = round(float(res_cc.max()), 3)
        max_duplication = max(0.0, duplication_sim)
        if duplication_sim > 0.92:
            max_suspicion_score += 0.35
            triggered_categories.add("DUPLICATION")
            reasons.append(f"Suspicious near-identical duplicate/cloned stamp structure detected (Similarity: {duplication_sim})")

    # Classification logic (Conservative multi-category rule)
    if len(triggered_categories) >= 2 and triggered_categories != {"ELA"}:
        status = "SUSPICIOUS"
        confidence = round(min(0.98, 0.70 + max_suspicion_score * 0.28), 2)
    elif len(triggered_categories) == 1:
        status = "INCONCLUSIVE"
        confidence = 0.75
        if not any("insufficient" in r for r in reasons):
            reasons.append("Stamp-like region detected but forensic evidence was insufficient for a reliable forgery determination")
    else:
        status = "NOT_DETECTED"
        confidence = 0.95

    return {
        "status": status,
        "confidence": confidence,
        "candidateRegions": candidate_regions,
        "indicators": {
            "edgeDiscontinuity": max_edge_disc,
            "textureMismatch": max_tex_mismatch,
            "compressionMismatch": max_comp_mismatch,
            "colorMismatch": max_color_mismatch,
            "duplicationScore": max_duplication,
        },
        "reasons": reasons,
        "notes": loc_notes,
    }
