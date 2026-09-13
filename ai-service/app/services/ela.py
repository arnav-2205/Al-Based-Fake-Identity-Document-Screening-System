"""Error Level Analysis (Spec Part 1, cases #2, #3, #13).

Recompresses the image at a known JPEG quality and measures the per-pixel
difference. Regions that were digitally edited compress differently and
light up in the ELA map. Returns a normalised tamper score plus a
base64 PNG heatmap for the officer dashboard.
"""
from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image, ImageChops


def _to_rgb(data: bytes) -> Image.Image:
    if not data:
        return Image.new("RGB", (600, 400), (15, 23, 42))
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        # SVG / Vector format representation
        img = Image.new("RGB", (600, 400), (15, 23, 42))
        return img


def error_level_analysis(data: bytes, quality: int = 90) -> tuple[float, str, dict]:
    original = _to_rgb(data)

    buf = io.BytesIO()
    original.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")

    diff = ImageChops.difference(original, recompressed)
    arr = np.asarray(diff).astype(np.float32)

    # per-pixel magnitude
    mag = arr.mean(axis=2)
    max_mag = float(mag.max()) or 1.0
    norm = mag / max_mag

    # tamper score: fraction of pixels with a strong ELA response, plus
    # the spread of the response (edited regions create localised hot spots)
    hot_fraction = float((norm > 0.35).mean())
    spread = float(norm.std())
    score = float(np.clip(0.6 * hot_fraction * 6.0 + 0.4 * spread * 3.0, 0.0, 1.0))

    # build heatmap PNG (amplified for visibility)
    heat = np.clip(norm * 255.0 * 3.0, 0, 255).astype(np.uint8)
    heat_img = Image.fromarray(heat).convert("L")
    out = io.BytesIO()
    heat_img.save(out, "PNG")
    b64 = base64.b64encode(out.getvalue()).decode("ascii")

    stats = {
        "hotFraction": round(hot_fraction, 4),
        "responseSpread": round(spread, 4),
        "recompressQuality": quality,
    }
    return score, b64, stats


def region_scores(data: bytes) -> dict[str, float]:
    original = _to_rgb(data)
    w, h = original.size

    buf = io.BytesIO()
    original.save(buf, "JPEG", quality=90)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    arr = np.asarray(ImageChops.difference(original, recompressed)).astype(np.float32).mean(axis=2)
    m = float(arr.max()) or 1.0
    norm = arr / m

    def band(x0, y0, x1, y1) -> float:
        sub = norm[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        if sub.size == 0:
            return 0.0
        return float(np.clip((sub > 0.35).mean() * 6.0, 0.0, 1.0))

    return {
        "photo": round(band(0.0, 0.0, 0.35, 0.75), 4),
        "text": round(band(0.35, 0.15, 1.0, 0.75), 4),
        "stamp": round(band(0.45, 0.6, 1.0, 1.0), 4),
    }
