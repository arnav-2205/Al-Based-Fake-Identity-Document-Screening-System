from typing import Any

from pydantic import BaseModel, Field


class OcrResult(BaseModel):
    mrz: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    visualZone: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    mrzValid: bool = False
    mrzChecks: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    detectedDocumentType: str = "UNKNOWN"
    extractionTimeMs: float = 0.0


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
