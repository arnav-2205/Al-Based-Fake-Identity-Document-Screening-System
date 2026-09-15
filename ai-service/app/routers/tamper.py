from fastapi import APIRouter, File, UploadFile

from app.schemas import TamperResult
from app.services import tamper_model

router = APIRouter(prefix="/tamper", tags=["tamper"])


@router.post("/analyze", response_model=TamperResult)
def analyze(file: UploadFile = File(...)) -> TamperResult:
    data = file.file.read()
    return TamperResult(**tamper_model.analyse(data, filename=file.filename))
