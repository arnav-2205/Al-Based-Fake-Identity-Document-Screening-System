from fastapi import APIRouter, File, UploadFile

from app.schemas import OcrResult
from app.services import ocr_engine

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/extract", response_model=OcrResult)
async def extract(file: UploadFile = File(...)) -> OcrResult:
    data = await file.read()
    return OcrResult(**ocr_engine.extract(data))
