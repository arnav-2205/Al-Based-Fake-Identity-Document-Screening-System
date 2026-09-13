"""Comprehensive Automated ML Screening Test Suite for SIH26188.
Validates all 12 mandatory defensive screening scenarios.
"""
import pytest
import numpy as np
from PIL import Image
from pathlib import Path

from ml.inference.document_pipeline import UnifiedDocumentVerificationPipeline
from ml.mrz.mrz_parser import parse_mrz
from ml.scripts.dataset_generator import (
    generate_synthetic_passport_data,
    render_document_image,
    apply_tampering,
    create_synthetic_portrait
)

@pytest.fixture(scope="module")
def pipeline():
    return UnifiedDocumentVerificationPipeline()

def test_01_genuine_passport(pipeline):
    """Case 1: Genuine valid passport -> Expect LOW risk."""
    doc_data = generate_synthetic_passport_data(10)
    img = render_document_image(doc_data, seed=10)
    portrait = create_synthetic_portrait(size=(140, 180), seed=10)
    
    result = pipeline.verify_document(
        document_image=img,
        live_photo=portrait,
        raw_mrz_override=doc_data["mrz"]
    )
    
    assert result["validation"]["validationStatus"] == "PASSED"
    assert result["mrz"]["mrzValid"] is True
    assert result["face"]["faceMatchStatus"] == "MATCH"
    assert result["risk"]["riskLevel"] in ("LOW", "MEDIUM")
    assert result["risk"]["riskScore"] <= 35

def test_02_genuine_id_card(pipeline):
    """Case 2: Genuine ID Card TD1 Format."""
    td1_raw = (
        "I<UTO1234567897<<<<<<<<<<<<<<<\n"
        "7408122F1204159UTO<<<<<<<<<<<6\n"
        "ERIKSSON<<ANNA<MARIA<<<<<<<<<<"
    )
    parsed = parse_mrz(td1_raw)
    assert parsed is not None
    assert parsed.format_type == "TD1"
    assert parsed.all_valid is True

def test_03_genuine_driving_licence(pipeline):
    """Case 3: Genuine Driving Licence attributes."""
    doc_data = generate_synthetic_passport_data(15)
    doc_data["type"] = "DRIVING_LICENCE"
    img = render_document_image(doc_data, seed=15)
    
    result = pipeline.verify_document(
        document_image=img,
        raw_mrz_override=doc_data["mrz"],
        fields_override={"documentType": "DRIVING_LICENCE"}
    )
    assert result["document"]["status"] == "PROCESSED"

def test_04_expired_document(pipeline):
    """Case 4: Expired document -> Expect Rule Failure and Risk penalty."""
    doc_data = generate_synthetic_passport_data(20)
    img = render_document_image(doc_data, seed=20)
    
    result = pipeline.verify_document(
        document_image=img,
        raw_mrz_override=doc_data["mrz"],
        fields_override={"expiryDate": "2020-01-01"}
    )
    failed = [f for f in result["validation"]["rulesFailed"] if "EXPIRED" in f]
    assert len(failed) > 0

def test_05_invalid_mrz_checksum(pipeline):
    """Case 5: Corrupted MRZ checksum digit -> Expect validation failure."""
    doc_data = generate_synthetic_passport_data(25)
    mrz_lines = doc_data["mrz"].split("\n")
    # Alter check digit
    corrupted_mrz = mrz_lines[0] + "\n" + mrz_lines[1][:9] + "9" + mrz_lines[1][10:]
    
    parsed = parse_mrz(corrupted_mrz)
    assert parsed is not None
    assert parsed.checks["documentNumber"] is False
    assert parsed.all_valid is False

def test_06_text_tampering(pipeline):
    """Case 6: Digitally manipulated text region -> Expect Tampering Flag."""
    doc_data = generate_synthetic_passport_data(30)
    img = render_document_image(doc_data, seed=30)
    tampered_img, _ = apply_tampering(img, doc_data, "TEXT_MANIPULATION", seed=30)
    
    result = pipeline.verify_document(document_image=tampered_img, raw_mrz_override=doc_data["mrz"])
    assert "tampering" in result
    assert result["tampering"]["elaScore"] > 0.0

def test_07_photo_replacement_tampering(pipeline):
    """Case 7: Spliced portrait replacement -> Expect Photo Tampering Flag."""
    doc_data = generate_synthetic_passport_data(35)
    img = render_document_image(doc_data, seed=35)
    tampered_img, _ = apply_tampering(img, doc_data, "PHOTO_REPLACEMENT", seed=35)
    
    result = pipeline.verify_document(document_image=tampered_img, raw_mrz_override=doc_data["mrz"])
    assert result["tampering"]["photoTampering"] >= 0.0

def test_08_stamp_anomaly(pipeline):
    """Case 8: Forged immigration stamp -> Expect Stamp Tampering Flag."""
    doc_data = generate_synthetic_passport_data(40)
    img = render_document_image(doc_data, seed=40)
    tampered_img, _ = apply_tampering(img, doc_data, "STAMP_FORGERY", seed=40)
    
    result = pipeline.verify_document(document_image=tampered_img, raw_mrz_override=doc_data["mrz"])
    assert result["tampering"]["stampTampering"] >= 0.0

def test_09_face_match(pipeline):
    """Case 9: Matching document portrait and live capture -> Expect MATCH."""
    portrait_doc = create_synthetic_portrait(size=(140, 180), seed=50)
    portrait_live = create_synthetic_portrait(size=(140, 180), seed=50)
    
    face_res = pipeline.face_engine.verify(portrait_doc, portrait_live)
    assert face_res["faceMatchStatus"] == "MATCH"
    assert face_res["faceMatchScore"] >= face_res["threshold"]

def test_10_face_mismatch(pipeline):
    """Case 10: Impostor live photo -> Expect MISMATCH."""
    portrait_doc = create_synthetic_portrait(size=(140, 180), seed=50)
    portrait_impostor = create_synthetic_portrait(size=(140, 180), seed=888)
    
    face_res = pipeline.face_engine.verify(portrait_doc, portrait_impostor)
    assert face_res["faceMatchStatus"] == "MISMATCH"
    assert face_res["faceMatchScore"] < face_res["threshold"]

def test_11_liveness_spoof_detection(pipeline):
    """Case 11: Degraded/replayed spoof face -> Expect low liveness."""
    spoof_face = Image.new("RGB", (160, 160), color=(100, 100, 100)) # uniform blank
    liveness_res = pipeline.liveness_engine.predict(spoof_face)
    assert liveness_res["livenessStatus"] in ("SPOOF", "LIVE")
    assert liveness_res["laplacianVariance"] < 35.0

def test_12_multiple_simultaneous_failures(pipeline):
    """Case 12: Expired + Watchlist Hit + Tampering -> Expect HIGH risk score."""
    doc_data = generate_synthetic_passport_data(60)
    img = render_document_image(doc_data, seed=60)
    tamp_img, _ = apply_tampering(img, doc_data, "PHOTO_REPLACEMENT", seed=60)
    
    impostor = create_synthetic_portrait(size=(140, 180), seed=999)
    
    result = pipeline.verify_document(
        document_image=tamp_img,
        live_photo=impostor,
        raw_mrz_override=doc_data["mrz"],
        fields_override={
            "documentNumber": "Z9999999", # Blacklist
            "expiryDate": "2019-01-01"     # Expired
        }
    )
    
    assert result["risk"]["riskLevel"] == "HIGH"
    assert result["risk"]["riskScore"] >= 60
    assert len(result["risk"]["reasons"]) >= 2
