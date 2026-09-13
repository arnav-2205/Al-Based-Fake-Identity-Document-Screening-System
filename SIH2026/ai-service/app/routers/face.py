from fastapi import APIRouter, File, UploadFile

from app.schemas import FaceResult
from app.services import face_engine

router = APIRouter(prefix="/face", tags=["face"])


@router.post("/verify", response_model=FaceResult)
async def verify(
    doc_photo: UploadFile = File(...),
    live_photo: UploadFile | None = File(None),
) -> FaceResult:
    doc = await doc_photo.read()
    live = await live_photo.read() if live_photo is not None else None
    return FaceResult(**face_engine.verify(doc, live))
