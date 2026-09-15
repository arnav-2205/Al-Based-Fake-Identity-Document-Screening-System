"""Copy-move forgery and font/glyph consistency detection.

Complements CNN + ELA in tampering_inference.py by catching tampering
that leaves no compression artifact for ELA to find:

- Copy-move: a region (e.g. a digit) copied from elsewhere in the *same*
  image to overwrite another region. Found via ORB keypoint matching
  within the image, clustering matches by displacement vector — a
  cluster of keypoints sharing one shift vector means a block was moved,
  not just similar texture.
- Font consistency: a reprinted/edited field is often subtly rescaled or
  a different weight than the surrounding printed text. Approximated via
  MSER glyph-height variance within the document's text band.
"""
from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np


def detect_copy_move(
    image_bgr: np.ndarray,
    min_cluster: int = 12,
    grid: int = 15,
    descriptor_thresh: int = 35,
) -> tuple[float, dict]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1500)
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or len(kp) < 30:
        return 0.0, {"matchedClusters": 0, "keypoints": len(kp) if kp else 0}

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(des, des, k=4)

    h, w = gray.shape
    min_self_distance = max(w, h) * 0.04

    displacement_votes: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for group in matches:
        # Filter self match
        non_self = [m for m in group if m.queryIdx != m.trainIdx and m.distance < descriptor_thresh]
        if len(non_self) >= 2:
            # Lowe's ratio test on ORB descriptors
            if non_self[0].distance < 0.75 * non_self[1].distance:
                p1 = np.array(kp[non_self[0].queryIdx].pt)
                p2 = np.array(kp[non_self[0].trainIdx].pt)
                disp = p2 - p1
                if np.linalg.norm(disp) >= min_self_distance:
                    bin_disp = (int(round(disp[0] / grid) * grid), int(round(disp[1] / grid) * grid))
                    displacement_votes[bin_disp].append((non_self[0].queryIdx, non_self[0].trainIdx))

    if not displacement_votes:
        return 0.0, {"matchedClusters": 0, "keypoints": len(kp)}

    best_disp, best_pairs = max(displacement_votes.items(), key=lambda kv: len(kv[1]))
    cluster_size = len(best_pairs)
    score = (
        float(np.clip((cluster_size - min_cluster) / (min_cluster * 3), 0.0, 1.0))
        if cluster_size >= min_cluster
        else 0.0
    )

    return score, {
        "matchedClusters": cluster_size,
        "keypoints": len(kp),
        "dominantShift": [int(best_disp[0]), int(best_disp[1])],
    }


def detect_font_inconsistency(
    image_bgr: np.ndarray,
    text_band: tuple[float, float, float, float] = (0.0, 0.10, 1.0, 0.85),
) -> tuple[float, dict]:
    h, w = image_bgr.shape[:2]
    x0, y0, x1, y1 = text_band
    roi = image_bgr[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    if roi.size == 0:
        return 0.0, {"glyphCount": 0}

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    mser = cv2.MSER_create()
    mser.setMinArea(20)
    mser.setMaxArea(2000)
    regions, _ = mser.detectRegions(gray)

    boxes = []
    for pts in regions:
        bx, by, bw, bh = cv2.boundingRect(pts)
        if 8 <= bh <= 60 and 4 <= bw <= 60 and bw < bh * 2.5:
            boxes.append((bx, by, bw, bh))

    if len(boxes) < 15:
        return 0.0, {"glyphCount": len(boxes)}

    # Group glyphs into text lines by vertical center
    boxes.sort(key=lambda b: (b[1] + b[3] / 2))
    lines = []
    current_line = []
    current_cy = None

    for b in boxes:
        cy = b[1] + b[3] / 2
        if current_cy is None or abs(cy - current_cy) < (b[3] * 0.6 + 4):
            current_line.append(b)
            current_cy = cy if current_cy is None else (current_cy * 0.7 + cy * 0.3)
        else:
            if len(current_line) >= 5:
                lines.append(current_line)
            current_line = [b]
            current_cy = cy

    if len(current_line) >= 5:
        lines.append(current_line)

    if not lines:
        return 0.0, {"glyphCount": len(boxes), "lineCount": 0}

    line_scores = []
    for line in lines:
        heights = np.array([b[3] for b in line], dtype=np.float32)
        med_h = float(np.median(heights))
        mad = float(np.median(np.abs(heights - med_h))) or 1.0
        outliers = float((np.abs(heights - med_h) > mad * 4.0).mean())
        if outliers >= 0.25:
            line_scores.append(outliers)

    if not line_scores:
        return 0.0, {"glyphCount": len(boxes), "lineCount": len(lines), "maxLineInconsistency": 0.0}

    max_line_inconsistency = max(line_scores)
    score = float(np.clip((max_line_inconsistency - 0.25) * 3.0, 0.0, 1.0))

    return score, {
        "glyphCount": len(boxes),
        "lineCount": len(lines),
        "maxLineInconsistency": round(max_line_inconsistency, 4),
    }
