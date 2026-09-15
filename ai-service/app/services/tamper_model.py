"""Forgery / tamper classification connecting to trained EfficientNet-B0 and multi-signal heuristics.
"""
from __future__ import annotations

import io
from PIL import Image

from app.config import settings
from ml.inference.tampering_inference import TamperingInferenceEngine

_engine: TamperingInferenceEngine | None = None

def _get_engine() -> TamperingInferenceEngine:
    global _engine
    if _engine is None:
        _engine = TamperingInferenceEngine()
    return _engine

def _to_rgb(data: bytes | None) -> Image.Image:
    if not data:
        return Image.new("RGB", (600, 400), (15, 23, 42))
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return Image.new("RGB", (600, 400), (15, 23, 42))

def analyse(data: bytes, ocr_result: dict | None = None, filename: str | None = None) -> dict:
    img = _to_rgb(data)
    engine = _get_engine()
    res = engine.predict(img, ocr_result=ocr_result, raw_data=data, filename=filename)
    return {
        "tamperingScore": res["tamperingScore"],
        "photoTampering": res["photoTampering"],
        "textTampering": res["textTampering"],
        "stampTampering": res["stampTampering"],
        "copyMoveScore": res["copyMoveScore"],
        "fontInconsistencyScore": res["fontInconsistencyScore"],
        "photoForgery": res.get("photoForgery", {"status": "NOT_DETECTED", "confidence": 0.95, "reasons": []}),
        "textManipulation": res.get("textManipulation", {"status": "NOT_DETECTED", "confidence": 0.95, "suspiciousFields": [], "reasons": [], "fieldResults": {}}),
        "stampForgery": res.get("stampForgery", {"status": "NOT_DETECTED", "confidence": 0.95, "candidateRegions": [], "reasons": []}),
        "metadataAnalysis": res.get("metadataAnalysis", {"status": "NOT_AVAILABLE", "confidence": 0.95, "signals": [], "metadata": {}, "reasons": []}),
        "elaHeatmapBase64": res["elaHeatmapBase64"],
        "exif": res["exif"],
        "notes": res["notes"],
    }
