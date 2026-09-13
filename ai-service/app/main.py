import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI

from app.config import settings
from app.routers import face, ocr, tamper, screening

app = FastAPI(
    title="SIH26188 AI Service",
    version="0.1.0",
    description="Combined AI service: OCR/MRZ, tamper detection, face verification, and unified screening.",
)

app.include_router(ocr.router)
app.include_router(tamper.router)
app.include_router(face.router)
app.include_router(screening.router)


@app.get("/health")
def health():
    return {"status": "ok", "useRealModels": settings.use_real_models}

