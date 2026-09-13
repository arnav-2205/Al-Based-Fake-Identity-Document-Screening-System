from typing import Any

from pydantic import BaseModel, Field


class OcrResult(BaseModel):
    mrz: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    visualZone: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    fieldExtractionConfidence: float = 0.0
    rawOcrConfidence: float = 0.0
    fieldConfidences: dict[str, float] = Field(default_factory=dict)
    fieldStates: dict[str, str] = Field(default_factory=dict)
    mrzValid: bool = False
    mrzChecks: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    detectedDocumentType: str = "UNKNOWN"
    documentCategory: str = "NATIONAL_ID"
    documentSubtype: str = "NATIONAL_ID_CARD"
    applicableFields: list[str] = Field(default_factory=list)
    applicableChecks: list[str] = Field(default_factory=list)
    issuingCountry: str = "UNKNOWN"
    extractionTimeMs: float = 0.0
    qrDetected: bool = False
    qrDecoded: bool = False
    qrSignatureVerified: bool = False
    qrSignatureStatus: str = "NOT_AVAILABLE"
    qrOcrMatchStatus: str = "NOT_APPLICABLE"
    qrOcrDiscrepancies: list[str] = Field(default_factory=list)
    barcodeDetected: bool = False
    barcodeDecoded: bool = False
    barcodeParsed: bool = False
    barcodeValidated: bool = False
    barcodeStatus: str = "NOT_AVAILABLE"
    barcodeType: str = "NONE"
    barcodeData: Any | None = None
    barcodeCrossCheckStatus: str = "NOT_APPLICABLE"
    mrzStatus: str = "NOT_AVAILABLE"



class TamperResult(BaseModel):
    tamperingScore: float = 0.0
    photoTampering: float = 0.0
    textTampering: float = 0.0
    stampTampering: float = 0.0
    copyMoveScore: float = 0.0
    fontInconsistencyScore: float = 0.0
    elaHeatmapBase64: str | None = None
    exif: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class FaceResult(BaseModel):
    faceMatchScore: float = 0.0
    faceMatchStatus: str = "UNKNOWN"
    livenessStatus: str = "UNKNOWN"
    embedding: list[float] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
