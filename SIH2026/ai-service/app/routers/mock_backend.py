"""Mock backend API routes that replace the Spring Boot backend for standalone demo.

Provides: /api/auth/login, /api/documents/upload, /api/verification/start,
/api/verification/{id}, /api/verification/{id}/integrity-check,
/api/verification/{id}/decision, /api/blacklist
"""
from __future__ import annotations

import hashlib
import io
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["mock-backend"])

# ── In-memory stores ──────────────────────────────────────────────────
_USERS = {
    "officer1": {"password": "password", "name": "Inspector Sharma", "role": "OFFICER"},
    "admin": {"password": "admin123", "name": "Admin Verma", "role": "ADMIN"},
    "demo": {"password": "demo", "name": "Demo User", "role": "VIEWER"},
}

_tokens: dict[str, dict[str, str]] = {}          # token -> user info
_documents: dict[int, dict[str, Any]] = {}        # docId -> doc data
_verifications: dict[int, dict[str, Any]] = {}    # verId -> verification result
_next_doc_id = 1
_next_ver_id = 1

_BLACKLIST = [
    {
        "id": 1,
        "documentNumber": "Z9876543",
        "documentType": "PASSPORT",
        "name": "Rajesh Kumar (Fake)",
        "dateOfBirth": "1985-03-15",
        "reason": "Interpol Red Notice — Identity fraud",
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "documentNumber": "AB1234567",
        "documentType": "PASSPORT",
        "name": "Unknown Alias",
        "dateOfBirth": "1990-07-22",
        "reason": "Document forgery syndicate link",
        "status": "ACTIVE",
    },
    {
        "id": 3,
        "documentNumber": "DL-0420199000123",
        "documentType": "DRIVING_LICENCE",
        "name": "Deepak Singh (Fake)",
        "dateOfBirth": "1992-11-08",
        "reason": "Multiple fraudulent IDs seized",
        "status": "SUSPENDED",
    },
    {
        "id": 4,
        "documentNumber": "NATID-7788001",
        "documentType": "NATIONAL_ID",
        "name": "Priya Mehta (Alias)",
        "dateOfBirth": "1988-01-30",
        "reason": "Wanted — Financial fraud",
        "status": "ACTIVE",
    },
]


# ── Auth ──────────────────────────────────────────────────────────────

class LoginReq(BaseModel):
    officerId: str
    password: str


@router.post("/auth/login")
def login(body: LoginReq):
    user = _USERS.get(body.officerId)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = f"tok_{uuid.uuid4().hex}"
    info = {"officerId": body.officerId, "name": user["name"], "role": user["role"], "token": token}
    _tokens[token] = info
    return info


# ── Document upload ───────────────────────────────────────────────────

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    documentType: str = Form("PASSPORT"),
):
    global _next_doc_id
    raw = await file.read()
    doc_id = _next_doc_id
    _next_doc_id += 1
    _documents[doc_id] = {
        "documentId": doc_id,
        "documentType": documentType,
        "filename": file.filename,
        "bytes": raw,
        "uploadedAt": datetime.utcnow().isoformat(),
    }
    return {"documentId": doc_id, "documentType": documentType, "filename": file.filename}


# ── Verification ──────────────────────────────────────────────────────

@router.post("/verification/start")
async def start_verification(
    documentId: int = Form(...),
    liveFace: UploadFile | None = File(None),
):
    global _next_ver_id

    doc = _documents.get(documentId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Upload first.")

    live_bytes = await liveFace.read() if liveFace else None

    # ── Run the real ML pipeline via the AI service ────────────────
    from PIL import Image
    doc_img = Image.open(io.BytesIO(doc["bytes"]))
    live_img = Image.open(io.BytesIO(live_bytes)) if live_bytes else None

    try:
        from app.services import ocr_engine, face_engine
        from app.services import tamper_model

        ocr_result = ocr_engine.extract(doc["bytes"])
        tamper_result = tamper_model.analyse(doc["bytes"])
        face_result = face_engine.verify(doc["bytes"], live_bytes)
        result = {
            "ocr": ocr_result,
            "tampering": tamper_result,
            "face": face_result,
            "risk": _score_risk(ocr_result, tamper_result, face_result),
        }
    except Exception as exc:
        try:
            from ml.inference.document_pipeline import UnifiedDocumentVerificationPipeline
            pipeline = UnifiedDocumentVerificationPipeline()
            result = pipeline.verify_document(doc_img, live_photo=live_img, document_type=doc["documentType"])
        except Exception:
            result = _stub_result(doc, str(exc))

    # Build record hash
    record_str = f"{documentId}|{result.get('risk', {}).get('riskScore', 0)}|{time.time()}"
    record_hash = hashlib.sha256(record_str.encode()).hexdigest()

    ver_id = _next_ver_id
    _next_ver_id += 1

    ocr = result.get("ocr", {})
    tampering = result.get("tampering", {})
    face = result.get("face", {})
    risk = result.get("risk", {})
    fields = ocr.get("fields", {})

    verification: dict[str, Any] = {
        "verificationId": ver_id,
        "documentId": documentId,
        "documentType": doc["documentType"],
        "extracted": {
            "name": fields.get("name") or "",
            "passportNumber": fields.get("passportNumber") or fields.get("documentNumber") or "",
            "nationality": fields.get("nationality") or "",
            "dateOfBirth": fields.get("dateOfBirth") or "",
            "gender": fields.get("gender") or "",
            "issueDate": fields.get("issueDate") or "",
            "expiryDate": fields.get("expiryDate") or "",
            "mrz": ocr.get("mrz") or "",
            "ocrConfidence": ocr.get("confidence", 0.0),
            "visualZone": ocr.get("visualZone", {}),
        },
        "ocrStatus": "COMPLETE" if ocr.get("mrz") else "PARTIAL",
        "validationStatus": "VALID" if ocr.get("mrzValid") else "INVALID",
        "tamperingScore": tampering.get("tamperingScore", 0.0),
        "photoTampering": tampering.get("photoTampering", 0.0),
        "textTampering": tampering.get("textTampering", 0.0),
        "stampTampering": tampering.get("stampTampering", 0.0),
        "elaHeatmapBase64": tampering.get("elaHeatmapBase64"),
        "faceMatchScore": face.get("faceMatchScore", 0.0),
        "faceMatchStatus": face.get("faceMatchStatus", "UNKNOWN"),
        "livenessStatus": face.get("livenessStatus", "UNKNOWN"),
        "blacklistStatus": "CLEAR",
        "riskScore": risk.get("riskScore", 0),
        "riskLevel": risk.get("riskLevel", "LOW"),
        "finalResult": risk.get("recommendation", "ACCEPT"),
        "reasons": risk.get("reasons", []),
        "recordHash": record_hash,
        "blockchainTxId": f"0x{hashlib.sha256(record_hash.encode()).hexdigest()[:40]}",
        "createdAt": datetime.utcnow().isoformat(),
        "decision": None,
    }

    _verifications[ver_id] = verification
    return {"verificationId": ver_id}


@router.get("/verification/{vid}")
def get_verification(vid: int):
    v = _verifications.get(vid)
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")
    return v


@router.get("/verification/{vid}/integrity-check")
def integrity_check(vid: int):
    v = _verifications.get(vid)
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")
    return {
        "integrityStatus": "INTACT",
        "currentHash": v["recordHash"],
        "ledgerHash": v["recordHash"],
    }


class DecisionReq(BaseModel):
    decision: str


@router.post("/verification/{vid}/decision")
def officer_decision(vid: int, body: DecisionReq):
    v = _verifications.get(vid)
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")
    v["decision"] = body.decision
    return {"status": "ok", "decision": body.decision}


# ── Blacklist ─────────────────────────────────────────────────────────

@router.get("/blacklist")
def list_blacklist():
    return _BLACKLIST


# ── Verification history ─────────────────────────────────────────────

@router.get("/verification")
def list_verifications():
    return sorted(_verifications.values(), key=lambda v: v["verificationId"], reverse=True)


# ── Stub fallback result ─────────────────────────────────────────────

def _score_risk(ocr: dict, tampering: dict, face: dict) -> dict:
    tamper_score = float(tampering.get("tamperingScore") or 0.0)
    face_score = float(face.get("faceMatchScore") or 0.0)
    mrz_valid = bool(ocr.get("mrzValid"))
    risk = int(min(100, tamper_score * 60 + (0 if mrz_valid else 20) + (20 if face_score < 0.5 else 0)))
    level = "HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW"
    recommendation = "REJECT" if risk >= 70 else "MANUAL_REVIEW" if risk >= 40 else "CLEAR"
    reasons = list(ocr.get("notes") or []) + list(tampering.get("notes") or []) + list(face.get("notes") or [])
    return {
        "riskScore": risk,
        "riskLevel": level,
        "recommendation": recommendation,
        "reasons": reasons,
    }


def _stub_result(doc: dict, error_msg: str) -> dict:
    return {
        "ocr": {
            "mrz": "",
            "fields": {},
            "visualZone": {},
            "confidence": 0.0,
            "mrzValid": False,
            "notes": [f"ML pipeline error: {error_msg}"],
        },
        "tampering": {
            "tamperingScore": 0.0,
            "photoTampering": 0.0,
            "textTampering": 0.0,
            "stampTampering": 0.0,
            "elaHeatmapBase64": None,
            "exif": {},
            "notes": [],
        },
        "face": {
            "faceMatchScore": 0.0,
            "faceMatchStatus": "UNKNOWN",
            "livenessStatus": "UNKNOWN",
            "notes": [],
        },
        "risk": {
            "riskScore": 0,
            "riskLevel": "LOW",
            "recommendation": "MANUAL_REVIEW",
            "reasons": [f"Automated analysis unavailable: {error_msg}"],
        },
    }
