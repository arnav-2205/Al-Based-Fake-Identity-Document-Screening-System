"""Unified Screening API Router.
Exposes the complete end-to-end multi-modal document verification pipeline via FastAPI.
"""
import io
import sys
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional
from PIL import Image

# Ensure ml package is in path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.inference.document_pipeline import UnifiedDocumentVerificationPipeline

router = APIRouter(prefix="/ml", tags=["unified-screening"])
pipeline = UnifiedDocumentVerificationPipeline()

@router.post("/verify-document")
async def verify_document(
    document: UploadFile = File(...),
    live_photo: Optional[UploadFile] = File(None),
    raw_mrz: Optional[str] = Form(None)
):
    doc_bytes = await document.read()
    doc_img = Image.open(io.BytesIO(doc_bytes))
    
    live_img = None
    if live_photo:
        live_bytes = await live_photo.read()
        live_img = Image.open(io.BytesIO(live_bytes))
        
    result = pipeline.verify_document(
        document_image=doc_img,
        live_photo=live_img,
        raw_mrz_override=raw_mrz
    )
    return result

@router.post("/tampering")
async def check_tampering(document: UploadFile = File(...)):
    doc_bytes = await document.read()
    doc_img = Image.open(io.BytesIO(doc_bytes))
    return pipeline.tamper_engine.predict(doc_img)

@router.post("/face-verification")
async def face_verification(
    doc_photo: UploadFile = File(...),
    live_photo: Optional[UploadFile] = File(None)
):
    doc_bytes = await doc_photo.read()
    doc_img = Image.open(io.BytesIO(doc_bytes))
    live_img = None
    if live_photo:
        live_bytes = await live_photo.read()
        live_img = Image.open(io.BytesIO(live_bytes))
    return pipeline.face_engine.verify(doc_img, live_img)

@router.post("/liveness")
async def check_liveness(live_photo: UploadFile = File(...)):
    live_bytes = await live_photo.read()
    live_img = Image.open(io.BytesIO(live_bytes))
    return pipeline.liveness_engine.predict(live_img)
