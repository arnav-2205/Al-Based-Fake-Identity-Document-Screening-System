# AI Service (FastAPI)

Combined service with three routers — OCR/MRZ, tamper detection, face verification.

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
```

Docs: http://localhost:8000/docs

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/ocr/extract` | `file` (image) | MRZ text, extracted fields, ICAO 9303 check-digit results |
| POST | `/tamper/analyze` | `file` (image) | composite + per-region tamper scores, base64 ELA heatmap, EXIF findings |
| POST | `/face/verify` | `doc_photo`, optional `live_photo` | cosine match score, match status, liveness status, embedding |
| GET | `/health` | — | status |

## Real vs. stub models

Set `AI_USE_REAL_MODELS=true` and `pip install -r requirements-models.txt` to enable
PaddleOCR, the forgery CNN, and InsightFace. Otherwise:

- **OCR** returns a demo MRZ unless the image carries an `<MRZ>...</MRZ>` EXIF sidecar.
- **Tamper** runs real ELA + EXIF analysis (no model needed).
- **Face** uses a deterministic hash-of-image pseudo-embedding.

To drive the demo with specific MRZ data, embed it in the image's EXIF UserComment as
`<MRZ>LINE1\nLINE2</MRZ>`.
