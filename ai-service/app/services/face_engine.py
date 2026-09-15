"""Face verification + liveness service connecting to InceptionResnetV1 and MobileNetV3 engines.
"""
from __future__ import annotations

import base64
import io
import re
from PIL import Image

from app.config import settings
from ml.inference.face_inference import FaceVerificationEngine
from ml.inference.liveness_inference import LivenessInferenceEngine

_face_engine: FaceVerificationEngine | None = None
_liveness_engine: LivenessInferenceEngine | None = None

def _get_engines():
    global _face_engine, _liveness_engine
    if _face_engine is None:
        _face_engine = FaceVerificationEngine()
    if _liveness_engine is None:
        _liveness_engine = LivenessInferenceEngine()
    return _face_engine, _liveness_engine

def _to_rgb(data: bytes | None) -> Image.Image:
    if not data:
        return Image.new("RGB", (160, 200), (220, 220, 220))
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        try:
            content = data.decode("utf-8", errors="ignore")
            match = re.search(r'href=["\']data:image/[^;]+;base64,([^"\']+)["\']', content)
            if match:
                b64_data = base64.b64decode(match.group(1))
                return Image.open(io.BytesIO(b64_data)).convert("RGB")
        except Exception:
            pass
        return Image.new("RGB", (160, 200), (220, 220, 220))


def embedding(data: bytes) -> tuple[list[float], list[str]]:
    face_eng, _ = _get_engines()
    img = _to_rgb(data)
    emb = face_eng.extract_embedding(img)
    return emb, ["Face embedding: InceptionResnetV1 (512-D)"]

def liveness(data: bytes) -> tuple[str, list[str]]:
    _, live_eng = _get_engines()
    img = _to_rgb(data)
    res = live_eng.predict(img)
    return res["livenessStatus"], res["notes"]

def verify(doc_photo: bytes, live_photo: bytes | None) -> dict:
    face_eng, live_eng = _get_engines()
    doc_img = _to_rgb(doc_photo)
    doc_emb = face_eng.extract_embedding(doc_img)

    if live_photo is None:
        return {
            "faceMatchScore": 0.0,
            "faceMatchStatus": "UNKNOWN",
            "livenessStatus": "UNKNOWN",
            "embedding": doc_emb,
            "notes": ["No live photo supplied — face match skipped"],
        }

    live_img = _to_rgb(live_photo)
    live_res = live_eng.predict(live_img)
    live_emb = face_eng.extract_embedding(live_img)

    sim_score = face_eng.compare_embeddings(doc_emb, live_emb)
    status = "MATCH" if sim_score >= face_eng.match_threshold else "MISMATCH"
    face_notes = [f"Cosine similarity: {sim_score:.4f} (Decision threshold: {face_eng.match_threshold})"]

    return {
        "faceMatchScore": round(sim_score, 4),
        "faceMatchStatus": status,
        "livenessStatus": live_res["livenessStatus"],
        "embedding": doc_emb,
        "notes": face_notes + live_res["notes"],
    }
