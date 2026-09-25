from typing import Any

from pydantic import BaseModel, Field


class OcrResult(BaseModel):
    mrz: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    mrzFields: dict[str, str] = Field(default_factory=dict)
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
    detectedType: str = "UNKNOWN"
    detectionConfidence: float = 0.0
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
    visaResult: "VisaResult" = Field(default_factory=lambda: VisaResult())
    drivingLicenceResult: "DrivingLicenceResult" = Field(default_factory=lambda: DrivingLicenceResult())
    nationalIdResult: "NationalIdResult" = Field(default_factory=lambda: NationalIdResult())
    permitResult: "PermitResult" = Field(default_factory=lambda: PermitResult())



class VisaResult(BaseModel):
    visaNumber: str | None = None
    visaType: str | None = None
    entryType: str = "UNKNOWN"
    stayDuration: str | None = None
    stayDurationValue: int | None = None
    stayDurationUnit: str | None = None
    issueDate: str | None = None
    expiryDate: str | None = None
    issuingCountry: str | None = None
    status: str = "NOT_APPLICABLE"
    validationMessages: list[str] = Field(default_factory=list)


class DrivingLicenceResult(BaseModel):
    dlNumber: str | None = None
    holderName: str | None = None
    dateOfBirth: str | None = None
    issueDate: str | None = None
    expiryDate: str | None = None
    state: str | None = None
    issuingAuthority: str | None = None
    vehicleClasses: list[str] = Field(default_factory=list)
    barcodeStatus: str = "NOT_AVAILABLE"
    status: str = "NOT_APPLICABLE"
    validationMessages: list[str] = Field(default_factory=list)


class NationalIdResult(BaseModel):
    idNumber: str | None = None
    holderName: str | None = None
    dateOfBirth: str | None = None
    idSubtype: str = "UNKNOWN"
    issueDate: str | None = None
    expiryDate: str | None = None
    address: str | None = None
    gender: str | None = None
    nationality: str | None = None
    qrStatus: str = "NOT_AVAILABLE"
    barcodeStatus: str = "NOT_AVAILABLE"
    status: str = "NOT_APPLICABLE"
    validationMessages: list[str] = Field(default_factory=list)


class PermitResult(BaseModel):
    permitNumber: str | None = None
    permitType: str | None = None
    holderName: str | None = None
    organizationName: str | None = None
    issueDate: str | None = None
    expiryDate: str | None = None
    issuingAuthority: str | None = None
    address: str | None = None
    vehicleAssetIdentifier: str | None = None
    permitCategory: str | None = None
    referenceNumber: str | None = None
    status: str = "NOT_APPLICABLE"
    validationMessages: list[str] = Field(default_factory=list)






class PhotoForgeryResult(BaseModel):
    status: str = "NOT_DETECTED"
    confidence: float = 0.95
    reasons: list[str] = Field(default_factory=list)


class TextManipulationResult(BaseModel):
    status: str = "NOT_DETECTED"
    confidence: float = 0.95
    suspiciousFields: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    fieldResults: dict[str, Any] = Field(default_factory=dict)


class StampForgeryResult(BaseModel):
    status: str = "NOT_DETECTED"
    confidence: float = 0.95
    candidateRegions: list[dict[str, Any]] = Field(default_factory=list)
    indicators: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MetadataAnalysisResult(BaseModel):
    status: str = "NOT_AVAILABLE"
    confidence: float = 0.95
    signals: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class TamperResult(BaseModel):
    tamperingScore: float = 0.0
    photoTampering: float = 0.0
    textTampering: float = 0.0
    stampTampering: float = 0.0
    copyMoveScore: float = 0.0
    fontInconsistencyScore: float = 0.0
    photoForgery: PhotoForgeryResult = Field(default_factory=PhotoForgeryResult)
    textManipulation: TextManipulationResult = Field(default_factory=TextManipulationResult)
    stampForgery: StampForgeryResult = Field(default_factory=StampForgeryResult)
    metadataAnalysis: MetadataAnalysisResult = Field(default_factory=MetadataAnalysisResult)
    elaHeatmapBase64: str | None = None
    exif: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)



class FaceResult(BaseModel):
    faceMatchScore: float = 0.0
    faceMatchStatus: str = "UNKNOWN"
    livenessStatus: str = "UNKNOWN"
    embedding: list[float] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
